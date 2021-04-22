from string import Template
from typing import Dict

import pytest
import yaml
from aiohttp import ClientSession
from rich import inspect

from pfmsoft.aiohttp_queue import (
    ActionCallbacks,
    AiohttpAction,
    AiohttpQueueWorker,
    AiohttpRequest,
)
from pfmsoft.aiohttp_queue import callbacks as AC
from pfmsoft.aiohttp_queue.runners import do_action_runner, do_queue_runner


def action_with_pages() -> AiohttpAction:
    url_template = "https://esi.evetech.net/latest/contracts/public/${region_id}"
    url_paramters = {"region_id": 10000002}
    template = Template(url_template)
    params: Dict = {"page": 1}
    aiohttp_request = AiohttpRequest(
        method="get",
        url=template.substitute(url_paramters),
        params=params,
    )

    context: Dict = {}

    callbacks = ActionCallbacks(success=[AC.ResponseContentToJson()])
    action = AiohttpAction(
        aiohttp_args=aiohttp_request,
        context=context,
        callbacks=callbacks,
    )
    return action


def action_with_out_pages() -> AiohttpAction:
    url_template = "https://esi.evetech.net/latest/markets/${region_id}/history"
    url_paramters = {"region_id": 10000002}
    template = Template(url_template)
    params: Dict = {"page": 1, "type_id": 34}
    aiohttp_request = AiohttpRequest(
        method="get",
        url=template.substitute(url_paramters),
        params=params,
    )
    context: Dict = {}
    callbacks = ActionCallbacks(success=[AC.ResponseContentToJson()])
    action = AiohttpAction(
        aiohttp_args=aiohttp_request,
        context=context,
        callbacks=callbacks,
    )
    return action


@pytest.fixture(scope="module", name="completed_action_with_out_pages")
def completed_action_with_out_pages_():
    action = action_with_out_pages()
    do_action_runner([action])
    assert len(action.response_data) > 5
    return action


@pytest.fixture(scope="module", name="completed_action_with_pages")
def completed_action_with_pages_():
    action = action_with_pages()
    do_action_runner([action])
    assert len(action.response_data) > 5
    return action


def test_completed_action_pages(completed_action_with_pages):
    action: AiohttpAction = completed_action_with_pages
    assert len(action.response_data) > 5


def test_completed_action_no_pages(completed_action_with_out_pages):
    action: AiohttpAction = completed_action_with_out_pages
    assert len(action.response_data) > 5


def test_check_for_pages(
    completed_action_with_pages: AiohttpAction,
    completed_action_with_out_pages: AiohttpAction,
):
    callback = AC.CheckForPages()
    with_pages = completed_action_with_pages
    with_out_pages = completed_action_with_out_pages
    print(yaml.dump(with_pages.response_meta_to_dict()))
    assert with_pages.response is not None
    assert with_out_pages.response is not None
    assert with_pages.response.headers.get("x-pages", None) is not None
    assert int(with_pages.response.headers.get("x-pages")) > 1
    assert with_out_pages.response.headers.get("x-pages", None) is None
    assert callback.check_for_pages(with_pages) is not None
    assert callback.check_for_pages(with_pages) > 1
    assert callback.check_for_pages(with_out_pages) is None


def test_make_new_action(completed_action_with_pages):
    action = completed_action_with_pages
    callback = AC.CheckForPages()
    pages = callback.check_for_pages(action)
    assert pages >= 2
    new_action = callback.make_new_action(action, 2)
    do_action_runner([new_action])
    assert len(new_action.response_data) > 1
    assert str(action.uid) in new_action.name
    assert new_action.id_ == "2"


def test_get_all_pages(logger):
    action = action_with_pages()
    action.callbacks.success.append(AC.CheckForPages())
    do_action_runner([action])
    assert len(action.response_data) > 5
    print(len(action.response_data))
    print(yaml.dump(action.context["pfmsoft_page_report"]))
    # print(action.context["pfmsoft_page_report"])
    pages = AC.CheckForPages().check_for_pages(action)
    assert pages == len(action.context["pfmsoft_page_report"])
