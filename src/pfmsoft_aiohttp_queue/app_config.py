"""App config values

TODO support a more complex logger, with log to file
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union

import click

APP_NAME = os.getenv(
    "pfmsoft_aiohttp_queue_APP_NAME",
    "Pfmsoft-Aiohttp-Queue",
)
"""The name of the app. Should be namespaced to prevent collision."""


APP_DIR = os.getenv(
    "pfmsoft_aiohttp_queue_APP_DIR",
    click.get_app_dir(APP_NAME, force_posix=True),
)
"""The app data directory. Location is system dependent."""


LOG_LEVEL = int(
    os.getenv(
        "pfmsoft_aiohttp_queue_LOG_LEVEL",
        str(logging.WARNING),
    )
)
"""App wide setting for log level"""


# TESTING = os.getenv("PFMSOFT_eve_esi_jobs_TESTING", "False")
# """"""
def _logger(
    log_path_parent: str, name: str, log_level: Union[str, int]
) -> logging.Logger:
    """A central logger that will log to file."""
    # log_level = logging.DEBUG
    log_file_name = f"{name}.log"
    logger_ = logging.getLogger(name)
    log_path: Path = log_path_parent / Path("logs")
    log_path.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path / Path(log_file_name), maxBytes=102400, backupCount=10
    )
    format_string = (
        "%(asctime)s %(levelname)s:%(funcName)s: "
        "%(message)s [in %(pathname)s:%(lineno)d]"
    )
    file_handler.setFormatter(logging.Formatter(format_string))
    file_handler.setLevel(log_level)
    logger_.addHandler(file_handler)
    # _logger.addHandler(RichHandler()
    logger_.setLevel(log_level)
    ############################################################
    # NOTE add file handler to other library modules as needed #
    ############################################################
    # async_logger = logging.getLogger("eve_esi_jobs")
    # async_logger.addHandler(file_handler)
    logger_.info("Logger initializd at %s", log_path)
    return logger_


LOGGER = _logger(APP_DIR, APP_NAME, LOG_LEVEL)
