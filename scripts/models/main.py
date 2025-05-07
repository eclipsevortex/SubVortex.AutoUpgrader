import os
import torch
import argparse
import numpy as np

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul
import bittensor_wallet.wallet as btw


class Worker:
    def __init__(self, config):
        self.config = config

    def run(self):
        torch_path = config.torch_model or f"{self._get_full_path()}/model.torch"

        if not os.path.exists(torch_path):
            btul.logging.error(f"❌ File not found: {torch_path}")
            return

        try:

            # Load the torch model
            state_dict = torch.load(torch_path, map_location="cpu")

            # If it's a full model, try to access the state_dict
            if hasattr(state_dict, "state_dict"):
                state_dict = state_dict.state_dict()

            # Convert each tensor to numpy
            np_weights = {}
            for key, tensor in state_dict.items():
                np_weights[key] = tensor

            btul.logging.debug(f"NPZ weights: {np_weights}")

            # Save to .npz file
            npz_path = os.path.join(os.path.dirname(torch_path), "model.npz")
            np.savez(npz_path, **np_weights)

            btul.logging.success(f"✅ Converted and saved as: {npz_path}")

        except Exception as e:
            btul.logging.error(f"❌ Failed to convert: {e}")

    def _get_full_path(self):
        full_path = os.path.expanduser(
            "{}/{}/{}/netuid{}/{}".format(
                config.logging.logging_dir,
                config.wallet.name,
                config.wallet.hotkey,
                config.netuid,
                config.neuron.name,
            )
        )

        return os.path.expanduser(full_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    btul.logging.add_args(parser)
    btw.Wallet.add_args(parser)

    parser.add_argument("--netuid", type=int, help="Subvortex network netuid", default=7)

    parser.add_argument(
        "--neuron.name",
        type=str,
        help="Trials for this miner go in miner.root / (wallet_cold - wallet_hot) / miner.name. ",
        default="subvortex_validator",
    )

    parser.add_argument("--torch_model", type=str, help="Path to the torch model", default=None)

    config = btcc.Config(parser)

    btul.logging(config=config, debug=True)
    btul.logging.set_trace(config.logging.trace)
    btul.logging._stream_formatter.set_trace(config.logging.trace)

    worker = Worker(config=config)
    worker.run()
