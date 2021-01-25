import re
import typing as t
from collections import defaultdict
from functools import partial
from urllib.parse import unquote

from .utils import regexize, parse


__version__ = "0.3.3"
__license__ = "MIT"


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

    NotFound: t.Type[Exception] = NotFound
    RouterError: t.Type[Exception] = RouterError
    MethodNotAllowed: t.Type[Exception] = MethodNotAllowed

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


# pylama: ignore=D
