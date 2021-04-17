import logging
from asyncio.queues import Queue
from dataclasses import dataclass, field
from enum import Enum
from string import Template
from typing import Any, Dict, List, Literal, Optional, Sequence
from uuid import UUID, uuid4

from aiohttp import ClientResponse, ClientSession

from pfmsoft.aiohttp_queue.utilities import optional_object

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


HTTP_STATUS_CODES_TO_RETRY = [500, 502, 503, 504]


# class AiohttpQueueWorkerFactory:
#     def __init__(self) -> None:
#         self.worker_count = 0

#     def get_worker(self, queue: Queue, session: ClientSession):
#         async def consumer(queue):
#             while True:
#                 action: AiohttpAction = await queue.get()
#                 await action.do_action(session, queue)
#                 queue.task_done()

#         worker = consumer(queue)
#         return worker


class AiohttpQueueWorker:
    def __init__(self) -> None:
        self.uid = uuid4()
        self.task_count = 0

    async def consumer(self, queue: Queue, session: ClientSession):
        while True:
            action: AiohttpAction = await queue.get()
            try:
                self.task_count += 1
                await action.do_action(session, queue)
            except Exception as ex:
                logger.exception(
                    "Queue worker %s caught an exception from %r", self.uid, action
                )
            queue.task_done()


class CallbackState(Enum):
    NOT_SET = "not_set"
    SUCCESS = "success"
    FAIL = "fail"


class AiohttpActionCallback:
    def __init__(self, *args, **kwargs) -> None:
        _, _ = args, kwargs
        self.state: CallbackState = CallbackState.NOT_SET
        self.state_message: str = ""

    def callback_success(self, caller: "AiohttpAction", msg: str = "", **kwargs):
        _, _ = caller, kwargs
        self.state = CallbackState.SUCCESS
        self.state_message = msg

    def callback_fail(self, caller: "AiohttpAction", msg: str, **kwargs):
        _ = kwargs
        self.state = CallbackState.FAIL
        self.state_message = msg
        caller.update_state(ActionState.CALLBACK_FAIL, self)

    async def do_callback(self, caller: "AiohttpAction"):
        raise NotImplementedError()


class ActionObserver:
    def __init__(self) -> None:
        pass

    def update(
        self,
        action: "AiohttpAction",
        callback: Optional[AiohttpActionCallback] = None,
        **kwargs,
    ):
        _, _ = callback, kwargs
        print(action)


@dataclass
class ActionCallbacks:
    success: List[AiohttpActionCallback] = field(default_factory=list)
    retry: List[AiohttpActionCallback] = field(default_factory=list)
    fail: List[AiohttpActionCallback] = field(default_factory=list)


class ActionState(Enum):
    NOT_SET = "not_set"
    SUCCESS = "success"
    RETRY = "retry"
    FAIL = "fail"
    CALLBACK_FAIL = "callback_fail"


class AiohttpAction:
    """
    A self contained unit of execution
    """

    def __init__(
        self,
        method: str,
        url_template: str,
        url_parameters: Optional[Dict] = None,
        max_attempts: int = 1,
        context: Optional[Dict] = None,
        request_kwargs: Optional[Dict] = None,
        name: str = "",
        id_: Any = None,
        callbacks: Optional[ActionCallbacks] = None,
        observers: Optional[List[ActionObserver]] = None,
    ):
        self.name = name
        self.id_ = id_
        self.uid: UUID = uuid4()
        self.callbacks: ActionCallbacks = optional_object(callbacks, ActionCallbacks)
        self.method = method
        self.url_template = url_template
        self.url_parameters: Dict = optional_object(url_parameters, dict)
        self.url = Template(url_template).substitute(self.url_parameters)
        self.max_attempts = max_attempts
        self.response: Optional[ClientResponse] = None
        self.attempts: int = 0
        self.result: Any = None
        self.request_kwargs = optional_object(request_kwargs, dict)
        self.context = optional_object(context, dict)
        self.observers = optional_object(observers, list)
        self.state: ActionState = ActionState.NOT_SET

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"method={self.method!r}, url_template={self.url_template!r}, "
            f"url_parameters={self.url_parameters!r}, retry_limit={self.max_attempts!r}, "
            f"context={self.context!r}, request_kwargs={self.request_kwargs!r}, "
            f"name={self.name!r}, id_={self.id_!r}, callbacks={self.callbacks!r}, "
            f"observers={self.observers!r}"
            ")"
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"state={self.state}, "
            f"method={self.method!r}, url={self.url!r}, "
            f"request_kwargs={self.request_kwargs!r}"
            ")"
        )

    def _update(
        self,
        callback: Optional[AiohttpActionCallback] = None,
        **kwargs,
    ):
        for observer in self.observers:
            observer.update(self, callback, **kwargs)

    def update_state(
        self,
        state: ActionState,
        callback: Optional[AiohttpActionCallback] = None,
        **kwargs,
    ):
        self.state = state
        self._update(callback, **kwargs)

    async def success(self, *args, **kwargs):
        self.update_state(ActionState.SUCCESS)
        logger.debug("Successful response for %s", self)

        for callback in self.callbacks.success:
            try:
                await callback.do_callback(caller=self, *args, **kwargs)
            except Exception as ex:
                logger.exception(
                    "Exception: %s during success callback: %s for action: %s",
                    ex.__class__.__name__,
                    callback,
                    self,
                )
                raise ex

    async def fail(self, *args, **kwargs):
        self.update_state(ActionState.FAIL)
        logger.warning(
            "Fail response for %r meta: %r", self, self.response_meta_to_json
        )
        for callback in self.callbacks.fail:
            try:
                await callback.do_callback(caller=self, *args, **kwargs)
            except Exception as ex:
                logger.exception(
                    "Exception: %s during fail callback: %s for action: %s",
                    ex.__class__.__name__,
                    callback,
                    self,
                )
                raise ex

    async def retry(self, *args, **kwargs):
        self.update_state(ActionState.RETRY)
        for callback in self.callbacks.retry:
            try:
                await callback.do_callback(caller=self, *args, **kwargs)
            except Exception as ex:
                logger.exception(
                    "Exception: %s during retry callback: %s for action: %s",
                    ex.__class__.__name__,
                    callback,
                    self,
                )
                raise ex

    async def do_action(self, session: ClientSession, queue: Optional[Queue] = None):
        self.attempts += 1
        try:
            if self.attempts <= self.max_attempts or self.max_attempts == -1:
                async with session.request(
                    self.method, self.url, **self.request_kwargs
                ) as response:
                    self.response = response
                    await self.check_response(queue)
            else:
                logger.warning("Retry fail: %r retry_count:%s", self, self.attempts)
                await self.fail()
        except Exception as ex:
            logger.exception(
                "Exception: %s raised while doing action: %s",
                ex.__class__.__name__,
                self,
            )
            raise ex

    async def check_response(self, queue: Optional[Queue]):
        # FIXME split to class, handle more codes
        if self.response is not None:
            if self.response.status == 200:
                await self.success()
            elif self.response.status in HTTP_STATUS_CODES_TO_RETRY:
                # self.retry_count += 1
                logger.info(
                    "Retrying %s retry_count=%s, retry_limit=%s",
                    self,
                    self.attempts,
                    self.max_attempts,
                )
                if queue is not None:
                    await queue.put(self)
                    await self.retry()
                else:
                    logger.info(
                        "Could have retried this action if used with a queue. Action: %s",
                        self,
                    )
                    await self.fail()
            else:
                await self.fail()
        else:
            logger.error(
                "Checked response before response recieved. This should not be possible."
            )

    def response_meta_to_json(self) -> Optional[Dict[str, Any]]:
        data: Dict[str, Any] = {}
        if self.response is None:
            return None
        request_headers = [
            {key: value} for key, value in self.response.request_info.headers.items()
        ]
        response_headers = [
            {key: value} for key, value in self.response.headers.items()
        ]
        data["version"] = self.response.version
        data["status"] = self.response.status
        data["reason"] = self.response.reason
        data["cookies"] = self.response.cookies
        data["response_headers"] = response_headers
        data["request_info"] = {
            "method": self.response.request_info.method,
            "url": str(self.response.request_info.url),
            "real_url": str(self.response.request_info.real_url),
            "headers": request_headers,
        }
        return data
