import logging
import random
from typing import List, Sequence

from tests.pfmsoft.aiohttp_queue import action_builders

from pfmsoft.aiohttp_queue import (
    ActionObserver,
    ActionState,
    AiohttpAction,
    AiohttpQueueWorker,
)
from pfmsoft.aiohttp_queue.runners import do_queue_runner

logger = logging.getLogger(__name__)


def test_new_workers(logger, caplog):
    caplog.set_level(logging.INFO)
    actions: List[AiohttpAction] = []
    workers = [AiohttpQueueWorker(), AiohttpQueueWorker()]
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    test_action = action_builders.get_with_response_json(params)
    action = test_action.action
    actions.append(action)
    do_queue_runner(actions, workers)
    for action in actions:
        assert action.state == ActionState.SUCCESS
    # assert False


def build_get_json_actions(count: int) -> Sequence[action_builders.TestAction]:
    test_actions = []
    for _ in range(count):
        params = {"arg1": random.randint(1, 1000), "arg2": random.randint(1, 1000)}
        test_action = action_builders.get_with_response_json(params)
        test_actions.append(test_action)
    return test_actions


def build_get_json_delay_actions(count: int, max_delay: int):
    test_actions = []
    for _ in range(count):
        params = {"arg1": random.randint(1, 1000), "arg2": random.randint(1, 1000)}
        test_action = action_builders.get_with_response_json_delay(params, max_delay)
        test_action.action.observers.append(ActionObserver())
        test_actions.append(test_action)
    return test_actions


def build_get_500_json_actions(count: int):
    test_actions = []
    for _ in range(count):
        params = {"arg1": random.randint(1, 1000), "arg2": random.randint(1, 1000)}
        test_action = action_builders.get_with_500_code(params)
        test_action.action.observers.append(ActionObserver())
        test_actions.append(test_action)
    return test_actions


def test_10_actions(caplog):
    caplog.set_level(logging.INFO)
    test_actions = build_get_json_actions(10)
    actions: List[AiohttpAction] = [item.action for item in test_actions]
    worker_count = 5
    workers = []
    for _ in range(worker_count):
        workers.append(AiohttpQueueWorker())
    do_queue_runner(actions, workers)
    for action in actions:
        assert action.state == ActionState.SUCCESS

    # assert False


def test_10_actions_delay(caplog):
    caplog.set_level(logging.INFO)
    test_actions = build_get_json_delay_actions(10, 3)
    actions: List[AiohttpAction] = [item.action for item in test_actions]
    worker_count = 5
    workers = []
    for _ in range(worker_count):
        workers.append(AiohttpQueueWorker())
    do_queue_runner(actions, workers)
    for action in actions:
        assert action.state == ActionState.SUCCESS
    # assert False


def test_500(caplog):
    caplog.set_level(logging.INFO)
    test_actions = build_get_500_json_actions(1)
    actions: List[AiohttpAction] = [item.action for item in test_actions]
    worker_count = 2
    workers = []
    for _ in range(worker_count):
        workers.append(AiohttpQueueWorker())
    do_queue_runner(actions, workers)
    for action in actions:
        assert action.state == ActionState.FAIL
    # assert False
