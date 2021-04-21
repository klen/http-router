import typing as t
from urllib.parse import unquote
from collections.abc import Iterator

from .router import Router
from .utils import parse_path, INDENTITY


cdef class RouteMatch:
    """Keeping route matching data."""

    def __cinit__(self, bint path, bint method, object target=None, dict params=None):
        self.path = path
        self.method = method
        self.target = target
        self.params = params

    def __bool__(self) -> bool:
        return self.path and self.method


cdef class BaseRoute:

    def __init__(self, str path, set methods):
        self.path = path
        self.methods = methods

    def __lt__(self, BaseRoute route) -> bool:
        return self.path < route.path

    cpdef RouteMatch match(self, str path, str method):
        raise NotImplementedError


cdef class Route(BaseRoute):
    """Base plain route class."""

    def __init__(self, str path, set methods, object target=None):
        super(Route, self).__init__(path, methods)
        self.target = target

    cpdef RouteMatch match(self, str path, str method):
        """Is the route match the path."""
        cdef bint path_ = self.path == path
        cdef bint method_ = not self.methods or method in self.methods
        if not (path_ and method_):
            return RouteMatch(path_, method_)

        return RouteMatch(path_, method_, self.target)


cdef class DynamicRoute(Route):
    """Base dynamic route class."""

    def __init__(self, path: t.Union[str, t.Pattern], set methods,
                 object target=None, pattern: t.Pattern = None, params: t.Dict = None):

        if pattern is None:
            path, pattern, params = parse_path(path)
            assert pattern, 'Invalid path'

        self.pattern = pattern
        self.params = params
        self.path = path
        self.methods = methods
        self.target = target

    cpdef RouteMatch match(self, str path, str method):
        match = self.pattern.match(path)  # type: ignore  # checked in __post_init__
        if not match:
            return RouteMatch(False, False)

        cdef bint method_ = not self.methods or method in self.methods
        cdef dict path_params = {
            key: self.params.get(key, INDENTITY)(unquote(value))
            for key, value in match.groupdict().items()
        }

        return RouteMatch(True, method_, self.target, path_params)


cdef class Mount(BaseRoute):
    """Support for nested routers."""

    def __init__(self, str path, set methods=None, Router router=None):
        """Validate self prefix."""
        self.router = router or Router()
        self.route = self.router.route
        path, pattern, _ = parse_path(path)
        if pattern:
            raise self.router.RouterError("Prefix doesn't support parameters")

        if not path.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        super(Mount, self).__init__(path.rstrip('/'), methods)

    cpdef RouteMatch match(self, str path, str method):
        """Is the route match the path."""
        if not path.startswith(self.path):
            return RouteMatch(False, False)

        return self.router.match(path[len(self.path):], method)
