"""A semi-functional example. Loading and saving data in the app data dir.

manifest.json will support metadata for each file.

| Data directory format:
| app-data
|     static
|         schemas
|             schema-version
|                 schema.json
|                 <generated schema info>
|         data
|             schema-version
|             <static data>
|         manifest.json
|     dynamic
|         schema-version
|             history
|                 <market history data>
|         manifest.json

"""

# pylint: disable=empty-docstring, missing-function-docstring

from pathlib import Path
from string import Template
from typing import Callable, Dict, List, Optional, TypeVar, Union

from pfmsoft_aiohttp_queue.app_config import APP_DIR, LOGGER

logger = LOGGER
ROUTE: Dict = {
    "example_resource": {
        "sub_path": "static/schemas",
        "version": "schema-${version}",
        "file_name": "schema-${version}.json",
    }
}
"""Routes to file locations by key"""


def get_app_data_directory() -> Path:
    directory = Path(APP_DIR)
    return directory


def get_data_subpath(route_name: str, params: Optional[Dict] = None) -> Path:
    sub_path_template = ROUTE[route_name]["sub_path"]
    params = optional_object(params, dict)
    sub_path = Template(sub_path_template).substitute(params)
    return Path(sub_path)


def get_data_version(route_name: str, params: Optional[Dict] = None) -> Path:
    version_template = ROUTE[route_name]["version"]
    params = optional_object(params, dict)
    version = Template(version_template).substitute(params)
    return Path(version)


def get_data_filename(route_name: str, params: Optional[Dict] = None) -> str:
    route_template = ROUTE[route_name]["file_name"]
    params = optional_object(params, dict)
    file_name = Template(route_template).substitute(params)
    return file_name


def save_json_to_app_data(
    data, route_name: str, params: Optional[Dict] = None
) -> Optional[Path]:
    app_data_path = get_app_data_directory()
    sub_path = get_data_subpath(route_name, params)
    version = get_data_version(route_name, params)
    file_name = get_data_filename(route_name, params)
    file_path = app_data_path / sub_path / version / Path(file_name)
    try:
        save_json(data, file_path, parents=True)
    except Exception as ex:
        logger.error(
            "Unable to save %s with params: %s to path %s Error message: %s",
            route_name,
            params,
            file_path,
            ex,
        )
        raise ex
    return file_path


def load_json_from_app_data(
    route_name: str, params: Optional[Dict] = None
) -> Optional[Dict]:
    app_data_path = get_app_data_directory()
    sub_path = get_data_subpath(route_name, params)
    version = get_data_version(route_name, params)
    file_name = get_data_filename(route_name, params)
    file_path = app_data_path / sub_path / version / Path(file_name)
    try:
        data = load_json(file_path)
    except Exception as ex:
        logger.error(
            "Unable to load %s with params: %s to path %s\nError message: %s",
            route_name,
            params,
            file_path,
            ex,
        )
        raise ex
    return data


def clean_app_data():
    """
    [summary]
    clean out app data.
    save configs?

    [extended_summary]
    """
    pass


def app_data_info():
    """
    [summary]
    get info on app data. dates of downloads? schema version?
    make a manifest file in data directory.
    [extended_summary]
    """
    pass


def get_directory_versions(parent: Path) -> List[str]:
    """
    [summary]
    get list of directories
    strip out versions
    make a list
    [extended_summary]

    :param parent: [description]
    :type parent: Path
    :return: [description]
    :rtype: List[str]
    """
    # FIXME
    return ["1.7.15"]


def most_recent_version(versions: List[str]) -> str:
    # FIXME make smarter about 7 vs 10
    versions.sort()
    return versions[0]


def load_schema(version: str) -> Optional[Dict]:
    if version == "latest":
        schema_parent = get_data_subpath("schema")
        versions = get_directory_versions(schema_parent)
        version = most_recent_version(versions)
    schema = load_json_from_app_data("schema", {"version": version})
    return schema


T = TypeVar("T")


def optional_object(
    argument: Union[None, T], object_factory: Callable[..., T], *args, **kwargs
) -> T:
    """
    A convenience method for initializing optional arguments.

    Meant to be used when solving the problem of passing an object, e.g. a List
    when the object is expected to be a passed in list or a default empty list.
    So make the default value None, and call this function to initialize the object.

    .. code-block:: python

        @dataclass
        class SomeData:
            data_1: int
            data_2: str

        class MyClass:
            def __init__(
                self,
                arg1: int,
                arg2: Optional[List[str]] = None,
                arg3: Optional[Dict[str, int]] = None,
                arg4: Optional[SomeData] = None,
            ):
                default_somedata = {"data_1": 1, "data_2": "two"}
                self.arg1 = arg1
                self.arg2: List[str] = collection_utilities.optional_object(
                    arg2, list, ["a", "b", "c"]
                )
                self.arg3: Dict[str, int] = collection_utilities.optional_object(arg3, dict)
                self.arg4: SomeData = collection_utilities.optional_object(
                    arg4, SomeData, **default_somedata
                )

    :param argument: An argument that is an object that may be None.
    :param object_factory: Factory function used to create the object.
    :param `*args`: Optional arguments passed to factory function.
    :param `**kwargs`: Optional keyword arguments passed to factory function.
    :return: The initialized object.
    """

    if argument is None:
        return object_factory(*args, **kwargs)
    return argument


def save_json(*args, **kwargs):
    pass


def load_json(*args):
    return {}
