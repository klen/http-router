import typing as t
from collections import defaultdict
from functools import partial, lru_cache

from . import NotFound, RouterError, MethodNotAllowed  # noqa
from .utils import parse_path
from .typing import CBV, CB, TYPE_METHODS, TYPE_PATH


cdef class Router:
    """Route HTTP queries."""

    NotFound: t.ClassVar[t.Type[Exception]] = NotFound                  # noqa
    RouterError: t.ClassVar[t.Type[Exception]] = RouterError            # noqa
    MethodNotAllowed: t.ClassVar[t.Type[Exception]] = MethodNotAllowed  # noqa

    def __init__(self, bint trim_last_slash=False, object validator=None, object converter=None):
        """Initialize the router."""
        self.trim_last_slash = trim_last_slash
        self.validator = validator or (lambda v: True)
        self.converter = converter or (lambda v: v)
        self.plain: t.Dict[str, t.List[Route]] = {}
        self.dynamic: t.List[Route] = []

    def __call__(self, str path, str method="GET") -> 'RouteMatch':
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip('/')

        match = self.match(path, method)

        if match is None:
            raise self.NotFound(path, method)

        if not match.method:
            raise self.MethodNotAllowed(path, method)

        return match

    def __route__(self, root: 'Router', prefix: str, *paths: t.Any,
                  methods: TYPE_METHODS = None, **params):
        """Bind self as a nested router."""
        route = Mount(prefix, set(), router=self)
        root.dynamic.insert(0, route)
        return self

    def __getattr__(self, method: str) -> t.Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)

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

    def bind(self, target: t.Any, *paths: TYPE_PATH, methods: TYPE_METHODS = None, **opts):
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

    def route(self, path: t.Union[CB, TYPE_PATH], *paths: TYPE_PATH,
              methods: TYPE_METHODS = None, **opts) -> t.Any:
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

    def routes(self) -> t.List['Route']:
        """Get a list of self routes."""
        return sorted(self.dynamic + [r for routes in self.plain.values() for r in routes])


from .routes cimport RouteMatch, Route, DynamicRoute, Mount  # noqa

# pylama: ignore=D
