import re
import typing as t
from uuid import UUID

from ._types import TYPE_PATH


INDENTITY = lambda v: v  # noqa


VAR_RE = re.compile(r'^(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<var_type>.+))?$')
VAR_TYPES = {
    'float': (r"\d+(\.\d+)?", float),
    'int': (r"\d+", int),
    'path': (r".*", str),
    'str': (r"[^/]+", str),
    'uuid': (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", UUID)
}


def parse_path(path: TYPE_PATH) -> t.Tuple[str, t.Optional[t.Pattern], t.Dict[str, t.Callable]]:
    """Prepare the given path to regexp it."""
    if isinstance(path, t.Pattern):
        return path.pattern, path, {}

    src, regex, path = path.strip(' '), '^', ''
    params = {}
    idx, cur, group = 0, 0, None
    while cur < len(src):
        sym = src[cur]
        cur += 1

        if sym == '{':
            if group:
                cur = src.find('}', cur) + 1
                continue

            group = cur
            continue

        if sym == '}' and group:
            part = src[group: cur - 1]
            length = len(part)
            match = VAR_RE.match(part.strip())
            if match:
                opts = match.groupdict('str')
                var_type_re, params[opts['var']] = VAR_TYPES.get(
                    opts['var_type'], (opts['var_type'], INDENTITY))
                regex += re.escape(src[idx:group - 1]) + f"(?P<{ opts['var'] }>{ var_type_re })"
                path += src[idx:group - 1] + f"{{{opts['var']}}}"
                cur = idx = group + length + 1

            group = None

    if not path:
        return src, None, params

    regex += re.escape(src[idx:]) + '$'
    path += src[idx:]
    return path, re.compile(regex), params
