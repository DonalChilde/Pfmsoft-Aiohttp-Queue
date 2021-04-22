# import dataclasses
# import logging
# from asyncio.queues import Queue
# from dataclasses import dataclass, field
# from enum import Enum
# from string import Template
# from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Union
# from uuid import UUID, uuid4

# import aiohttp
# from aiohttp import ClientResponse, ClientSession

# from pfmsoft.aiohttp_queue.aiohttp import AiohttpQueueWorker
# from pfmsoft.aiohttp_queue.runners import do_queue_runner
# from pfmsoft.aiohttp_queue.utilities import optional_object

# logger = logging.getLogger(__name__)
# logger.addHandler(logging.NullHandler())


# @dataclass
# class AiohttpRequest:

#     method: str
#     url: str
#     params: Optional[Mapping] = None
#     data: Any = None
#     json: Optional[Union[List, Dict]] = None
#     headers: Optional[Dict] = None
#     kwargs: Dict = field(default_factory=dict)

#     def as_dict(self):
#         kwarg_dict = {
#             "method": self.method,
#             "url": self.url,
#             "params": self.params,
#             "data": self.data,
#             "json": self.json,
#             "headers": self.headers,
#         }
#         kwarg_dict.update(self.kwargs)
#         return kwarg_dict


# class CallbackState(Enum):
#     NOT_SET = "not_set"
#     SUCCESS = "success"
#     FAIL = "fail"


# class ActionState(Enum):
#     NOT_SET = "not_set"
#     SUCCESS = "success"
#     RETRY = "retry"
#     FAIL = "fail"
#     CALLBACK_FAIL = "callback_fail"


# class AiohttpActionCallback:
#     def __init__(self, *args, **kwargs) -> None:
#         _, _ = args, kwargs
#         self.state: CallbackState = CallbackState.NOT_SET
#         self.state_message: str = ""

#     def success(self, caller: "AiohttpAction", msg: str = "", **kwargs):
#         _, _ = caller, kwargs
#         self.state = CallbackState.SUCCESS
#         self.state_message = msg

#     def fail(self, caller: "AiohttpAction", msg: str, **kwargs):
#         _ = kwargs
#         self.state = CallbackState.FAIL
#         self.state_message = msg
#         caller.update_state(ActionState.CALLBACK_FAIL, self.__class__.__name__, msg)

#     async def do_callback(self, caller: "AiohttpAction"):
#         raise NotImplementedError()


# class ActionObserver:
#     def __init__(self) -> None:
#         pass

#     def update(
#         self,
#         action: "AiohttpAction",
#         source: str,
#         msg: str,
#         **kwargs,
#     ):
#         _ = kwargs
#         print(action, source, msg)


# @dataclass
# class ActionCallbacks:
#     success: List[AiohttpActionCallback] = field(default_factory=list)
#     retry: List[AiohttpActionCallback] = field(default_factory=list)
#     fail: List[AiohttpActionCallback] = field(default_factory=list)


# class AiohttpAction:
#     def __init__(
#         self,
#         aiohttp_args: AiohttpRequest,
#         id_: str = "",
#         max_attempts: int = 1,
#         context: Optional[Dict] = None,
#         callbacks: Optional[ActionCallbacks] = None,
#         observers: Optional[List[ActionObserver]] = None,
#         retry_codes: Optional[List[int]] = None,
#     ) -> None:
#         self.aiohttp_args = aiohttp_args
#         self.id_ = id_
#         self.uid: UUID = uuid4()
#         self.max_attempts = max_attempts
#         self.context = optional_object(context, dict)
#         self.observers = optional_object(observers, list)
#         self.callbacks: ActionCallbacks = optional_object(callbacks, ActionCallbacks)
#         self.retry_codes = optional_object(retry_codes, list, [500, 502, 503, 504])
#         self.attempts: int = 0
#         self.response: Optional[ClientResponse] = None
#         self.response_data: Any = None
#         self.state: ActionState = ActionState.NOT_SET

#     def __str__(self) -> str:
#         if self.response is not None:
#             code: Optional[int] = self.response.status
#             reason = self.response.reason
#         else:
#             code = None
#             reason = None
#         return (
#             f"{self.__class__.__name__}("
#             f"state={self.state}, "
#             f"method={self.aiohttp_args.method!r}, url={self.aiohttp_args.url!r}, "
#             f"status_code={code!r}, reason={reason!r}"
#             ")"
#         )

#     async def do_action(self, session: ClientSession, queue: Optional[Queue] = None):
#         self.attempts += 1
#         try:

#             if self.attempts <= self.max_attempts or self.max_attempts == -1:
#                 async with session.request(**self.aiohttp_args.as_dict()) as response:
#                     self.response = response
#                     await self.check_response(queue)
#             else:
#                 logger.warning("Retry fail: %r retry_count:%s", self, self.attempts)
#                 await self.fail()
#         except Exception as ex:
#             logger.exception(
#                 "Exception: %s raised while doing action: %s",
#                 ex.__class__.__name__,
#                 self,
#             )
#             raise ex

#     async def check_response(self, queue: Optional[Queue]):
#         if self.response is not None:
#             if 200 <= self.response.status <= 299:
#                 await self.success()
#             elif self.response.status in self.retry_codes:
#                 await self.retry(queue)
#             else:
#                 await self.fail()
#         else:
#             logger.error(
#                 "Checked response before response recieved. This should not be possible."
#             )

#     async def success(self):
#         self.update_state(ActionState.SUCCESS, "action", self.response.status)
#         logger.debug("Successful response for %s", self)

#         for callback in self.callbacks.success:
#             try:
#                 await callback.do_callback(caller=self)
#             except Exception as ex:
#                 logger.exception(
#                     "Exception: %s during success callback: %s for action: %s",
#                     ex.__class__.__name__,
#                     callback,
#                     self,
#                 )
#                 raise ex

#     async def fail(self):
#         self.update_state(ActionState.FAIL, "action", str(self))
#         for callback in self.callbacks.fail:
#             try:
#                 await callback.do_callback(caller=self)
#             except Exception as ex:
#                 logger.exception(
#                     "Exception: %s during fail callback: %s for action: %r",
#                     ex.__class__.__name__,
#                     callback,
#                     self,
#                 )
#                 raise ex
#         logger.warning(
#             "Fail response for %r meta: %r", self, self.response_meta_to_dict()
#         )

#     async def retry(self, queue: Optional[Queue]):
#         self.update_state(
#             ActionState.RETRY,
#             "action",
#             f"Made {self.attempts} of {self.max_attempts} attempts.",
#         )
#         logger.info(
#             "Retrying %s Made %s of %s} attempts.",
#             self,
#             self.attempts,
#             self.max_attempts,
#         )
#         if queue is not None:
#             await queue.put(self)
#         else:
#             logger.info(
#                 "Could have retried this action if used with a queue. Action: %s",
#                 self,
#             )
#             await self.fail()
#             return
#         for callback in self.callbacks.retry:
#             try:
#                 await callback.do_callback(caller=self)
#             except Exception as ex:
#                 logger.exception(
#                     "Exception: %s during retry callback: %s for action: %s",
#                     ex.__class__.__name__,
#                     callback,
#                     self,
#                 )
#                 raise ex

#     def update_state(
#         self,
#         state: ActionState,
#         source: str,
#         msg: str,
#         **kwargs,
#     ):
#         self.state = state
#         for observer in self.observers:
#             observer.update(self, source, msg, **kwargs)

#     def response_meta_to_dict(self) -> Dict[str, Any]:
#         data: Dict[str, Any] = {}
#         if self.response is None:
#             return {}
#         request_headers = [
#             {key: value} for key, value in self.response.request_info.headers.items()
#         ]
#         response_headers = [
#             {key: value} for key, value in self.response.headers.items()
#         ]
#         data["version"] = self.response.version
#         data["status"] = self.response.status
#         data["reason"] = self.response.reason
#         data["cookies"] = self.response.cookies
#         data["response_headers"] = response_headers
#         data["request_info"] = {
#             "method": self.response.request_info.method,
#             "url": str(self.response.request_info.url),
#             "real_url": str(self.response.request_info.real_url),
#             "headers": request_headers,
#         }
#         return data


# class ResponseContentToJson(AiohttpActionCallback):
#     def __init__(self) -> None:
#         super().__init__()

#     async def do_callback(self, caller: AiohttpAction):
#         if caller.response is not None:
#             caller.response_data = await caller.response.json()
#             self.success(caller)
#             return
#         self.fail(caller, "Response is None.")


# def test_new_format():
#     aiohttp_args = AiohttpRequest(method="get", url="https://httpbin.org/get")
#     callbacks = ActionCallbacks(success=[ResponseContentToJson()])
#     action = AiohttpAction(aiohttp_args=aiohttp_args, callbacks=callbacks)
#     worker = AiohttpQueueWorker()
#     do_queue_runner([action], [worker])
#     print(action)
#     assert action.response.status == 200
#     assert False
