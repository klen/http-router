# cython: language_level=3

import typing as t
from urllib.parse import unquote

from .router import Router
from .utils import parse_path, INDENTITY


cdef class RouteMatch:
    """Keeping route matching data."""

    cdef public bint path, method
    cdef public object target
    cdef public dict path_params

    def __init__(self, path: bool = False, method: bool = False,
                 target: t.Any = None, path_params: t.Mapping[str, t.Any] = None):

        self.path = path
        self.method = method
        self.target = target
        self.path_params = path_params

    def __bool__(self):
        return self.path and self.method

    def __iter__(self):
        return iter((self.target, self.path_params))

    def __str__(self):
        status = self.path and 200 or self.method and 404 or 405
        return f"RouteMatch {status} ({self.target}, {self.path_params!r})"


cdef class BaseRoute:

    cdef readonly str path
    cdef readonly set methods

    def __init__(self, path: str, methods: t.Sequence[str] = None):
        self.path = path
        self.methods = methods or set()

    def __lt__(self, route: 'BaseRoute'):
        assert isinstance(route, BaseRoute), 'Only routes are supported'
        return self.path < route.path

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        raise NotImplementedError


cdef class Route(BaseRoute):
    """Base plain route class."""

    cdef public object target

    def __init__(self, path: str, methods: t.Sequence[str] = None, target: t.Any = None):
        super(Route, self).__init__(path, methods)
        self.target = target

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        return RouteMatch(
            path == self.path, not self.methods or (method in self.methods), self.target)


cdef class DynamicRoute(Route):
    """Base dynamic route class."""

    cdef public pattern
    cdef public dict params

    def __init__(self, path: t.Union[str, t.Pattern], methods: t.Sequence[str] = None,
                 target: t.Any = None, pattern: t.Pattern = None, params: t.Dict = None):
        super(DynamicRoute, self).__init__(path, methods, target)
        if pattern is None:
            self.path, pattern, params = parse_path(self.path)
            assert pattern, 'Invalid path'

        self.pattern = pattern
        self.params = params

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


class Mount(BaseRoute):
    """Support for nested routers."""

    def __init__(self, path: str, methods: t.Sequence[str] = None, router: Router = None):
        """Validate self prefix."""
        super(Mount, self).__init__(path, methods)
        self.router = router or Router()
        self.route = self.router.route
        prefix, pattern, _ = parse_path(self.path)
        if pattern:
            raise self.router.RouterError("Prefix doesn't support parameters")

        if not prefix.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        self.path = prefix.rstrip('/')

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        if not path.startswith(self.path):
            return RouteMatch(False)

        try:
            cb, opts = self.router(path[len(self.path):], method=method)
            return RouteMatch(True, True, cb, opts)

        except self.router.NotFound:
            return RouteMatch(False)
