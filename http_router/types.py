from __future__ import annotations

from typing import Any, Collection, Iterable, Pattern, TypeVar

THosts = Collection[str]
THostsArg = Iterable[str] | str
TMethods = Iterable[str]
TMethodsArg = TMethods | str
TPath = Pattern | str
TVObj = TypeVar("TVObj", bound=Any)
