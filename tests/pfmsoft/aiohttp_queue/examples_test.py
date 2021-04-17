import asyncio
import logging
import random
import time
from asyncio.queues import Queue
from time import perf_counter_ns
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pytest
from aiohttp.client import ClientSession
from rich import inspect

from pfmsoft.aiohttp_queue import ActionCallbacks, AiohttpAction, AiohttpQueueWorker
from pfmsoft.aiohttp_queue.callbacks import ResponseContentToJson


@pytest.mark.asyncio
async def test_aiohttp_action(logger):
    """This longhand example relies on pytest-asyncio to actually run the task"""
    start = perf_counter_ns()
    url_template: str = "https://esi.evetech.net/latest/markets/${region_id}/history"
    method: str = "get"
    url_parameters: Dict = {"region_id": 10000002}
    context: Dict = {}
    max_attempts: int = 1
    request_kwargs: Dict = {"params": {"type_id": 34}}
    name: str = ""
    id_: str = ""
    callbacks = None
    action = AiohttpAction(
        method,
        url_template,
        url_parameters=url_parameters,
        max_attempts=max_attempts,
        context=context,
        request_kwargs=request_kwargs,
        name=name,
        id_=id_,
        callbacks=callbacks,
    )
    actions = [action]
    workers = [AiohttpQueueWorker()]
    queue = Queue()
    async with ClientSession() as session:
        worker_tasks = []
        for worker in workers:
            worker_task: asyncio.Task = asyncio.create_task(
                worker.consumer(queue, session)
            )
            worker_tasks.append(worker_task)
        for item in actions:
            queue.put_nowait(item)
        await queue.join()
        for worker_task in worker_tasks:
            worker_task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
    end = perf_counter_ns()
    seconds = (end - start) / 1000000000
    logger.info(
        "Queue completed -  took %s seconds, %s actions per second.",
        f"{seconds:9f}",
        f"{len(actions)/seconds:1f}",
    )
    assert action.response.status == 200


@pytest.mark.asyncio
async def test_just_an_action():
    action_1 = market_history_action(10000002, 34)
    async with ClientSession() as session:
        await action_1.do_action(session)
    assert action_1.response.status == 200
    assert len(action_1.result) > 5


def test_run_a_queue_of_tasks():
    """Actions are performed concurrently.

    With a larger set of actions, and more workers,
    this will show a dramatic speed up over sequential
    actions.
    """
    action_1 = market_history_action(10000002, 34)
    action_2 = market_history_action(10000002, 36)
    actions = [action_1, action_2]
    workers = [AiohttpQueueWorker(), AiohttpQueueWorker()]
    asyncio.run(example_queue_runner(actions, workers))
    assert action_1.response.status == 200
    assert len(action_1.result) > 5
    assert action_2.response.status == 200
    assert len(action_2.result) > 5


def test_run_a_list_of_tasks(logger):
    """Actions are performed sequentially.

    Not really making use of async/await,
    but sometimes you only need to do a couple of things.
    """
    action_1 = market_history_action(10000002, 34)
    action_2 = market_history_action(10000002, 36)
    actions = [action_1, action_2]
    asyncio.run(example_action_runner(actions))
    assert action_1.response.status == 200
    assert len(action_1.result) > 5
    assert action_2.response.status == 200
    assert len(action_2.result) > 5


async def example_action_runner(
    actions: Sequence[AiohttpAction],
    session_kwargs=None,
):
    """A coroutine that performs actions sequentially."""
    start = perf_counter_ns()
    if session_kwargs is None:
        session_kwargs = {}
    async with ClientSession(**session_kwargs) as session:
        for action in actions:
            await action.do_action(session)
    end = perf_counter_ns()
    seconds = (end - start) / 1000000000
    print(
        "Actions completed -  took %s seconds, %s actions per second.",
        f"{seconds:9f}",
        f"{len(actions)/seconds:1f}",
    )


async def example_queue_runner(
    actions: Sequence[AiohttpAction],
    workers: Sequence[AiohttpQueueWorker],
    session_kwargs=None,
):
    """A coroutine that puts the actions, workers and the queue together.

    Performs actions concurrently
    """
    start = perf_counter_ns()
    if session_kwargs is None:
        session_kwargs = {}
    queue: Queue = Queue()
    async with ClientSession(**session_kwargs) as session:
        worker_tasks = []
        for worker in workers:
            worker_task: asyncio.Task = asyncio.create_task(
                worker.consumer(queue, session)
            )
            worker_tasks.append(worker_task)
        for action in actions:
            queue.put_nowait(action)
        await queue.join()
        for worker_task in worker_tasks:
            worker_task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        end = perf_counter_ns()
        seconds = (end - start) / 1000000000
        print(
            "Queue completed -  took %s seconds, %s actions per second.",
            f"{seconds:9f}",
            f"{len(actions)/seconds:1f}",
        )


def market_history_action(region_id, type_id) -> AiohttpAction:
    """Build an action that gets market history from Eve ESI."""
    route = "/latest/markets/${region_id}/history"
    url_parameters = {"region_id": region_id}
    params = {"datasource": "tranquility", "type_id": type_id}
    request_kwargs = {"params": params}
    callbacks: ActionCallbacks = ActionCallbacks(success=[ResponseContentToJson()])
    action = make_get_action(
        route=route,
        url_parameters=url_parameters,
        request_kwargs=request_kwargs,
        callbacks=callbacks,
    )
    return action


def make_get_action(
    route: str,
    url_parameters: Dict[str, Any],
    request_kwargs,
    callbacks: Optional[ActionCallbacks] = None,
):
    """A helper to build actions for Eve Online's ESI api."""
    base_path = "esi.evetech.net"
    url_template: str = "https://" + base_path + route
    action = AiohttpAction(
        method="get",
        url_template=url_template,
        url_parameters=url_parameters,
        request_kwargs=request_kwargs,
        callbacks=callbacks,
    )
    return action
