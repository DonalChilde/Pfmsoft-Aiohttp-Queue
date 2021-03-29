"""Top-level package for Pfmsoft-Aiohttp-Queue."""
import logging

from pfmsoft.aiohttp_queue.aiohttp import (
    ActionCallbacks,
    AiohttpAction,
    AiohttpActionCallback,
    AiohttpQueueWorkerFactory,
)

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

__author__ = """Chad Lowe"""
__email__ = "pfmsoft@gmail.com"
__version__ = "0.1.0"
