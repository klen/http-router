from __future__ import annotations

from typing import Annotated, Any, Collection, Iterable, Pattern, TypeVar

THosts = Collection[str]
THostsArg = Iterable[str] | str
TMethods = Iterable[str]
TMethodsArg = TMethods | str
TPath = Pattern | str
TStr = Annotated[str, "also accepts str subclasses, e.g. StrEnum"]
TVObj = TypeVar("TVObj", bound=Any)
