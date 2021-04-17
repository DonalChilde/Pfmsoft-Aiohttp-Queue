import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pfmsoft import aiohttp_queue
from pfmsoft.aiohttp_queue import callbacks as AQ_callbacks


@dataclass
class TestAction:
    action: aiohttp_queue.AiohttpAction
    context: Dict = field(default_factory=dict)


def get_with_500_code(params: Dict[str, Any]) -> TestAction:
    url_template = "https://httpbin.org/status/500"
    url_params = None
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToText()]
    )

    test_action = build_get_test_action(
        "get_with_response_text",
        url_template=url_template,
        url_parameters=url_params,
        params=params,
        callbacks=callbacks,
        max_attempts=3,
    )
    return test_action


def get_with_response_text(params: Dict[str, Any]) -> TestAction:
    url_template = "https://httpbin.org/get"
    url_params = None
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToText()]
    )

    test_action = build_get_test_action(
        "get_with_response_text",
        url_template=url_template,
        url_parameters=url_params,
        params=params,
        callbacks=callbacks,
    )
    return test_action


def get_with_response_json(params: Dict[str, Any]) -> TestAction:

    url_template = "https://httpbin.org/get"
    url_params = None
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_with_response_json",
        url_template=url_template,
        url_parameters=url_params,
        params=params,
        callbacks=callbacks,
    )
    return test_action


def get_with_response_json_delay(params: Dict[str, Any], max_delay: int) -> TestAction:
    delay = random.randint(0, max_delay)
    url_template = f"https://httpbin.org/delay/{delay}"
    url_params = None
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_with_response_json",
        url_template=url_template,
        url_parameters=url_params,
        params=params,
        callbacks=callbacks,
    )
    return test_action


# def get_with_404() -> TestAction:
#     test_action = None
#     return test_action


# def get_with_501() -> TestAction:
#     test_action = None
#     return test_action


def get_list_of_dicts_result(url_params: Dict, params: Dict) -> TestAction:
    url_template = "https://esi.evetech.net/latest/markets/${region_id}/history"
    callbacks = aiohttp_queue.ActionCallbacks(
        success=[AQ_callbacks.ResponseContentToJson()]
    )
    test_action = build_get_test_action(
        "get_list_of_dicts_result",
        url_template=url_template,
        url_parameters=url_params,
        params=params,
        callbacks=callbacks,
    )
    return test_action


def build_get_test_action(
    name, url_template, url_parameters, params, callbacks, max_attempts=1
):
    request_qwargs = {"params": params}
    action = aiohttp_queue.AiohttpAction(
        "get",
        url_template=url_template,
        url_parameters=url_parameters,
        request_kwargs=request_qwargs,
        name=name,
        callbacks=callbacks,
        max_attempts=max_attempts,
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


def save_list_of_dicts_to_csv_file(
    url_params: Dict[str, str],
    params: Dict[str, str],
    file_path: Path,
    path_values: Optional[Dict] = None,
    file_ending: str = ".csv",
):
    test_action = get_list_of_dicts_result(url_params, params)
    test_action.action.callbacks.success.append(
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
    file_ending: str = "",
) -> TestAction:

    test_action = get_with_response_text(params)
    test_action.action.callbacks.success.append(
        AQ_callbacks.SaveResultToFile(
            file_path=file_path,
            path_values=path_values,
            file_ending=file_ending,
        )
    )
    return test_action


def save_json_to_file(
    params: Dict[str, str],
    file_path: Path,
    path_values: Optional[Dict] = None,
    file_ending: str = ".json",
) -> TestAction:
    test_action = get_with_response_json(params)
    test_action.action.callbacks.success.append(
        AQ_callbacks.SaveJsonResultToFile(
            file_path=file_path,
            path_values=path_values,
            file_ending=file_ending,
        )
    )
    return test_action


# def action_with_data() -> TestAction:
#     test_action = None
#     return test_action
