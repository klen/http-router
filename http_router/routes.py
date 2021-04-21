import typing as t
from urllib.parse import unquote

from .router import Router
from .utils import parse_path, INDENTITY


class RouteMatch:
    """Keeping route matching data."""

    __slots__ = 'path', 'method', 'target', 'params'

    def __init__(self, path: bool, method: bool,
                 target: t.Any = None, params: t.Mapping[str, t.Any] = None):
        self.path = path
        self.method = method
        self.target = target
        self.params = params

    def __bool__(self):
        return self.path and self.method


class BaseRoute:

    __slots__ = 'path', 'methods'

    def __init__(self, path: str, methods: t.Set = None):
        self.path = path
        self.methods = methods

    def __lt__(self, route: 'BaseRoute'):
        assert isinstance(route, BaseRoute), 'Only routes are supported'
        return self.path < route.path

    def match(self, path: str, method: str) -> RouteMatch:
        raise NotImplementedError


class Route(BaseRoute):
    """Base plain route class."""

    __slots__ = 'path', 'methods', 'target'

    def __init__(self, path: str, methods: t.Set = None, target: t.Any = None):
        super(Route, self).__init__(path, methods)
        self.target = target

    def match(self, path: str, method: str) -> RouteMatch:
        """Is the route match the path."""
        path_matched = path == self.path
        method_matched = not self.methods or (method in self.methods)
        if not path_matched and method_matched:
            return RouteMatch(path_matched, method_matched)

        return RouteMatch(path_matched, method_matched, self.target)


class DynamicRoute(Route):
    """Base dynamic route class."""

    __slots__ = 'path', 'methods', 'target', 'pattern', 'params'

    def __init__(self, path: str, methods: t.Set = None, target: t.Any = None,
                 pattern: t.Pattern = None, params: t.Dict = None):
        if pattern is None:
            path, pattern, params = parse_path(path)
            assert pattern, 'Invalid path'
        self.pattern = pattern
        self.params = params or {}
        super(DynamicRoute, self).__init__(path, methods, target)

    def match(self, path: str, method: str) -> RouteMatch:
        match = self.pattern.match(path)  # type: ignore  # checked in __post_init__
        if not match:
            return RouteMatch(False, False)

        return RouteMatch(
            True, not self.methods or method in self.methods, self.target, {
                key: self.params.get(key, INDENTITY)(unquote(value))
                for key, value in match.groupdict().items()
            }
        )


class Mount(BaseRoute):
    """Support for nested routers."""

    __slots__ = 'path', 'methods', 'router', 'route'

    def __init__(self, path: str, methods: t.Set = None, router: Router = None):
        """Validate self prefix."""
        self.router = router or Router()
        self.route = self.router.route
        path, pattern, _ = parse_path(path)
        if pattern:
            raise self.router.RouterError("Prefix doesn't support parameters")

        if not path.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        super(Mount, self).__init__(path.rstrip('/'), methods)

    def match(self, path: str, method: str) -> RouteMatch:
        """Is the route match the path."""
        if not path.startswith(self.path):
            return RouteMatch(False, False)

        path = path[len(self.path):]
        return self.router.match(path, method)
