from __future__ import annotations

import dataclasses as dc
import abc
import re
import typing as t
from collections import defaultdict
from functools import partial
from urllib.parse import unquote

from .utils import regexize, parse


__version__ = "0.8.1"
__license__ = "MIT"

# Types
TYPE_METHODS = t.Union[t.Collection[str], str, None]
CB = t.TypeVar('CB', bound=t.Any)
CBV = t.Callable[[CB], bool]


__all__ = 'RouterError', 'NotFound', 'MethodNotAllowed', 'Route', 'DynamicRoute', 'Router'


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


class RouteMatch:
    """Keeping route matching data."""

    __slots__ = 'path', 'method', 'callback', 'path_params'

    def __init__(self, path: bool = False, method: bool = False,
                 callback: t.Any = None, path_params: t.Mapping[str, t.Any] = None):

        self.path = path
        self.method = method
        self.callback = callback
        self.path_params = path_params

    def __bool__(self):
        return self.path and self.method

    def __iter__(self):
        return iter([self.callback, self.path_params])

    def __str__(self):
        status = self.path and 200 or self.method and 404 or 405
        return f"RouteMatch {status} ({self.callback}, {self.path_params!r})"


@dc.dataclass  # type: ignore  # mypy issue: https://github.com/python/mypy/issues/5374
class BaseRoute(metaclass=abc.ABCMeta):

    pattern: str
    methods: t.Set[str] = dc.field(default_factory=lambda: set())

    def __lt__(self, route: BaseRoute):
        assert isinstance(route, BaseRoute), 'Only routes are supported'
        return self.path < route.path

    @property
    def path(self):
        return self.pattern

    @abc.abstractmethod
    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        raise NotImplementedError


@dc.dataclass
class Route(BaseRoute):
    """Base plain route class."""

    callback: t.Any = None

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        return RouteMatch(
            path == self.pattern, not self.methods or (method in self.methods), self.callback)


@dc.dataclass
class DynamicRoute(Route):
    """Base dynamic route class."""

    pattern: t.Union[str, t.Pattern]  # type: ignore

    def __post_init__(self):
        if isinstance(self.pattern, str):
            self.pattern: t.Pattern = re.compile(regexize(self.pattern))

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        match = self.pattern.match(path)  # type: ignore
        if not match:
            return RouteMatch(callback=self.callback)

        return RouteMatch(
            bool(match), not self.methods or method in self.methods,
            self.callback, {key: unquote(value) for key, value in match.groupdict('').items()}
        )

    @property
    def path(self):
        return self.pattern.pattern


@dc.dataclass
class Mount(BaseRoute):
    """Support for nested routers."""

    router: 'Router' = dc.field(default_factory=lambda: Router(), repr=False)

    def __post_init__(self):
        """Validate self prefix."""
        self.route = self.router.route
        prefix = parse(self.pattern)
        if isinstance(prefix, t.Pattern):
            raise self.router.RouterError("Prefix doesn't support regexp")

        if not prefix.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        self.pattern = prefix.rstrip('/')

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        if not path.startswith(self.pattern):
            return RouteMatch(False)

        try:
            cb, opts = self.router(path[len(self.pattern):], method=method)
            return RouteMatch(True, True, cb, opts)

        except self.router.NotFound:
            return RouteMatch(False)


@dc.dataclass
class Router:
    """Route HTTP queries."""

    trim_last_slash: bool = False
    validate_cb: CBV = dc.field(default=lambda cb: True, repr=False, hash=False, compare=False)

    NotFound: t.ClassVar[t.Type[Exception]] = NotFound
    RouterError: t.ClassVar[t.Type[Exception]] = RouterError
    MethodNotAllowed: t.ClassVar[t.Type[Exception]] = MethodNotAllowed

    def __post_init__(self):
        """Initialize the router."""
        self.plain: t.DefaultDict[str, t.List[BaseRoute]] = defaultdict(list)
        self.dynamic: t.List[BaseRoute] = list()

    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        """Found a callback for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip('/') or '/'

        methods: t.Set = set()
        for route in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match.path:
                methods |= route.methods
                if match.method:
                    return match

        if methods:
            raise self.MethodNotAllowed(path, method)

        raise self.NotFound(path, method)

    def __route__(self, root: 'Router', prefix: str, *paths: t.Any,
                  methods: TYPE_METHODS = None, **params):
        """Bind self as a nested router."""
        route = Mount(prefix, router=self)
        root.dynamic.append(route)
        return self

    def bind(self, callback: t.Any, *paths: str, methods: TYPE_METHODS = None, **opts):
        """Bind a callback to self."""
        if opts:
            callback = partial(callback, **opts)

        if not isinstance(methods, (list, tuple, set)):
            methods = [methods]  # type: ignore

        methods = set(m.upper() for m in methods if isinstance(m, str))

        for path in paths:
            pattern = parse(path)
            if isinstance(pattern, t.Pattern):
                self.dynamic.append(DynamicRoute(pattern, methods, callback))
                continue

            self.plain[pattern].append(Route(pattern, methods, callback))

    def route(self, path: t.Union[CB, str], *paths: str,
              methods: TYPE_METHODS = None, **opts) -> t.Callable:
        """Register a route."""

        def wrapper(callback: CB) -> CB:
            if hasattr(callback, '__route__'):
                callback.__route__(self, *paths, methods=methods, **opts)
                return callback

            if not self.validate_cb(callback):  # type: ignore
                raise self.RouterError('Invalid callback: %r' % callback)

            if not paths:
                raise self.RouterError('Invalid route. A HTTP Path is required.')

            self.bind(callback, *paths, methods=methods, **opts)
            return callback

        if isinstance(path, str):
            paths = (path, *paths)

        else:
            return wrapper(path)

        return wrapper

    def routes(self) -> t.List[BaseRoute]:
        """Get a list of self routes."""
        return sorted(self.dynamic + [r for routes in self.plain.values() for r in routes])


# pylama: ignore=D
