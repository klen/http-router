from __future__ import annotations

from typing import Any, Iterable, Pattern, TypeVar

TMethods = Iterable[str]
TMethodsArg = TMethods | str
TPath = Pattern | str
TVObj = TypeVar("TVObj", bound=Any)
