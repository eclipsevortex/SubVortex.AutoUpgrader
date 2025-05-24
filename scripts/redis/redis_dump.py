import os
import json
import asyncio
import argparse
import traceback
from dotenv import load_dotenv
from redis import asyncio as aioredis

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

SV_EXECUTION_DIR = os.path.abspath(os.path.expanduser("~/subvortex"))


def _load_env_var():
    # TEMP parse to get --neuron before loading env
    temp_args, _ = parser.parse_known_args()
    env_path = f"{SV_EXECUTION_DIR}/subvortex/{temp_args.neuron}/redis/.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
        btul.logging.info(f"📄 Loaded environment from {env_path}")
    else:
        btul.logging.warning(
            f"⚠️ Env file '{env_path}' not found. Proceeding with defaults and system env."
        )


async def _remove_prune_keys(database: aioredis.Redis):
    btul.logging.debug("🧹 Fetching all keys for pruning...")
    all_keys = await database.keys("*")

    keys_to_delete = [
        key
        for key in all_keys
        if key != b"version" and not key.startswith(b"migration_mode:")
    ]

    btul.logging.info(f"🗑️ Deleting {len(keys_to_delete)} keys from Redis...")
    if keys_to_delete:
        await database.delete(*keys_to_delete)
    btul.logging.success("✅ Pruning complete.")


def _create_redis_instace():
    return aioredis.StrictRedis(
        host=os.environ.get("SUBVORTEX_REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("SUBVORTEX_REDIS_PORT", 6379)),
        db=int(os.environ.get("SUBVORTEX_REDIS_INDEX", 0)),
        password=os.environ.get("SUBVORTEX_REDIS_PASSWORD", ""),
    )


async def _create_dump(path: str, database: aioredis.Redis):
    btul.logging.info(f"📦 Starting Redis dump to '{path}'...")
    keys = await database.keys("*")
    dump = {}

    async with database.pipeline() as pipe:
        for key in keys:
            pipe.type(key)
        key_types = await pipe.execute()

    for key, key_type in zip(keys, key_types):
        key_str = key.decode("utf-8")
        if key_type == b"string":
            value = await database.get(key)
            dump[key_str] = value.decode("utf-8") if value else None
        elif key_type == b"hash":
            hash_data = await database.hgetall(key)
            dump[key_str] = {f.decode(): v.decode() for f, v in hash_data.items()}
        elif key_type == b"list":
            dump[key_str] = [
                item.decode() for item in await database.lrange(key, 0, -1)
            ]
        elif key_type == b"set":
            dump[key_str] = {item.decode() for item in await database.smembers(key)}
        elif key_type == b"zset":
            dump[key_str] = [
                (item.decode(), score)
                for item, score in await database.zrange(key, 0, -1, withscores=True)
            ]

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        json.dump(dump, f)

    btul.logging.success(f"✅ Redis dump saved to '{path}' with {len(dump)} keys.")


async def _restore_dump(path: str, database: aioredis.StrictRedis):
    btul.logging.info(f"♻️ Restoring Redis dump from '{path}'...")

    await _remove_prune_keys(database)

    with open(path, "r") as file:
        dump = json.load(file)

    for key, value in dump.items():
        if isinstance(value, str):
            await database.set(key, value)
        elif isinstance(value, bytes):
            await database.set(key, value)
        elif isinstance(value, dict):
            await database.hset(key, mapping=value)
        elif isinstance(value, list) and all(
            isinstance(v, tuple) and len(v) == 2 for v in value
        ):
            await database.zadd(key, dict(value))
        elif isinstance(value, list):
            await database.lpush(key, *value)
        elif isinstance(value, set):
            await database.sadd(key, *value)

    btul.logging.success(f"✅ Redis restore complete. {len(dump)} keys loaded.")


async def create(args):
    try:
        btul.logging.info(
            f"🔌 Connecting to Redis at {args.redis_host}:{args.redis_port}, DB {args.redis_index}"
        )
        database = _create_redis_instace()

        await _create_dump(args.redis_dump_path, database)

    except Exception as e:
        btul.logging.error(f"❌ Dump creation failed: {e}")


async def restore(args):
    try:
        btul.logging.info(
            f"🔌 Connecting to Redis at {args.redis_host}:{args.redis_port}, DB {args.redis_index}"
        )
        database = _create_redis_instace()

        await _restore_dump(args.redis_dump_path, database)

    except Exception as e:
        btul.logging.error(f"❌ Restore failed: {e}")


async def main(config):
    btul.logging.info(
        f"🚀 Starting {'dump creation' if config.run_type == 'create' else 'restore'} process..."
    )

    # Load the env variable from the env file
    _load_env_var()

    # Create or restore the dump
    await create(config) if config.run_type == "create" else await restore(config)

    # Process successful
    btul.logging.success("🎉 Process complete.")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        btul.logging.add_args(parser)

        parser.add_argument(
            "--neuron",
            type=str,
            required=True,
            choices=["miner", "validator"],
            help="Neuron type (miner or validator)",
        )

        parser.add_argument(
            "--run_type",
            type=str,
            default="create",
            choices=["create", "restore"],
            help="Operation type: create or restore",
        )

        parser.add_argument(
            "--redis_dump_path",
            type=str,
            default="/var/tmp/redis/redis.dump",
            help="Dump file (with path) to create or restore",
        )

        config = btcc.Config(parser)

        btul.logging(config=config, debug=True)
        btul.logging.set_trace(config.logging.trace)
        btul.logging._stream_formatter.set_trace(config.logging.trace)

        asyncio.run(main(config=config))

    except KeyboardInterrupt:
        btul.logging.warning("⚠️ Interrupted by user.")
        
    except Exception as e:
        btul.logging.error(f"🔥 Unexpected error: {e}")
        btul.logging.debug(traceback.format_exc())
