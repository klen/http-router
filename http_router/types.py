from typing import Iterable, Pattern, TypeVar, Union

TMethods = Iterable[str]
TMethodsArg = Union[TMethods, str]
TPath = Union[str, Pattern]
TVMatch = TypeVar("TVMatch")
