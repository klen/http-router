from __future__ import annotations

import re
from typing import TYPE_CHECKING, Pattern
from uuid import UUID

if TYPE_CHECKING:
    from collections.abc import Callable

    from .types import THosts, THostsArg, TMethods, TMethodsArg, TPath, TVObj


def identity(v: TVObj) -> TVObj:
    """Identity function."""
    return v


def always_true(_: TVObj) -> bool:
    """Validator accepting any target."""
    return True


VAR_RE = re.compile(r"^(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<var_type>.+))?$")
VAR_TYPES = {
    "float": (r"\d+(\.\d+)?", float),
    "int": (r"\d+", int),
    "path": (r".*", str),
    "str": (r"[^/]+", str),
    "uuid": (r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", UUID),
}


def parse_path(path: TPath) -> tuple[str, Pattern | None, dict[str, Callable]]:
    """Prepare the given path to regexp it."""
    if isinstance(path, Pattern):
        return path.pattern, path, {}

    src, regex, path = path.strip(" "), "^", ""
    params: dict[str, Callable] = {}
    idx, cur, group = 0, 0, None
    while cur < len(src):
        sym = src[cur]
        cur += 1

        if sym == "{":
            if group:
                end = src.find("}", cur)
                cur = end + 1 if end != -1 else len(src)
                continue

            group = cur
            continue

        if sym == "}" and group:
            part = src[group : cur - 1]
            length = len(part)
            match = VAR_RE.match(part.strip())
            if match:
                opts = match.groupdict("str")
                var_type_re, params[opts["var"]] = VAR_TYPES.get(
                    opts["var_type"],
                    (opts["var_type"], identity),
                )
                regex += re.escape(src[idx : group - 1]) + f"(?P<{opts['var']}>{var_type_re})"
                path += src[idx : group - 1] + f"{{{opts['var']}}}"
                cur = idx = group + length + 1

            group = None

    if not path:
        return src, None, params

    regex += re.escape(src[idx:]) + "$"
    path += src[idx:]
    return path, re.compile(regex), params


def prepare_route_params(
    methods: TMethodsArg | None,
    hosts: THostsArg | None,
) -> tuple[TMethods | None, THosts | None]:
    if isinstance(methods, str):
        methods = [methods]

    if methods is not None:
        methods = {m.upper() for m in methods}

    if isinstance(hosts, str):
        hosts = {hosts}

    elif hosts is not None:
        hosts = set(hosts)

    return methods, hosts
