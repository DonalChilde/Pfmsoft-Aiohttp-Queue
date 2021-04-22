import random
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from pfmsoft import aiohttp_queue
from pfmsoft.aiohttp_queue import callbacks as AQ_callbacks
from pfmsoft.aiohttp_queue.aiohttp import AiohttpAction, AiohttpRequest


@dataclass
class TestAction:
    action: aiohttp_queue.AiohttpAction
    context: Dict = field(default_factory=dict)


def get_with_500_code(params: Dict[str, Any]) -> AiohttpAction:
    url = "https://httpbin.org/status/500"
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToText()]
    )

    test_action = build_get_test_action(
        "get_with_500_code",
        url=url,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


def get_with_response_text(params: Dict[str, Any]) -> AiohttpAction:
    url = "https://httpbin.org/get"
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToText()]
    )

    test_action = build_get_test_action(
        "get_with_response_text",
        url=url,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


def get_with_response_json(params: Dict[str, Any]) -> AiohttpAction:

    url = "https://httpbin.org/get"
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_with_response_json",
        url=url,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


def get_with_response_json_delay(
    params: Dict[str, Any], max_delay: int
) -> AiohttpAction:
    delay = random.randint(0, max_delay)
    url = f"https://httpbin.org/delay/{delay}"
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_with_response_json",
        url=url,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


# def get_with_404() -> TestAction:
#     test_action = None
#     return test_action


# def get_with_501() -> TestAction:
#     test_action = None
#     return test_action


def get_list_of_dicts_result(url_params: Dict, params: Dict) -> AiohttpAction:
    url_template = Template(
        "https://esi.evetech.net/latest/markets/${region_id}/history"
    )
    url = url_template.substitute(url_params)
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_list_of_dicts_result",
        url=url,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


def build_get_test_action(name, url, params, callbacks, json=None, max_attempts=1):
    aiohttp_request = AiohttpRequest(
        method="get",
        url=url,
        params=params,
        json=json,
    )
    context = {"params": params}
    action = aiohttp_queue.AiohttpAction(
        aiohttp_args=aiohttp_request,
        name=name,
        callbacks=callbacks,
        max_attempts=max_attempts,
        context=context,
    )

    return action


def save_list_of_dicts_to_csv_file(
    url_params: Dict[str, str],
    params: Dict[str, str],
    file_path: Path,
    path_values: Optional[Dict] = None,
    file_ending: str = ".csv",
) -> AiohttpAction:
    test_action = get_list_of_dicts_result(url_params, params)
    test_action.callbacks.success.append(
        AQ_callbacks.SaveListOfDictResultToCSVFile(
            file_path=file_path,
            path_values=path_values,
            file_ending=file_ending,
        )
    )
    return test_action


def save_txt_to_file(
    params: Dict[str, str],
    file_path: Path,
    path_values: Optional[Dict] = None,
) -> AiohttpAction:

    test_action = get_with_response_text(params)
    test_action.callbacks.success.append(
        AQ_callbacks.SaveResultToTxtFile(
            file_path=file_path,
            path_values=path_values,
        )
    )
    return test_action


def save_json_to_file(
    params: Dict[str, str],
    file_path: Path,
    path_values: Optional[Dict] = None,
    file_ending: str = ".json",
) -> AiohttpAction:
    test_action = get_with_response_json(params)
    test_action.callbacks.success.append(
        AQ_callbacks.SaveResultToJsonFile(
            file_path=file_path,
            path_values=path_values,
            file_ending=file_ending,
        )
    )
    return test_action


# def action_with_data() -> TestAction:
#     test_action = None
#     return test_action
