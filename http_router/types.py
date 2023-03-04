from __future__ import annotations

from typing import Any, Iterable, Pattern, TypeVar, Union

TMethods = Iterable[str]
TMethodsArg = Union[TMethods, str]
TPath = Union[str, Pattern]
TVObj = TypeVar("TVObj", bound=Any)
