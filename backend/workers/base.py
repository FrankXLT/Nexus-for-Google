import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)

class BaseWorker:
    """Base architecture for infinite async worker loops."""
    def __init__(self, name: str):
        self.name = name

    async def run(self):
        """The main loop for the worker."""
        logger.info(f"Worker {self.name} started.")
        while True:
            try:
                await self.process()
            except Exception as e:
                logger.error(f"Worker {self.name} encountered an error: {e}")
                traceback.print_exc()
                await asyncio.sleep(10)

    async def process(self):
        """
        Abstract method to process one loop iteration. Must be overridden by subclasses.

        Layer Interactions:
        - Layer 3 (State Machine): Subclass logic for state transitions.

        State Interactions:
        - None

        Args/Returns:
        - None
        """
        raise NotImplementedError("Subclasses must implement process()")
entedError("Subclasses must implement process()")
