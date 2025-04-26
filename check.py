import argparse
from rich import print as rich_print

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

parser = argparse.ArgumentParser()

parser.add_argument(
    "--role",
    type=str,
    default="miner",
    help="Role of the auto upgrader (miner or validator), default miner",
)

btul.logging.add_args(parser)
config = btcc.Config(parser)

btul.logging(config=config, debug=True)
btul.logging.set_trace(config.logging.trace)
btul.logging._stream_formatter.set_trace(config.logging.trace)

btul.logging.info("\033[33m[34mYEAH\033[0m")