# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import asyncio
import argparse
import traceback

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.orchestrator as sauo
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.exception as saue


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

        # Display the execution method
        btul.logging.info(
            f"execution: {sauc.SV_EXECUTION_METHOD}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        if sauc.SV_EXECUTION_METHOD not in ['process', 'service', 'container']:
            btul.logging.error(
                f"Invalid execution method: '{sauc.SV_EXECUTION_METHOD}'. "
                "Must be one of: 'process', 'service', or 'container'.",
                prefix=sauc.SV_LOGGER_NAME
            )
            self.finished.set()
            return

        first_run = True
        while not self.should_exit.is_set():
            # Reset success
            success = False

            try:
                if not first_run:
                    btul.logging.debug(
                        f"Waiting {sauc.SV_CHECK_INTERVAL} seconds before next check..."
                    )
                    await asyncio.sleep(sauc.SV_CHECK_INTERVAL)

                # Rollout the plan
                success = await self.orchestrator.run_plan()

            except asyncio.TimeoutError:
                # Normal cycle timeout, no problem
                pass

            except (KeyboardInterrupt, asyncio.CancelledError):
                btul.logging.debug("Shutdown requested", prefix=sauc.SV_LOGGER_NAME)
                success = True

            except saue.AutoUpgraderError as e:
                btul.logging.error(e, prefix=sauc.SV_LOGGER_NAME)
                btul.logging.debug(traceback.format_exc())

            except Exception as e:
                btul.logging.error(
                    f"An error has been thrown: {e}", prefix=sauc.SV_LOGGER_NAME
                )
                btul.logging.debug(traceback.format_exc())

            finally:
                # Flat not first run anymore
                first_run = False

                if not success and not sauc.SV_DISABLE_ROLLBACK:
                    # The plan was not successful, rollback it
                    await self.orchestrator.run_rollback_plan()

                # Clean everything
                self.orchestrator.reset()

        # Signal the waiter the service has finished
        self.finished.set()

    async def shutdown(self):
        # Signal the service to stop
        self.should_exit.set()

        # Wait until the service has finished
        await self.finished.wait()


if __name__ == "__main__":
    asyncio.run(Worker().run())
