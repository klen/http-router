import re
import typing as t
from uuid import UUID

from ._types import TYPE_PATH


INDENTITY = lambda v: v  # noqa
PARAM_RE = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]+)(:[^>]+)?>")
PARAM_TYPES = {
    'float': (r"\d+(\.\d+)?", float),
    'int': (r"\d+", int),
    'path': (r".*", str),
    'str': (r"[^/]+", str),
    'uuid': (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", UUID)
}


def parse_path(path: TYPE_PATH) -> t.Tuple[str, t.Optional[t.Pattern], t.Dict[str, type]]:
    """Prepare the given path to regexp it."""
    if isinstance(path, t.Pattern):
        return path.pattern, path, {}

    source, path, regex, idx, convertors = path.strip(' '), '', '^', 0, {}
    for match in PARAM_RE.finditer(source):
        pname, ptype = match.groups('str')
        ptype = ptype.lstrip(':')
        tregex, convertors[pname] = PARAM_TYPES.get(ptype, (ptype, INDENTITY))
        regex += re.escape(source[idx:match.start()])
        regex += f"(?P<{pname}>{tregex})"
        path += source[idx:match.start()]
        path += f"<{pname}>"

        idx = match.end()

    if not path:
        return source, None, convertors

    regex += re.escape(source[idx:]) + '$'
    path += source[idx:]
    return path, re.compile(regex), convertors
