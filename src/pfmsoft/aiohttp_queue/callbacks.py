import csv
import json
import logging
from copy import deepcopy
from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Sequence

import aiofiles
from more_itertools import spy

from pfmsoft.aiohttp_queue import (
    AiohttpAction,
    AiohttpActionCallback,
    AiohttpQueueWorker,
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
            self.callback_success(caller)
            return
        self.callback_fail(caller, "Response is None.")


class ResponseContentToText(AiohttpActionCallback):
    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        if caller.response is not None:
            caller.result = await caller.response.text()
            self.callback_success(caller)
            return
        self.callback_fail(caller, "Response is None.")


class CheckForPages(AiohttpActionCallback):
    """Where page=<page number> is in query string, and x-pages is in response header.

    Assumes response data is a list
    """

    def __init__(self) -> None:
        super().__init__()

    async def do_callback(self, caller: AiohttpAction, *args, **kwargs):
        """"""
        if caller.response is None:
            return
        page_count = self.check_for_pages(caller, *args, **kwargs)
        if page_count is None:
            logger.warning(
                "No pages found for %s, Are you sure this api offers pages?",
                caller.response.real_url,
            )
            self.callback_fail(
                caller, "No pages found, Are you sure this api offers pages?"
            )
            return
        logger.info("Found %s pages for %s", page_count, caller)
        actions = []
        for page_number in range(2, page_count + 1):
            actions.append(self.make_new_action(caller, page_number, *args, **kwargs))
        await self.process_actions(caller, actions, *args, **kwargs)
        caller.context["pfmsoft_page_report"] = self.build_report(
            caller, actions, *args, **kwargs
        )
        self.handle_results(caller, actions, *args, **kwargs)
        self.callback_success(caller)

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
            max_attempts=caller.max_attempts,
            request_kwargs=deepcopy(caller.request_kwargs),
            name=str(caller.uid),
            id_=new_page,
            callbacks=ActionCallbacks(success=[ResponseContentToJson()]),
            observers=caller.observers,
        )
        params = new_action.request_kwargs.get("params", {})
        params["page"] = new_page
        new_action.request_kwargs["params"] = params
        logger.debug(
            "%s made %r to get page %s of %r",
            self.__class__.__name__,
            new_action,
            new_page,
            caller,
        )
        return new_action

    async def process_actions(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ):
        _, _ = args, kwargs
        worker_count = self.worker_count(caller, actions, *args, **kwargs)
        factories = [AiohttpQueueWorker() for _ in range(worker_count)]
        await queue_runner(actions, factories)

    def handle_results(
        self, caller: AiohttpAction, actions: Sequence[AiohttpAction], *args, **kwargs
    ):
        _, _ = args, kwargs
        if caller.response is None:
            return
        if not isinstance(caller.result, list):
            logger.warning(
                "Tried to append page data to a parent action with no result. url: %s uid: %s",
                caller.response.real_url,
                caller.uid,
            )
            return
        for action in actions:
            if action.response is None:
                return

            if action.response.status == 200:
                caller.result.extend(action.result)
                return
            logger.warning(
                (
                    "An attempt to get page data failed. Data is incomplete.\nUrl: %r \n"
                    "response: %s - %s"
                ),
                action.response.real_url,
                action.response.status,
                action.response.reason,
            )

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
        path_values: Optional[Dict[str, str]] = None,
        file_ending: str = "",
    ) -> None:
        super().__init__()
        self.file_path = Path(file_path)
        self.mode = mode
        self.path_values = optional_object(path_values, dict)
        self.file_ending = file_ending

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"file_path={self.file_path!r}, mode={self.mode!r}, "
            f"path_values={self.path_values!r}, file_ending={self.file_ending!r}, "
            ")"
        )

    def refine_path(self, caller: AiohttpAction, *args, **kwargs):
        """Refine the file path. Data from the AiohttpAction is available for use here."""
        _, _, _ = caller, args, kwargs
        if self.path_values is not None:
            template = Template(str(self.file_path))
            resolved_string = template.substitute(self.path_values)
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
                self.callback_success(caller)
        except Exception as ex:
            logger.exception(
                "Exception saving file to %s in action %s", self.file_path, caller
            )
            self.callback_fail(caller, f"Exception saving file to {self.file_path}")
            raise ex


class SaveJsonResultToFile(SaveResultToFile):
    """Usually used after ResponseToJson callback."""

    def __init__(
        self,
        file_path: Path,
        mode: str = "w",
        path_values: Optional[Dict[str, str]] = None,
        file_ending: str = ".json",
    ) -> None:
        super().__init__(
            file_path,
            mode=mode,
            path_values=path_values,
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
        path_values: Optional[Dict[str, str]] = None,
        file_ending: str = ".csv",
        field_names: Optional[List[str]] = None,
        additional_fields: Dict = None,
    ) -> None:
        super().__init__(
            file_path,
            mode=mode,
            path_values=path_values,
            file_ending=file_ending,
        )
        self.field_names = field_names
        self.additional_fields = additional_fields

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"file_path={self.file_path!r}, mode={self.mode!r}, "
            f"path_values={self.path_values!r}, file_ending={self.file_ending!r}, "
            f"field_names={self.field_names!r}, additional_fields={self.additional_fields!r}, "
            ")"
        )

    # def refine_path(self, caller: AiohttpAction, *args, **kwargs):
    #     """Refine the file path. Data from the AiohttpAction is available for use here."""
    #     # pass

    def get_data(self, caller: AiohttpAction, *args, **kwargs) -> List[Dict]:  # type: ignore
        """expects caller.result to be a List[Dict]."""
        _, _ = args, kwargs
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
                first, data_iter = spy(data)
                self.field_names = list(first[0].keys())
                data = data_iter
            with open(str(self.file_path), mode=self.mode) as file:
                writer = csv.DictWriter(file, fieldnames=self.field_names)
                writer.writeheader()
                for item in data:
                    writer.writerow(item)
            self.callback_success(caller)
        except Exception as ex:
            logger.exception(
                "Exception saving file to %s in action %s", self.file_path, caller
            )
            self.callback_fail(caller, f"Exception saving file to {self.file_path}")
            raise ex
