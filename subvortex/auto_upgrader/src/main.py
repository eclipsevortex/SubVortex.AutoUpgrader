import asyncio
import argparse
import traceback

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.orchestrator as sauo
import subvortex.auto_upgrader.src.version as sauv


class Worker:
    def __init__(self):
        parser = argparse.ArgumentParser()

        btul.logging.add_args(parser)
        self.config = btcc.Config(parser)

        btul.logging(config=self.config, debug=True)
        btul.logging.set_trace(self.config.logging.trace)
        btul.logging._stream_formatter.set_trace(self.config.logging.trace)

        self.orchestrator = sauo.Orchestrator()

        self.should_exit = asyncio.Event()
        self.finished = asyncio.Event()

    async def run(self):
        # Display the version
        btul.logging.info(
            f"version: {sauv.__VERSION__}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        first_run = True
        while not self.should_exit.is_set():
            # Reset success
            success = False

            try:
                if not first_run:
                    await asyncio.sleep(sauc.SV_CHECK_INTERVAL)

                # Rollout the plan
                success = self.orchestrator.run_plan()

            except KeyboardInterrupt:
                btul.logging.debug("KeyboardInterrupt", prefix=sauc.SV_LOGGER_NAME)

            except Exception as e:
                btul.logging.error(
                    f"An error has been thrown: {e}", prefix=sauc.SV_LOGGER_NAME
                )
                btul.logging.debug(traceback.format_exc())

            finally:
                # Flat not first run anymore
                first_run = False

                if not success:
                    # The plan was not successful, rollback it
                    self.orchestrator.run_rollback_plan()

        # Signal the waiter the service has finished
        self.finished.set()

    async def shutdown(self):
        # Signal the service to stop
        self.should_exit.set()

        # Wait until the service has finished
        await self.finished.wait()


if __name__ == "__main__":
    asyncio.run(Worker().run())
