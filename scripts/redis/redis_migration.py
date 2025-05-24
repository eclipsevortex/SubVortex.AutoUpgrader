import os
import asyncio
import argparse
import traceback
from dotenv import load_dotenv

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.service as saus
import subvortex.auto_upgrader.src.resolvers.metadata_resolver as saur
import subvortex.auto_upgrader.src.migration_manager as saumm

SV_EXECUTION_DIR = os.path.abspath(os.path.expanduser("~/subvortex"))


def _load_env_var():
    temp_args, _ = parser.parse_known_args()
    env_path = f"{SV_EXECUTION_DIR}/subvortex/{temp_args.neuron}/redis/.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
        btul.logging.info(f"📄 Loaded environment from {env_path}")
    else:
        btul.logging.warning(
            f"⚠️ Env file '{env_path}' not found. Proceeding with defaults and system env."
        )


async def main(config):
    # Check if execution directory exists
    if not os.path.exists(SV_EXECUTION_DIR):
        btul.logging.error(
            f"🚫 Execution directory not found: {SV_EXECUTION_DIR}. Please follow the 'Quick Setup' section in the Auto Upgrader README to set up your environment."
        )
        return

    btul.logging.info("🔧 Starting migration tool for Redis service...")

    # Load the env variable from the env file
    _load_env_var()

    # Create a metadata resolver
    resolver = saur.MetadataResolver()

    # Create the path of the service
    service_path = os.path.join(SV_EXECUTION_DIR, "subvortex", config.neuron, "redis")

    if not resolver.is_directory(path=service_path):
        btul.logging.error(f"❌ Redis service directory not found: {service_path}")
        return

    btul.logging.info(f"📂 Found Redis service directory: {service_path}")

    # Get the service metadata
    metadata = resolver.get_metadata(path=service_path)

    # Create the service
    service = saus.Service.create(metadata)
    btul.logging.info(f"🔧 Created service instance: {service.name}")

    # Create a migration manager
    manager = saumm.MigrationManager([(service, None)])
    btul.logging.info(f"📦 Collected migration scripts: {len(manager.migrations)}")

    # Collect the migrations
    manager.collect_migrations()

    if config.direction == "rollout":
        btul.logging.info("🚀 Starting rollout of migrations...")
    else:
        btul.logging.info("↩️ Starting rollback of migrations...")

    if config.direction == "rollout":
        await manager.apply()
        btul.logging.success("✅ Rollout completed successfully.")
    else:
        await manager.rollback()
        btul.logging.success("↩️ Rollback completed successfully.")

    # Final confirmation
    btul.logging.success(f"🎉 Migration process ({config.direction}) completed.")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        btul.logging.add_args(parser)

        parser.add_argument(
            "--neuron",
            type=str,
            required=True,
            choices=["miner", "validator"],
            help="🧠 Neuron type to migrate (miner or validator)",
        )

        parser.add_argument(
            "--direction",
            type=str,
            required=False,
            default="rollout",
            choices=["rollout", "rollback"],
            help="🔁 Direction of migration: rollout or rollback",
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
