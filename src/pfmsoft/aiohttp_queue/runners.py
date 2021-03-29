import asyncio
import logging
from asyncio import Task, create_task, gather
from asyncio.queues import Queue
from time import perf_counter_ns
from typing import Sequence

from aiohttp import ClientSession

from pfmsoft.aiohttp_queue import AiohttpAction, AiohttpQueueWorkerFactory

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def do_action_runner(
    actions: Sequence[AiohttpAction],
    session_kwargs=None,
):
    asyncio.run(action_runner(actions, session_kwargs))


async def action_runner(
    actions: Sequence[AiohttpAction],
    session_kwargs=None,
):
    start = perf_counter_ns()
    if session_kwargs is None:
        session_kwargs = {}
    async with ClientSession(**session_kwargs) as session:
        for action in actions:
            await action.do_action(session)
    end = perf_counter_ns()
    seconds = (end - start) / 1000000000
    logger.info(
        "%s Actions sequentially completed -  took %s seconds, %s actions per second.",
        len(actions),
        f"{seconds:9f}",
        f"{len(actions)/seconds:1f}",
    )


def do_queue_runner(
    actions: Sequence[AiohttpAction],
    worker_factories: Sequence[AiohttpQueueWorkerFactory],
    session_kwargs=None,
):
    asyncio.run(queue_runner(actions, worker_factories, session_kwargs))


async def queue_runner(
    actions: Sequence[AiohttpAction],
    worker_factories: Sequence[AiohttpQueueWorkerFactory],
    session_kwargs=None,
):
    start = perf_counter_ns()
    if session_kwargs is None:
        session_kwargs = {}
    queue: Queue = Queue()
    async with ClientSession(**session_kwargs) as session:
        worker_tasks = []
        for factory in worker_factories:
            worker_task: Task = create_task(factory.get_worker(queue, session))
            worker_tasks.append(worker_task)
        logger.info("Adding %d actions to queue", len(actions))
        for action in actions:
            queue.put_nowait(action)
        await queue.join()
        for worker_task in worker_tasks:
            worker_task.cancel()
        await gather(*worker_tasks, return_exceptions=True)
        end = perf_counter_ns()
        seconds = (end - start) / 1000000000
        logger.info(
            (
                "%s Actions concurrently completed -  took %s seconds, "
                "%s actions per second using %s workers."
            ),
            len(actions),
            f"{seconds:9f}",
            f"{len(actions)/seconds:1f}",
            len(worker_tasks),
        )
