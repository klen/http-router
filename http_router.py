import re
import typing as t
from collections import defaultdict
from functools import partial
from urllib.parse import unquote


__version__ = "0.2.0"
__license__ = "MIT"


DYNR_RE = re.compile(r'^\s*(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<re>.+))*\s*$')
METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATH"}

TYPE_METHODS = t.Union[t.Sequence, str, None]


__all__ = 'RouterError', 'NotFound', 'MethodNotAllowed', 'Route', 'DynamicRoute', 'Router'


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


class Route:
    """Base plain route class."""

    def __init__(
            self, pattern: str, methods: TYPE_METHODS = None) -> None:
        if not isinstance(methods, (list, tuple)):
            methods = [methods]

        self.methods = set([m.upper() for m in methods if isinstance(m, str)]) & METHODS
        self.pattern = pattern

    def match(self, path: str) -> t.Tuple[bool, t.Optional[t.Dict[str, str]]]:
        """Is the route match the path."""
        return path == self.pattern, None

    def __hash__(self) -> int:
        return hash(self.pattern)

    def __repr__(self) -> str:
        return "<%s %r %r>" % (self.__class__.__name__, self.methods, self.pattern)


class DynamicRoute(Route):
    """Base dynamic route class."""

    def __init__(
            self, pattern: t.Union[str, t.Pattern], methods: TYPE_METHODS = None) -> None:
        if isinstance(pattern, str):
            pattern = re.compile(regexize(pattern))
        self.regexp: t.Pattern = pattern
        super(DynamicRoute, self).__init__(self.regexp.pattern, methods)

    def match(self, path: str) -> t.Tuple[bool, t.Optional[t.Dict[str, str]]]:
        match = self.regexp.match(path)
        if not match:
            return False, None

        return bool(match), {key: unquote(value) for key, value in match.groupdict('').items()}


class Router:
    """Keep routes."""

    NotFound = NotFound
    RouterError = RouterError
    MethodNotAllowed = MethodNotAllowed

    def __init__(self, trim_last_slash: bool = False) -> None:
        self.trim_last_slash = trim_last_slash
        self.plain: t.Mapping[str, t.List] = defaultdict(list)
        self.dynamic: t.List = list()

    def __call__(self, path: str, method: str = "GET") -> t.Tuple[t.Callable, t.Mapping]:
        if self.trim_last_slash:
            path = path.rstrip('/') or '/'

        methods = set()
        for route, cb in self.plain.get(path, self.dynamic):
            match, path_params = route.match(path)
            if match:
                methods |= route.methods
                if route.methods and method not in route.methods:
                    continue

                return cb, {} if path_params is None else path_params

        if methods:
            raise self.MethodNotAllowed(path, method)

        raise self.NotFound(path, method)

    def bind(
            self, callback: t.Callable, *paths: str, methods: TYPE_METHODS = None, **opts) -> None:
        for path in paths:
            pattern = parse(path)
            if opts:
                callback = partial(callback, **opts)

            if isinstance(pattern, t.Pattern):
                self.dynamic.append((DynamicRoute(pattern, methods), callback))
                continue

            self.plain[pattern].append((Route(pattern, methods), callback))

    def route(
            self, path: t.Union[t.Callable, str], *paths: str,
            methods: TYPE_METHODS = None, **opts) -> t.Callable:
        """Register a route."""

        if callable(path):
            raise RouterError('`route` cannot be used as a decorator without params (paths)')

        def wrapper(callback):
            self.bind(callback, path, *paths, methods=methods, **opts)
            return callback

        return wrapper


def regexize(path: str) -> str:
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


# pylama: ignore=D
