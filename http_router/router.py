from __future__ import annotations

import typing as t
from collections import defaultdict
from functools import partial, lru_cache

from . import NotFound, RouterError, MethodNotAllowed  # noqa
from .utils import parse_path
from .typing import CB, TYPE_METHODS, TYPE_PATH


class Router:
    """Route HTTP queries."""

    NotFound: t.ClassVar[t.Type[Exception]] = NotFound                  # noqa
    RouterError: t.ClassVar[t.Type[Exception]] = RouterError            # noqa
    MethodNotAllowed: t.ClassVar[t.Type[Exception]] = MethodNotAllowed  # noqa

    def __init__(self, trim_last_slash: bool = False,
                 validator: t.Callable[[t.Any], bool] = None, converter: t.Callable = None):
        """Initialize the router.

        :param trim_last_slash: Ignore a last slash
        :param validator: Validate objects to route
        :param converter: Convert objects to route

        """
        self.trim_last_slash = trim_last_slash
        self.validator = validator or (lambda v: True)
        self.converter = converter or (lambda v: v)
        self.plain: t.DefaultDict[str, t.List[Route]] = defaultdict(list)
        self.dynamic: t.List[Route] = list()

    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip('/')

        match = self.match(path, method)
        if not match.path:
            raise self.NotFound(path, method)

        if not match.method:
            raise self.MethodNotAllowed(path, method)

        return match

    def __route__(self, root: Router, prefix: str, *paths: t.Any,
                  methods: TYPE_METHODS = None, **params):
        """Bind self as a nested router."""
        route = Mount(prefix, set(), router=self)
        root.dynamic.insert(0, route)
        return self

    @lru_cache(maxsize=1024)
    def match(self, path: str, method: str) -> RouteMatch:
        """Search a matched target for the given path and method."""
        neighbour = None
        for route in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match.path:
                if match.method:
                    return match
                neighbour = match

        return RouteMatch(False, False) if neighbour is None else neighbour

    def bind(self, target: t.Any, *paths: TYPE_PATH, methods: TYPE_METHODS = None, **opts):
        """Bind a target to self."""
        if opts:
            target = partial(target, **opts)

        if isinstance(methods, str):
            methods = [methods]

        if methods is not None:
            methods = set(m.upper() for m in methods or [])

        routes = []

        for path in paths:
            if self.trim_last_slash and isinstance(path, str):
                path = path.rstrip('/')

            path, pattern, params = parse_path(path)

            if pattern:
                route: Route = DynamicRoute(
                    path, methods=methods, target=target, pattern=pattern, params=params)
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

            target = self.converter(target)
            self.bind(target, *paths, methods=methods, **opts)
            return target

        if isinstance(path, TYPE_PATH.__args__):  # type: ignore
            paths = (path, *paths)

        else:
            return wrapper(path)  # type: ignore

        return wrapper

    def routes(self) -> t.List[Route]:
        """Get a list of self routes."""
        return sorted(self.dynamic + [r for routes in self.plain.values() for r in routes])

    def __getattr__(self, method: str) -> t.Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)


from .routes import RouteMatch, Route, DynamicRoute, Mount  # noqa

# pylama: ignore=D
