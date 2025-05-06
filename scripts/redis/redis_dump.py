import os
import json
import asyncio
import argparse
import bittensor.utils.btlogging as btul
from redis import asyncio as aioredis


async def _remove_prune_keys(database: aioredis.Redis):
    # Get all keys
    all_keys = await database.keys("*")

    # Filter keys: exclude "version" and keys that start with "migration:"
    keys_to_delete = [
        key
        for key in all_keys
        if key != b"version" and not key.startswith(b"migration_mode:")
    ]

    # Delete them
    if keys_to_delete:
        await database.delete(*keys_to_delete)


async def create_dump(path: str, database: aioredis.Redis):
    """
    Create a dump from the database
    """
    # Get all keys in the database
    keys = await database.keys(f"*")

    dump = {}

    # Use a pipeline to batch key type queries
    async with database.pipeline() as pipe:
        for key in keys:
            # Query key type in the pipeline
            pipe.type(key)

        # Execute the pipeline
        key_types = await pipe.execute()

    # Process key-value pairs based on key types
    for key, key_type in zip(keys, key_types):
        key_str = key.decode("utf-8")
        if key_type == b"string":
            value = await database.get(key)
            dump[key_str] = value.decode("utf-8") if value is not None else None
        elif key_type == b"hash":
            hash_data = await database.hgetall(key)
            dump[key_str] = {
                field.decode("utf-8"): value.decode("utf-8")
                for field, value in hash_data.items()
            }
        elif key_type == b"list":
            list_data = await database.lrange(key, 0, -1)
            dump[key_str] = [item.decode("utf-8") for item in list_data]
        elif key_type == b"set":
            set_data = await database.smembers(key)
            dump[key_str] = {member.decode("utf-8") for member in set_data}
        elif key_type == b"zset":
            zset_data = await database.zrange(key, 0, -1, withscores=True)
            dump[key_str] = [
                (member.decode("utf-8"), score) for member, score in zset_data
            ]

    # Get the directory path
    directory, _ = os.path.split(path)

    # Ensure the directory exists, create it if it doesn't
    os.makedirs(directory, exist_ok=True)

    # Save dump file
    with open(path, "w") as file:
        json.dump(dump, file)


async def restore_dump(path: str, database: aioredis.StrictRedis):
    """
    Restore the dump into the database
    """
    # Remove concerned key
    await _remove_prune_keys(database=database)

    # Load the dump
    with open(path, "r") as file:
        json_data = file.read()

    dump = json.loads(json_data)

    for key, value in dump.items():
        # Determine the data type of the key-value pair
        if isinstance(value, str):
            # String key
            await database.set(key, value)
        elif isinstance(value, bytes):
            # For string keys, set the value
            await database.set(key, value)
        elif isinstance(value, dict):
            # For hash keys, sesut all fields and values
            await database.hset(key, mapping=value)
        elif isinstance(value, list):
            # For list keys, push all elements
            await database.lpush(key, *value)
        elif isinstance(value, set):
            # For database keys, add all members
            await database.sadd(key, *value)
        elif isinstance(value, list) and all(
            isinstance(item, tuple) and len(item) == 2 for item in value
        ):
            # For sorted set keys, add all members with scores
            await database.zadd(key, dict(value))


async def create(args):
    try:
        btul.logging.info(f"Loading database from {args.redis_host}:{args.redis_port}")
        database = aioredis.StrictRedis(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_index,
            password=args.redis_password,
        )

        btul.logging.info("Create dump starting")

        await create_dump(args.redis_dump_path, database)

        btul.logging.success("Create dump successful")
    except Exception as e:
        btul.logging.error(f"Error during rollout: {e}")


async def restore(args):
    try:
        btul.logging.info(f"Loading database from {args.redis_host}:{args.redis_port}")
        database = aioredis.StrictRedis(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_index,
            password=args.redis_password,
        )

        btul.logging.info("Restore dump starting")

        await restore_dump(args.redis_dump_path, database)

        btul.logging.success("Restore dump successful")

    except Exception as e:
        btul.logging.error(f"Error during rollback: {e}")


async def main(args):
    if args.run_type == "create":
        await create(args)
    else:
        await restore(args)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--run_type",
            type=str,
            default="create",
            help="Type of migration you want too execute. Options: create or restore. Default: create",
        )
        parser.add_argument("--redis_host", type=str, default="localhost")
        parser.add_argument("--redis_port", type=int, default=6379)
        parser.add_argument("--redis_index", type=int, default=1)
        parser.add_argument(
            "--redis_password",
            type=str,
            default=None,
            help="password for the redis database",
        )
        parser.add_argument(
            "--redis_dump_path",
            type=str,
            default="/var/tmp/redis/redis.dump",
            help="Dump file (with path) to create or restore",
        )

        args = parser.parse_args()

        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    except ValueError as e:
        print(f"ValueError: {e}")
