from typing import Pattern, Union
from urllib.parse import unquote

from .router import Router
from .utils import parse_path, identity


cdef class RouteMatch:
    """Keeping route matching data."""

    def __cinit__(self, bint path, bint method, object target=None, dict params=None):
        self.path = path
        self.method = method
        self.target = target
        self.params = params

    def __bool__(self) -> bool:
        return self.path and self.method


cdef class Route:
    """Base plain route class."""

    def __init__(self, str path, set methods, object target=None):
        self.path = path
        self.methods = methods
        self.target = target

    def __lt__(self, Route route) -> bool:
        return self.path < route.path

    cpdef RouteMatch match(self, str path, str method):
        """Is the route match the path."""
        cdef bint path_ = self.path == path
        cdef set methods = self.methods
        cdef bint method_ = not methods or method in methods
        if not (path_ and method_):
            return RouteMatch(path_, method_)

        return RouteMatch(path_, method_, self.target)


cdef class DynamicRoute(Route):
    """Base dynamic route class."""

    def __init__(self, path: Union[str, Pattern], set methods,
                 object target=None, pattern: Pattern = None, dict params = None):

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
            key: self.params.get(key, identity)(unquote(value))
            for key, value in match.groupdict().items()
        }

        return RouteMatch(True, method_, self.target, path_params)


cdef class PrefixedRoute(Route):
    """Match by a prefix."""

    def __init__(self, str path, set methods, object target=None):
        path, pattern, _ = parse_path(path)
        if pattern:
            assert not pattern, "Prefix doesn't support patterns."

        super(PrefixedRoute, self).__init__(path.rstrip('/'), methods, target)

    cpdef RouteMatch match(self, str path, str method):
        """Is the route match the path."""
        cdef set methods = self.methods
        return RouteMatch(
            path.startswith(self.path), not methods or (method in methods), self.target)


cdef class Mount(PrefixedRoute):
    """Support for nested routers."""

    def __init__(self, str path, set methods, Router router=None):
        """Validate self prefix."""
        router = router or Router()
        super(Mount, self).__init__(path, methods, router.match)

    cpdef RouteMatch match(self, str path, str method):
        """Is the route match the path."""
        cdef RouteMatch match = super(Mount, self).match(path, method)
        if match.path and match.method:
            return self.target(path[len(self.path):], method)

        return match
