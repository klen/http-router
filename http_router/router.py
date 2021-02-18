from __future__ import annotations

import typing as t
from collections import defaultdict
from functools import partial, lru_cache

from . import NotFound, RouterError, MethodNotAllowed  # noqa
from .utils import parse_path
from ._types import CBV, CB, TYPE_METHODS, TYPE_PATH


class Router:
    """Route HTTP queries."""

    NotFound: t.ClassVar[t.Type[Exception]] = NotFound                  # noqa
    RouterError: t.ClassVar[t.Type[Exception]] = RouterError            # noqa
    MethodNotAllowed: t.ClassVar[t.Type[Exception]] = MethodNotAllowed  # noqa

    def __init__(self, trim_last_slash: bool = False, validator: CBV = None):
        """Initialize the router."""
        self.trim_last_slash = trim_last_slash
        self.validator = validator or (lambda v: True)
        self.plain: t.DefaultDict[str, t.List[BaseRoute]] = defaultdict(list)
        self.dynamic: t.List[BaseRoute] = list()

    @lru_cache(maxsize=1024)
    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip('/') or '/'

        methods: t.Set = set()
        for route in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match.path:
                if match.method:
                    return match
                methods |= route.methods

        if methods:
            raise self.MethodNotAllowed(path, method, methods)

        raise self.NotFound(path, method)

    def __route__(self, root: Router, prefix: str, *paths: t.Any,
                  methods: TYPE_METHODS = None, **params):
        """Bind self as a nested router."""
        route = Mount(prefix, router=self)
        root.dynamic.insert(0, route)
        return self

    def bind(self, target: t.Any, *paths: TYPE_PATH, methods: TYPE_METHODS = None, **opts):
        """Bind a target to self."""
        if opts:
            target = partial(target, **opts)

        if isinstance(methods, str):
            methods = [methods]

        methods = set(m.upper() for m in methods or [])
        routes = []

        for path in paths:
            path, pattern, params = parse_path(path)

            if pattern:
                route: Route = DynamicRoute(path=path, methods=methods,
                                            target=target, pattern=pattern, params=params)
                self.dynamic.append(route)

            else:
                route = Route(path, methods, target)
                self.plain[path].append(route)

            routes.append(route)

        return routes

    def route(self, path: t.Union[CB, TYPE_PATH], *paths: TYPE_PATH,
              methods: TYPE_METHODS = None, **opts) -> t.Callable:
        """Register a route."""

        def wrapper(target: CB) -> CB:
            if hasattr(target, '__route__'):
                target.__route__(self, *paths, methods=methods, **opts)
                return target

            if not self.validator(target):  # type: ignore
                raise self.RouterError('Invalid target: %r' % target)

            if not paths:
                raise self.RouterError('Invalid route. A HTTP Path is required.')

            self.bind(target, *paths, methods=methods, **opts)
            return target

        if isinstance(path, TYPE_PATH.__args__):  # type: ignore
            paths = (path, *paths)

        else:
            return wrapper(path)  # type: ignore

        return wrapper

    def routes(self) -> t.List[BaseRoute]:
        """Get a list of self routes."""
        return sorted(self.dynamic + [r for routes in self.plain.values() for r in routes])

    def __getattr__(self, method: str) -> t.Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)


from .routes import BaseRoute, RouteMatch, Route, DynamicRoute, Mount  # noqa

# pylama: ignore=D
