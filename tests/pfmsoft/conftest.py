"""conftest.py file for pfmsoft_aiohttp_queue"""
import json
import logging
from importlib import resources
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest
from rich import inspect

APP_LOG_LEVEL = logging.INFO


@pytest.fixture(scope="session", name="logger")
def _logger(test_log_path):
    """A central logger that will log to file."""
    log_level = logging.DEBUG
    log_file_name = f"{__name__}.log"
    logger = logging.getLogger(__name__)
    log_path: Path = test_log_path / Path("test-logs")
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
    logger.addHandler(file_handler)
    # _logger.addHandler(RichHandler()
    logger.setLevel(log_level)
    ############################################################
    # NOTE add file handler to other library modules as needed #
    ############################################################
    # async_logger = logging.getLogger("eve_esi_jobs")
    # async_logger.addHandler(file_handler)
    aiohttp_queue_logger = logging.getLogger("pfmsoft.aiohttp_queue")
    aiohttp_queue_logger.setLevel(logging.DEBUG)
    aiohttp_queue_logger.addHandler(file_handler)
    logger.info("Logging output of pfmsoft.aiohttp_queue")
    return logger


@pytest.fixture(scope="session", name="test_log_path")
def test_log_path_(test_app_data_dir):
    """Make a test-log directory under the app data directory"""
    log_path = test_app_data_dir / Path("test-logs")
    print(f"Logging at: {log_path}")
    return log_path


@pytest.fixture(scope="session", name="test_app_data_dir")
def test_app_data_dir_(tmp_path_factory):
    """make a temp directory for app data."""
    test_app_data_dir = tmp_path_factory.mktemp("pfmsoft_aiohttp_queue-")
    return test_app_data_dir


@pytest.fixture(scope="session")
def example_resource(logger: logging.Logger) -> dict:
    """Load a resource file from a package directory."""
    try:
        resource_path: str = "tests.pfmsoft.aiohttp_queue.resources"
        resource_name: str = "example.json"
        with resources.open_text(resource_path, resource_name) as data_file:
            data = json.load(data_file)
            logger.info("Loaded resource file %s from %s", resource_name, resource_path)
            return data
    except Exception as ex:
        logger.exception(
            "Unable to load resource file %s from %s Error msg %s",
            resource_name,
            resource_path,
            ex,
        )
        raise ex


# @pytest.fixture(autouse=True)
# def env_setup(monkeypatch, test_app_data_dir):
#     """environment variables set for each test."""
#     monkeypatch.setenv(
#         "pfmsoft_aiohttp_queue_TESTING",
#         "True",
#     )
#     monkeypatch.setenv(
#         "pfmsoft_aiohttp_queue_LOG_LEVEL",
#         str(APP_LOG_LEVEL),
#     )
#     monkeypatch.setenv(
#         "pfmsoft_aiohttp_queue_APP_DIR",
#         str(test_app_data_dir),
#     )
