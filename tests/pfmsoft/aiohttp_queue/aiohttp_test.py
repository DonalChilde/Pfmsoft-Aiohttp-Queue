import json
from pathlib import Path
from typing import Dict

from tests.pfmsoft.aiohttp_queue import action_builders

from pfmsoft.aiohttp_queue.runners import do_single_action_runner

# pylint: disable=unsubscriptable-object


def test_action_repr(logger):
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    action = action_builders.get_with_response_json(params)
    print(action.__repr__())
    print(action)
    assert "params" in action.__repr__()
    # assert False


def test_response_to_json(logger):
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    action = action_builders.get_with_response_json(params)

    do_single_action_runner(action)
    assert action.response.status == 200
    response_meta = action.response_meta_to_dict()
    assert action.aiohttp_args.url in response_meta["request_info"]["url"]
    data: Dict = action.response_data
    assert data["args"] == action.context["params"]


def test_response_to_string(logger):
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    action = action_builders.get_with_response_text(params)
    do_single_action_runner(action)
    assert action.response.status == 200
    response_meta = action.response_meta_to_dict()
    assert action.aiohttp_args.url in response_meta["request_info"]["url"]
    data_string: str = action.response_data
    # pylint: disable=unsupported-membership-test
    assert action.context["params"]["arg1"] in data_string
    json_result = json.loads(action.response_data)
    assert json_result["args"] == action.context["params"]


def test_text_result_to_file(test_app_data_dir, logger):
    file_path: Path = test_app_data_dir / Path("text_result_to_file.txt")
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    action = action_builders.save_txt_to_file(params, file_path)
    do_single_action_runner(action)
    assert action.response.status == 200
    print(file_path)
    assert file_path.is_file()
    assert file_path.stat().st_size > 10


def test_list_of_dicts_result(logger):
    url_params = {"region_id": 10000002}
    params = {"type_id": 34}
    action = action_builders.get_list_of_dicts_result(
        url_params=url_params, params=params
    )

    do_single_action_runner(action)
    assert action.response.status == 200
    assert isinstance(action.response_data, list)
    assert isinstance(action.response_data[0], dict)


def test_save_list_of_dicts_to_csv(test_app_data_dir, logger):
    # TODO verify all elements are output to csv, eg. json count == csv count
    url_params = {"region_id": 10000002}
    params = {"type_id": 34}
    file_path: Path = test_app_data_dir / Path("test_save_list_of_dicts_to_csv.csv")
    action = action_builders.save_list_of_dicts_to_csv_file(
        url_params=url_params, params=params, file_path=file_path
    )
    do_single_action_runner(action)
    assert action.response.status == 200
    print(file_path)
    assert file_path.is_file()
    assert file_path.stat().st_size > 10


def test_save_json_to_file(test_app_data_dir, logger):
    file_path: Path = test_app_data_dir / Path("test_save_json_to_file.json")
    params = {"arg1": "argument 1", "arg2": "argument 2"}
    action = action_builders.save_json_to_file(params, file_path)
    do_single_action_runner(action)
    assert action.response.status == 200
    print(file_path)
    assert file_path.is_file()
    assert file_path.stat().st_size > 10
    with open(file_path) as file:
        data = json.load(file)
        assert data == action.response_data


# from eve_esi_jobs.pfmsoft.util.async_actions.aiohttp import (
#     AiohttpAction,
#     AiohttpActionCallback,
#     AiohttpActionMessenger,
#     AiohttpQueueWorker,
#     LogFail,
#     LogRetry,
#     LogSuccess,
#     ResponseToJson,
#     do_aiohttp_action_queue,
# )


# def make_get_action(
#     route: str,
#     url_parameters: Dict[str, Any],
#     request_kwargs,
#     callbacks: Optional[ActionCallbacks] = None,
# ):
#     base_path = "esi.evetech.net"
#     url_template: str = "https://" + base_path + route
#     action = AiohttpAction(
#         method="get",
#         url_template=url_template,
#         url_parameters=url_parameters,
#         request_kwargs=request_kwargs,
#         callbacks=callbacks,
#     )
#     return action


# def test_run_queue_example():
#     pass


# async def example_queue_task(
#     actions: Sequence[AiohttpAction],
#     worker_factories: Sequence[AiohttpQueueWorkerFactory],
#     session_kwargs=None,
# ):
#     start = perf_counter_ns()
#     if session_kwargs is None:
#         session_kwargs = {}
#     queue: Queue = Queue()
#     async with ClientSession(**session_kwargs) as session:
#         worker_tasks = []
#         for factory in worker_factories:
#             worker_task: asyncio.Task = asyncio.create_task(
#                 factory.get_worker(queue, session)
#             )
#             worker_tasks.append(worker_task)
#         for action in actions:
#             queue.put_nowait(action)
#         await queue.join()
#         for worker_task in worker_tasks:
#             worker_task.cancel()
#         await asyncio.gather(*worker_tasks, return_exceptions=True)
#         end = perf_counter_ns()
#         seconds = (end - start) / 1000000000
#         print(
#             "Queue completed -  took %s seconds, %s actions per second.",
#             f"{seconds:9f}",
#             f"{len(actions)/seconds:1f}",
#         )


# @pytest.mark.asyncio
# async def test_get_market_history():
#     region_id = 10000002
#     type_id = 34
#     queue = Queue()
#     action = market_history_action(region_id=region_id, type_id=type_id)
#     async with ClientSession() as session:
#         await action.do_action(queue, session)
#         assert action.response.status == 200
#     # inspect(action)
#     # assert False


# @pytest.mark.asyncio
# async def test_get_market_history_queue_single(caplog):
#     caplog.set_level(logging.INFO)
#     region_id = 10000002
#     type_id = 34
#     action_list: List[AiohttpAction] = []
#     action = market_history_action(region_id=region_id, type_id=type_id)
#     action_list.append(action)
#     await do_aiohttp_action_queue(action_list, [AiohttpQueueWorker()])
#     assert action.response.status == 200
#     # assert False


# @pytest.mark.asyncio
# async def test_get_market_history_queue_multiple(caplog):
#     caplog.set_level(logging.INFO)
#     region_ids = [10000002, 10000032, 10000030, 10000042, 10000043]
#     type_ids = [34, 36, 38]
#     worker_count = 15
#     workers = []
#     actions = market_history_actions(region_ids=region_ids, type_ids=type_ids)
#     for _ in range(worker_count):
#         workers.append(AiohttpQueueWorker())
#     await do_aiohttp_action_queue(actions, workers)
#     for action in actions:
#         assert action.response.status == 200
#     # assert False


# @pytest.mark.asyncio
# async def test_success_action_callbacks(caplog):
#     caplog.set_level(logging.INFO)
#     region_ids = [10000002, 10000032, 10000030, 10000042, 10000043]
#     type_ids = [34, 36, 38]
#     worker_count = 15
#     workers = []
#     actions = market_history_actions(region_ids=region_ids, type_ids=type_ids)

#     for _ in range(worker_count):
#         workers.append(AiohttpQueueWorker())
#     await do_aiohttp_action_queue(actions, workers)
#     for action in actions:
#         assert action.response.status == 200
#         assert len(action.result) > 5

#     # assert False


# @pytest.mark.asyncio
# async def test_get_market_history_queue_local_def():
#     region_id = 10000002
#     type_id = 34
#     queue = Queue()
#     workers = []
#     action = market_history_action(region_id=region_id, type_id=type_id)
#     async with ClientSession() as session:
#         workers.append(make_consumer(queue, session))
#         queue.put_nowait(action)
#         worker_tasks = []
#         for worker in workers:
#             worker_tasks.append(create_task(worker))
#         await queue.join()
#         for worker_task in worker_tasks:
#             worker_task.cancel()
#         await gather(*worker_tasks, return_exceptions=True)
#         assert action.response.status == 200
#     assert action.response.status == 200


# def market_history_actions(
#     region_ids: Sequence[int],
#     type_ids: Sequence[int],
# ) -> List[AiohttpAction]:
#     actions = []
#     for region_id in region_ids:
#         for type_id in type_ids:
#             actions.append(market_history_action(region_id, type_id))
#     return actions


# def market_history_actions_with_callbacks(
#     region_ids: Sequence[int],
#     type_ids: Sequence[int],
# ) -> List[AiohttpAction]:
#     actions = []
#     for region_id in region_ids:
#         for type_id in type_ids:
#             actions.append(market_history_action(region_id, type_id))
#     return actions


# def market_history_action(region_id, type_id) -> AiohttpAction:
#     route = "/latest/markets/${region_id}/history"
#     url_parameters = {"region_id": region_id}
#     params = {"datasource": "tranquility", "type_id": type_id}
#     request_kwargs = {"params": params}
#     callbacks: ActionCallbacks = ActionCallbacks(success=[ResultToJson()])
#     action = make_get_action(
#         route=route,
#         url_parameters=url_parameters,
#         request_kwargs=request_kwargs,
#         callbacks=callbacks,
#     )
#     return action


# async def consumer(queue, session):
#     while True:
#         print("getting action from queue.")
#         action: AiohttpAction = await queue.get()
#         try:
#             print("awaiting action: ", action)
#             await action.do_action(queue, session)
#         except Exception as e:
#             print(e)
#         print("action complete: ", action)
#         queue.task_done()


# def make_consumer(queue, session):
#     async def consumer2(queue):
#         while True:
#             print("getting action from queue.")
#             action: AiohttpAction = await queue.get()
#             try:
#                 print("awaiting action: ", action)
#                 await action.do_action(queue, session)
#             except Exception as e:
#                 print(e)
#             print("action complete: ", action)
#             queue.task_done()

#     worker = consumer2(queue)
#     return worker


########################################################################
# async def example_worker(name, queue):
#     while True:
#         # Get a "work item" out of the queue.
#         sleep_for = await queue.get()

#         # Sleep for the "sleep_for" seconds.
#         await asyncio.sleep(sleep_for)

#         # Notify the queue that the "work item" has been processed.
#         queue.task_done()

#         print(f"{name} has slept for {sleep_for:.2f} seconds")


# @pytest.mark.asyncio
# async def test_example_main():
#     # Create a queue that we will use to store our "workload".
#     queue = asyncio.Queue()

#     # Generate random timings and put them into the queue.
#     total_sleep_time = 0
#     for _ in range(20):
#         sleep_for = random.uniform(0.05, 1.0)
#         total_sleep_time += sleep_for
#         queue.put_nowait(sleep_for)

#     # Create three worker tasks to process the queue concurrently.
#     tasks = []
#     for i in range(3):
#         task = asyncio.create_task(example_worker(f"worker-{i}", queue))
#         tasks.append(task)

#     # Wait until the queue is fully processed.
#     started_at = time.monotonic()
#     await queue.join()
#     total_slept_for = time.monotonic() - started_at

#     # Cancel our worker tasks.
#     for task in tasks:
#         task.cancel()

#     print("====")
#     print(f"3 workers slept in parallel for {total_slept_for:.2f} seconds")
#     print(f"total expected sleep time: {total_sleep_time:.2f} seconds")
#     # assert False


# # @pytest.mark.asyncio
# # async def test_example():
# #     await asyncio.run(example_main())
# #     assert False
