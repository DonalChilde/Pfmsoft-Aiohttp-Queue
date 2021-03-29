import logging
from typing import Callable, TypeVar, Union

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


T = TypeVar("T")  # pylint: disable=invalid-name


def optional_object(
    argument: Union[None, T], object_factory: Callable[..., T], *args, **kwargs
) -> T:
    """
    A convenience method for initializing optional arguments.

    Meant to be used when solving the problem of passing an object, e.g. a List
    when the object is expected to be a passed in list or a default empty list.
    So make the default value None, and call this function to initialize the object.

    :example:
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
