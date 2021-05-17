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

    def __repr__(self):
        return f"<RouteMatch path:{self.path} method:{self.method} - {self.target}>"


class Route:
    """Base plain route class."""

    __slots__ = 'path', 'methods', 'target'

    def __init__(self, path: str, methods: t.Set = None, target: t.Any = None):
        self.path = path
        self.methods = methods
        self.target = target

    def __lt__(self, route: 'Route'):
        assert isinstance(route, Route), 'Only routes are supported'
        return self.path < route.path

    def match(self, path: str, method: str) -> RouteMatch:
        """Is the route match the path."""
        methods = self.methods
        return RouteMatch(path == self.path, not methods or (method in methods), self.target)


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


class PrefixedRoute(Route):
    """Match by a prefix."""

    def __init__(self, path: str, methods: t.Set = None, target: t.Any = None):
        path, pattern, _ = parse_path(path)
        if pattern:
            assert not pattern, "Prefix doesn't support patterns."

        super(PrefixedRoute, self).__init__(path.rstrip('/'), methods, target)

    def match(self, path: str, method: str) -> RouteMatch:
        """Is the route match the path."""
        methods = self.methods
        return RouteMatch(
            path.startswith(self.path), not methods or (method in methods), self.target)


class Mount(PrefixedRoute):
    """Support for nested routers."""

    def __init__(self, path: str, methods: t.Set = None, router: Router = None):
        """Validate self prefix."""
        router = router or Router()
        super(Mount, self).__init__(path, methods, router.match)

    def match(self, path: str, method: str) -> RouteMatch:
        """Is the route match the path."""
        match: RouteMatch = super(Mount, self).match(path, method)
        if match:
            target = t.cast(t.Callable, self.target)
            return target(path[len(self.path):], method)

        return match
