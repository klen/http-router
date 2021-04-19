import typing as t
from urllib.parse import unquote
from collections.abc import Iterator

from .router import Router
from .utils import parse_path, INDENTITY


cdef class RouteMatch:
    """Keeping route matching data."""

    def __init__(self, path: bool = False, method: bool = False,
                 target: t.Any = None, path_params: t.Mapping[str, t.Any] = None):

        self.path = path
        self.method = method
        self.target = target
        self.path_params = path_params

    def __bool__(self) -> bool:
        return self.path and self.method

    def __iter__(self) -> Iterator:
        return iter((self.target, self.path_params))

    def __str__(self) -> str:
        status = self.path and 200 or self.method and 404 or 405
        return f"RouteMatch {status} ({self.target}, {self.path_params!r})"


cdef class BaseRoute:

    def __init__(self, path: str, methods: t.Sequence[str] = None):
        self.path = path
        self.methods = set(methods or set())

    def __lt__(self, route: 'BaseRoute') -> bool:
        assert isinstance(route, BaseRoute), 'Only routes are supported'
        return self.path < route.path

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        raise NotImplementedError


cdef class Route(BaseRoute):
    """Base plain route class."""

    def __init__(self, path: str, methods: t.Sequence[str] = None, target: t.Any = None):
        super(Route, self).__init__(path, methods)
        self.target = target

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        return RouteMatch(
            path == self.path,
            not self.methods or method in self.methods, self.target)


cdef class DynamicRoute(Route):
    """Base dynamic route class."""

    def __init__(self, path: t.Union[str, t.Pattern], methods: t.Sequence[str] = None,
                 target: t.Any = None, pattern: t.Pattern = None, params: t.Dict = None):

        if pattern is None:
            path, pattern, params = parse_path(path)
            assert pattern, 'Invalid path'

        self.pattern = pattern
        self.params = params

        super(DynamicRoute, self).__init__(path, methods, target)

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        match = self.pattern.match(path)  # type: ignore  # checked in __post_init__
        if not match:
            return RouteMatch(target=self.target)

        path_params = {
            key: self.params.get(key, INDENTITY)(unquote(value))
            for key, value in match.groupdict().items()
        }

        return RouteMatch(
            bool(match), not self.methods or method in self.methods,
            self.target, path_params
        )


cdef class Mount(BaseRoute):
    """Support for nested routers."""

    def __init__(self, path: str, methods: t.Sequence[str] = None, router: Router = None):
        """Validate self prefix."""
        self.router = router or Router()
        self.route = self.router.route
        path, pattern, _ = parse_path(path)
        if pattern:
            raise self.router.RouterError("Prefix doesn't support parameters")

        if not path.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        super(Mount, self).__init__(path.rstrip('/'), methods)

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        if not path.startswith(self.path):
            return RouteMatch(False)

        try:
            cb, opts = self.router(path[len(self.path):], method=method)
            return RouteMatch(True, True, cb, opts)

        except self.router.NotFound:
            return RouteMatch(False)
