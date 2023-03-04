from collections import defaultdict
from functools import lru_cache, partial
from typing import Any, Callable, ClassVar, DefaultDict, List, Optional, Type, Union

from .types import TMethodsArg, TPath, TVObj
from .utils import parse_path
from .exceptions import InvalidMethodError, NotFoundError, RouterError


cdef class Router:
    """Route HTTP queries."""

    NotFoundError: ClassVar[Type[Exception]] = NotFoundError            # noqa
    RouterError: ClassVar[Type[Exception]] = RouterError                # noqa
    InvalidMethodError: ClassVar[Type[Exception]] = InvalidMethodError  # noqa

    def __init__(
            self,
            bint trim_last_slash=False,
            object validator=None,
            object converter=None
    ):
        """Initialize the router."""
        self.trim_last_slash = trim_last_slash
        self.validator = validator or (lambda v: True)
        self.converter = converter or (lambda v: v)
        self.plain: Dict[str, List[Route]] = {}
        self.dynamic: List[Route] = []

    def __call__(self, str path, str method="GET") -> 'RouteMatch':
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip('/')

        match = self.match(path, method)

        if match is None:
            raise self.NotFoundError(path, method)

        if not match.method:
            raise self.InvalidMethodError(path, method)

        return match

    def __route__(self, root: 'Router', prefix: str, *paths: Any,
                  methods: TMethodsArg = None, **params):
        """Bind self as a nested router."""
        route = Mount(prefix, set(), router=self)
        root.dynamic.insert(0, route)
        return self

    @lru_cache(maxsize=1024)
    def match(self, str path, str method) -> 'RouteMatch':
        """Search a matched target for the given path and method."""
        cdef list routes = self.plain.get(path, self.dynamic)
        cdef RouteMatch match, neighbor = None
        cdef Route route

        for route in routes:
            match = route.match(path, method)
            if match.path:
                if match.method:
                    return match
                neighbor = match

        return neighbor

    def bind(self, target: Any, *paths: TPath, methods: Optional[TMethodsArg] = None, **opts):
        """Bind a target to self."""
        if opts:
            target = partial(target, **opts)

        if isinstance(methods, str):
            methods = [methods]

        if methods:
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
                self.plain.setdefault(path, [])
                self.plain[path].append(route)

            routes.append(route)

        return routes

    def route(
        self,
        *paths: TPath,
        methods: Optional[TMethodsArg] = None,
        **opts
    ):
        """Register a route."""

        def wrapper(target: TVObj) -> TVObj:
            if hasattr(target, '__route__'):
                target.__route__(self, *paths, methods=methods, **opts)
                return target

            if not self.validator(target):  # type: ignore
                raise self.RouterError('Invalid target: %r' % target)

            target = self.converter(target)
            self.bind(target, *paths, methods=methods, **opts)
            return target

        return wrapper

    def routes(self) -> List['Route']:
        """Get a list of self routes."""
        return sorted(self.dynamic + [r for routes in self.plain.values() for r in routes])

    def __getattr__(self, method: str) -> Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)


from .routes cimport DynamicRoute, Mount, Route, RouteMatch  # noqa

# pylama: ignore=D
