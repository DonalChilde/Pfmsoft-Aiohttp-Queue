import asyncio
import logging
from asyncio import Task, create_task, gather
from asyncio.queues import Queue
from time import perf_counter_ns
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

from aiohttp import ClientResponse

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def response_to_json(response: Optional[ClientResponse]) -> Dict:

    # TODO change name of Aiohttp callback from responsetojson to resulttojson
    # TODO make this a callback, figure out how to assign. attrgetter and a list of args?
    if response is not None:
        data: Dict[str, Any] = {}
        info = response.request_info
        request_headers = []
        for key, value in info.headers.items():
            request_headers.append({key: value})
        response_headers = [{key: value} for key, value in response.headers.items()]
        data["version"] = response.version
        data["status"] = response.status
        data["reason"] = response.reason
        data["method"] = info.method
        data["url"] = str(info.url)
        data["real_url"] = str(info.real_url)
        data["cookies"] = response.cookies
        data["request_headers"] = request_headers
        data["response_headers"] = response_headers
    else:
        data = {"error": "response to json called before response recieved."}
    return data
