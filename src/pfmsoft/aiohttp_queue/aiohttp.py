import logging
from asyncio.queues import Queue
from dataclasses import dataclass, field
from string import Template
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from aiohttp import ClientResponse, ClientSession

from pfmsoft.aiohttp_queue.utilities import optional_object

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


HTTP_STATUS_CODES_TO_RETRY = [500, 502, 503, 504]


class AiohttpQueueWorkerFactory:
    def __init__(self) -> None:
        pass

    def get_worker(self, queue: Queue, session: ClientSession):
        async def consumer(queue):
            while True:
                action: AiohttpAction = await queue.get()
                await action.do_action(session, queue)
                queue.task_done()

        worker = consumer(queue)
        return worker


class AiohttpActionCallback:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def do_callback(self, caller: "AiohttpAction", *args, **kwargs):
        raise NotImplementedError()


@dataclass
class ActionCallbacks:
    success: List[AiohttpActionCallback] = field(default_factory=list)
    retry: List[AiohttpActionCallback] = field(default_factory=list)
    fail: List[AiohttpActionCallback] = field(default_factory=list)


class AiohttpAction:
    """
    A self contained unit of execution
    """

    def __init__(
        self,
        method: str,
        url_template: str,
        url_parameters: Optional[Dict] = None,
        retry_limit: int = 0,
        context: Optional[Dict] = None,
        request_kwargs: Optional[Dict] = None,
        name: str = "",
        id_: Any = None,
        callbacks: Optional[ActionCallbacks] = None,
    ):
        self.name = name
        self.id_ = id_
        self.uid: UUID = uuid4()
        self.callbacks: ActionCallbacks = optional_object(callbacks, ActionCallbacks)
        self.method = method
        self.url_template = url_template
        self.url_parameters: Dict = optional_object(url_parameters, dict)
        self.url = Template(url_template).substitute(self.url_parameters)
        self.retry_limit = retry_limit
        self.response: Optional[ClientResponse] = None
        self.retry_count: int = 0
        self.result: Any = None
        self.request_kwargs = optional_object(request_kwargs, dict)
        self.context = optional_object(context, dict)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"method={self.method!r}, url_template={self.url_template!r}, "
            f"url_parameters={self.url_parameters!r}, retry_limit={self.retry_limit!r}, "
            f"context={self.context!r}, request_kwargs={self.request_kwargs!r}, "
            f"name={self.name!r}, id_={self.id_!r}, callbacks={self.callbacks!r}"
            ")"
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"method={self.method!r}, url={self.url!r}, "
            f"request_kwargs={self.request_kwargs!r}"
            ")"
        )

    async def success(self, *args, **kwargs):
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
        logger.info(
            "Retrying %s retry_count=%s, retry_limit=%s",
            self,
            self.retry_count,
            self.retry_limit,
        )
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
        try:
            if self.retry_count <= self.retry_limit or self.retry_limit == -1:
                async with session.request(
                    self.method, self.url, **self.request_kwargs
                ) as response:
                    self.response = response
                    await self.check_response(queue)
            else:
                logger.warning("Retry fail: %r retry_count:%s", self, self.retry_count)
                await self.fail()
        except Exception as ex:
            logger.exception(
                "Exception: %s raised while doing action: %s",
                ex.__class__.__name__,
                self,
            )
            raise ex

    async def check_response(self, queue: Optional[Queue]):
        if self.response is not None:
            if self.response.status == 200:
                await self.success()
            elif self.response.status in HTTP_STATUS_CODES_TO_RETRY:
                self.retry_count += 1
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
