from dataclasses import dataclass, field
from typing import Dict
from uuid import UUID, uuid4

from pfmsoft import aiohttp_queue
from pfmsoft.aiohttp_queue import callbacks as AQ_callbacks


@dataclass
class TestAction:
    action: aiohttp_queue.AiohttpAction
    context: Dict = field(default_factory=dict)


def get_with_response_text() -> TestAction:

    test_action = None
    return test_action


def get_with_response_json() -> TestAction:
    url_template = "https://httpbin.org/get"
    url_parameters = None
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    params: Dict = {"arg1": "argument 1", "arg2": "argument 2"}
    request_qwargs = {"params": params}
    action = aiohttp_queue.AiohttpAction(
        "get",
        url_template=url_template,
        url_parameters=url_parameters,
        request_kwargs=request_qwargs,
        name="get_with_response_json",
        id_=uuid4(),
        callbacks=callbacks,
    )
    test_action = TestAction(
        action,
        {
            "url_template": url_template,
            "url_parameters": url_parameters,
            "params": params,
        },
    )
    return test_action


def get_with_404() -> TestAction:
    test_action = None
    return test_action


def get_with_501() -> TestAction:
    test_action = None
    return test_action


def action_with_data() -> TestAction:
    test_action = None
    return test_action


# def action_with_data() -> TestAction:
#     test_action = None
#     return test_action
