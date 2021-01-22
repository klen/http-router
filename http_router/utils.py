"""HTTP Router Utils."""

import typing as t
import re

DYNR_RE = re.compile(r'^\s*(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<re>.+))*\s*$')


def regexize(path: str) -> str:
    """Prepare the given path to regexp it."""
    path = path.strip(' ')
    idx, group = 0, None
    start, end = '{', '}'
    while idx < len(path):
        sym = path[idx]
        idx += 1

        if sym == start:
            if group:
                idx = path.find(end, idx) + 1
                continue

            group = idx
            continue

        if sym == end and group:
            part = path[group: idx - 1]
            match = DYNR_RE.match(part)
            if match:
                params = match.groupdict()
                params['re'] = params['re'] or '[^/]+'
                restr = '(?P<%s>%s)' % (params['var'], params['re'].strip())
                path = path[:group - 1] + restr + path[idx:]
                idx = group + len(restr)

            group = None

    return path.rstrip('$')


def parse(path: str) -> t.Union[str, t.Pattern]:
    """Parse URL path and convert it to regexp if needed."""
    pattern = regexize(path)
    parsed = re.sre_parse.parse(pattern)  # type: ignore
    for case, _ in parsed:
        if case not in (re.sre_parse.LITERAL, re.sre_parse.ANY):  # type: ignore
            return re.compile('%s$' % pattern)

    return pattern
