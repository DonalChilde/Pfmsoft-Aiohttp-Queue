import csv
import json
import logging
import re
from copy import deepcopy
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Sequence, Union

import aiofiles
from aiohttp.client_reqrep import ClientResponse

from pfmsoft.aiohttp_queue import (
    AiohttpAction,
    AiohttpActionCallback,
    AiohttpQueueWorkerFactory,
)
from pfmsoft.aiohttp_queue.aiohttp import ActionCallbacks
from pfmsoft.aiohttp_queue.runners import queue_runner
from pfmsoft.aiohttp_queue.utilities import combine_dictionaries, optional_object

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# pylint: disable=[useless-super-delegation,no-self-use]


class ResponseContentToJson(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        if caller.response is not None:
            caller.result = await caller.response.json()


class ResponseContentToText(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        if caller.response is not None:
            caller.result = await caller.response.text()


class LogSuccess(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        logger.info("Success: %s", caller)


class LogFail(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        logger.warning("Fail: %s", caller)


class LogRetry(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        logger.info("Retry: %s", caller)


class CheckForPages(AiohttpActionCallback):
    """Where page=<page number> is in query string, and x-pages is in response header."""

    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        """
        - check for pages
        - copy action, with new page request,
        - add to list of child actions? use context variable?
        - add action to queue

        [extended_summary]

        :param caller: [description]
        :type caller: AiohttpAction
        """
        await self.collect_all_pages(caller, *args, **kwargs)

    async def collect_all_pages(self, caller: AiohttpAction, *args, **kwargs):
        _, _ = args, kwargs
        page_count = self.check_for_pages(caller, *args, **kwargs)
        if page_count is None:
            return
        actions = []
        for page_number in range(2, page_count + 1):
            actions.append(self.make_new_action(caller, page_number, *args, **kwargs))
        await self.process_actions(caller, actions, *args, **kwargs)

        caller.context["pfmsoft_page_report"] = self.build_report(
            caller, actions, *args, **kwargs
        )
        self.handle_results(caller, actions, *args, **kwargs)

    def build_report(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ):
        _, _ = args, kwargs
        caller_report = self.build_page_report(caller)
        reports = []
        reports.append(caller_report)
        for action in actions:
            reports.append(self.build_page_report(action))
        return reports

    def build_page_report(self, action: AiohttpAction):
        if action.response is not None:
            params = action.request_kwargs.get("params", {})
            page_num = int(params.get("page", "1"))
            if action.response.status != 200:
                count = -1
            else:
                count = len(action.result)
            action_report = {
                "uid": str(action.uid),
                "page": page_num,
                "count": count,
                "msg": f"Status: {action.response.status} msg: {action.response.reason}",
            }
            return action_report
        return {}

    def check_for_pages(self, caller: AiohttpAction, *args, **kwargs) -> Optional[int]:
        _, _ = args, kwargs
        response = caller.response
        if response is not None:
            pages = response.headers.get("x-pages", None)
            if pages is not None:
                page_int = int(pages)
                logger.info("%s pages reported for action.uid:%s", pages, caller.uid)
                return page_int
        return None

    def make_new_action(
        self, caller: AiohttpAction, new_page: int, *args, **kwargs
    ) -> AiohttpAction:
        _, _ = args, kwargs
        new_action = AiohttpAction(
            method=caller.method,
            url_template=caller.url_template,
            url_parameters=deepcopy(caller.url_parameters),
            retry_limit=caller.retry_limit,
            request_kwargs=deepcopy(caller.request_kwargs),
            name=str(caller.uid),
            id_=new_page,
            callbacks=ActionCallbacks(success=[ResponseContentToJson()]),
        )
        params = new_action.request_kwargs.get("params", {})
        params["page"] = new_page
        new_action.request_kwargs["params"] = params
        logger.info(
            "%s made action.uid=%s to get page %s of action.uid=%s",
            self.__class__.__name__,
            new_action.uid,
            new_page,
            caller.uid,
        )
        return new_action

    async def process_actions(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ):
        _, _ = args, kwargs
        factory_count = self.worker_count(caller, actions, *args, **kwargs)
        factories = [AiohttpQueueWorkerFactory() for _ in range(factory_count)]
        await queue_runner(actions, factories)

    def handle_results(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ):
        _, _ = args, kwargs
        for action in actions:
            caller.result.extend(action.result)

    def worker_count(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ) -> int:
        _, _, _, _ = caller, actions, args, kwargs
        return 5


class SaveResultToFile(AiohttpActionCallback):
    """Usually used after ResponseToText callback"""

    def __init__(
        self,
        file_path: Path,
        mode: str = "w",
        template_params: Optional[Dict[str, str]] = None,
        file_ending: str = "",
    ) -> None:
        super().__init__()
        self.file_path = Path(file_path)
        self.mode = mode
        self.template_params = optional_object(template_params, dict)
        self.file_ending = file_ending

    def refine_path(self, caller: AiohttpAction, *args, **kwargs):
        """Refine the file path. Data from the AiohttpAction is available for use here."""
        if self.template_params is not None:
            template = Template(str(self.file_path))
            resolved_string = template.substitute(self.template_params)
            self.file_path = Path(resolved_string)
        if self.file_ending != "":
            if self.file_path.suffix != self.file_ending:
                self.file_path = self.file_path.with_suffix(self.file_ending)

    def get_data(self, caller: AiohttpAction, *args, **kwargs) -> str:
        """expects caller.result to be a string."""
        _ = args
        _ = kwargs
        data = caller.result
        return data

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        self.refine_path(caller, *args, **kwargs)
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(
                str(self.file_path), mode=self.mode
            ) as file:  # type:ignore
                data = self.get_data(caller, args, kwargs)
                await file.write(data)
        except Exception as ex:
            logger.exception(
                "Exception saving file to %s in action %s", self.file_path, caller
            )
            raise ex


class SaveJsonResultToFile(SaveResultToFile):
    """Usually used after ResponseToJson callback."""

    def __init__(
        self,
        file_path: Path,
        mode: str = "w",
        template_params: Optional[Dict[str, str]] = None,
        file_ending: str = ".json",
    ) -> None:
        super().__init__(
            file_path,
            mode=mode,
            template_params=template_params,
            file_ending=file_ending,
        )

    def get_data(self, caller: AiohttpAction, *args, **kwargs) -> str:
        """expects data (caller.result in super) to be json."""
        data = super().get_data(caller, *args, **kwargs)
        json_data = json.dumps(data, indent=2)
        return json_data


class SaveListOfDictResultToCSVFile(SaveResultToFile):
    """Save the result to a CSV file.

    Expects the result to be a List[Dict].
    """

    def __init__(
        self,
        file_path: Path,
        mode: str = "w",
        template_params: Optional[Dict[str, str]] = None,
        file_ending: str = ".csv",
        field_names: Optional[List[str]] = None,
        additional_fields: Dict = None,
    ) -> None:
        super().__init__(
            file_path,
            mode=mode,
            template_params=template_params,
            file_ending=file_ending,
        )
        self.field_names = field_names
        self.additional_fields = additional_fields

    # FIXME move this to Aiohttp-Queue
    # def __init__(
    #     self,
    #     file_path: str,
    #     mode: str = "w",
    #     field_names: Optional[List[str]] = None,
    #     additional_fields: Dict = None,
    # ) -> None:
    #     super().__init__()
    #     self.file_path = Path(file_path)
    #     self.mode = mode
    #     self.field_names = field_names
    #     self.additional_fields = additional_fields

    def refine_path(self, caller: AiohttpAction, *args, **kwargs):
        """Refine the file path. Data from the AiohttpAction is available for use here."""
        # pass

    def get_data(self, caller: AiohttpAction, *args, **kwargs) -> List[Dict]:  # type: ignore
        """expects caller.result to be a List[Dict]."""
        _ = args
        _ = kwargs
        data = caller.result
        if self.additional_fields is not None:
            combined_data = []
            for item in data:
                combined_data.append(
                    combine_dictionaries(item, [self.additional_fields])
                )
            return combined_data
        return data

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        self.refine_path(caller, *args, **kwargs)
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.get_data(caller, args, kwargs)
            if self.field_names is None:
                self.field_names = list(data[0].keys())
            with open(str(self.file_path), mode=self.mode) as file:
                writer = csv.DictWriter(file, fieldnames=self.field_names)
                writer.writeheader()
                for item in data:
                    writer.writerow(item)
        except Exception as ex:
            logger.exception(
                "Exception saving file to %s in action %s", self.file_path, caller
            )
            raise ex


# class ResponseMetaToJson(AiohttpActionCallback):
#     def __init__(self, *args, **kwargs) -> None:
#         super().__init__(*args, **kwargs)

#     async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
#         response_info = self.response_to_json(caller)
#         caller.context["pfmsoft"]["response_info"] = response_info

#     def response_to_json(self, caller: AiohttpAction) -> Dict:
#         response: Optional[ClientResponse] = caller.response
#         data: Dict[str, Any] = {}
#         if response is None:
#             data = {"error": "response to json called before response recieved."}
#             return data
#         info = response.request_info
#         request_headers = [{key: value} for key, value in info.headers.items()]
#         response_headers = [{key: value} for key, value in response.headers.items()]
#         data["version"] = response.version
#         data["status"] = response.status
#         data["reason"] = response.reason
#         data["method"] = info.method
#         data["url"] = str(info.url)
#         data["real_url"] = str(info.real_url)
#         data["cookies"] = response.cookies
#         data["request_headers"] = request_headers
#         data["response_headers"] = response_headers
#         return data
