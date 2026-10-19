from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, Mapping, Pattern
from urllib.parse import unquote

from .router import Router
from .utils import identity, parse_path

if TYPE_CHECKING:
    from .types import THosts, TMethods, TPath


class RouteMatch:
    """Holds the result of a route match.

    Attributes:
        path: Whether the path matched (True/False)
        method: Whether the HTTP method is allowed (True/False)
        target: The callable bound to this route (or ``None``)
        params: URL parameters captured by the pattern (empty dict if none)

    A ``RouteMatch`` is truthy only when both path and method match.
    """

    __slots__ = "method", "params", "path", "target"

    def __init__(
        self,
        path: bool,
        method: bool,
        target=None,
        params: Mapping[str, Any] | None = None,
    ):
        self.path = path
        self.method = method
        self.target = target
        self.params = params

    def __bool__(self):
        return self.path and self.method

    def __repr__(self):
        return f"<RouteMatch path:{self.path} method:{self.method} - {self.target}>"


class Route:
    """Base class for static (non-parameterized) routes.

    Matches an exact path string against the request path and HTTP method.
    """

    __slots__ = "hosts", "methods", "path", "target"

    def __init__(
        self, path: str, methods: TMethods | None = None, target: Any = None,
        *, hosts: THosts | None = None,
    ):
        """Create a static route.

        :param path: Exact URL path (e.g. ``"/users"``)
        :param methods: Allowed HTTP method(s). ``None`` means any method.
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param target: Callable to invoke on match (or ``None``)
        """
        self.path = path
        self.methods = methods
        self.hosts = hosts
        self.target = target

    def __lt__(self, route: Route) -> bool:
        """Sort routes by path (for __routes__ ordering)."""
        assert isinstance(route, Route), "Only routes are supported"
        return self.path < route.path

    def match(self, path: str, method: str, host: str | None = None) -> RouteMatch:
        """Check if this route matches the given path, method and host.

        :param path: Request URL path
        :param method: HTTP method string (e.g. ``"GET"``)
        :param host: Request host, compared verbatim, or ``None``. A route with
            ``hosts`` doesn't match a host it doesn't list, as if its path hadn't matched.

        Returns a ``RouteMatch`` with the appropriate flags set.
        """
        methods = self.methods
        return RouteMatch(
            path == self.path and (not self.hosts or host in self.hosts),
            not methods or (method in methods),
            self.target,
        )


class DynamicRoute(Route):
    """A route with path parameters (e.g. ``/users/{id}``).

    Uses a compiled regex pattern to extract URL segments and bind them
    as keyword arguments on ``RouteMatch.params``.
    """

    __slots__ = "hosts", "methods", "params", "path", "pattern", "target", "unquote"

    def __init__(  # noqa: PLR0913
        self, path: TPath, methods: TMethods | None = None, target: Any = None,
        pattern: Pattern | None = None, params: dict | None = None,
        *,
        hosts: THosts | None = None,
        unquote: bool = True,
    ):
        """Create a dynamic route.

        :param path: URL pattern string (e.g. ``"/users/{id}"``)
        :param methods: Allowed HTTP method(s). ``None`` means any method.
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param target: Callable to invoke on match (or ``None``)
        :param pattern: Pre-compiled regex. If ``None``, parsed from ``path``.
        :param params: Parameter converters dict (e.g. ``{"id": int}``)
        :param unquote: Unquote captured values after matching (default ``True``).

        Raises AssertionError if no pattern can be extracted when ``pattern=None``.
        """
        if pattern is None:
            path, pattern, params = parse_path(path)
            assert pattern, "Invalid path"
        self.pattern = pattern
        self.params = params or {}
        self.unquote = unquote
        super(DynamicRoute, self).__init__(path, methods, target, hosts=hosts)  # type: ignore[arg-type]

    def match(self, path: str, method: str, host: str | None = None) -> RouteMatch:
        """Check if this route matches using its regex pattern.

        Extracts captured URL segments into ``params`` on success.
        """
        match = self.pattern.match(path)
        if not (match and (not self.hosts or host in self.hosts)):
            return RouteMatch(False, False)

        decode = unquote if self.unquote else identity
        return RouteMatch(
            True,
            not self.methods or method in self.methods,
            self.target,
            MappingProxyType(
                {
                    key: self.params.get(key, identity)(decode(value))
                    for key, value in match.groupdict().items()
                },
            ),
        )


class PrefixedRoute(Route):
    """Matches any path that starts with a given prefix.

    Used internally for nested routers (Mount).
    """

    def __init__(self, path: str, methods: TMethods | None = None, target: Any = None,
        *, hosts: THosts | None = None,
    ):
        """Create a prefix-based route.

        :param path: Prefix to match (e.g. ``"/api"``)
        :param methods: Allowed HTTP method(s). ``None`` means any method.
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param target: Callable to invoke on match (usually a sub-router)
        """
        path, pattern, _ = parse_path(path)
        assert not pattern, "Prefix doesn't support patterns."

        super(PrefixedRoute, self).__init__(path.rstrip("/"), methods, target, hosts=hosts)

    def match(self, path: str, method: str, host: str | None = None) -> RouteMatch:
        """Check if the request path starts with this prefix."""
        methods = self.methods
        return RouteMatch(
            path.startswith(self.path) and (not self.hosts or host in self.hosts),
            not methods or (method in methods),
            self.target,
        )


class Mount(PrefixedRoute):
    """Mount a nested Router under a URL prefix.

    Combines prefix matching with delegation to the mounted router
    for sub-path resolution.
    """

    def __init__(self, path: str, methods: TMethods | None = None, router: Router | None = None,
        *, hosts: THosts | None = None,
    ):
        """Create a mount point for a nested router.

        :param path: Mount prefix (e.g. ``"/api"``)
        :param methods: Allowed HTTP method(s). ``None`` means any method.
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param router: The nested Router instance to delegate to. Defaults to a new empty Router.
        """
        router = router or Router()
        super(Mount, self).__init__(path, methods, router.match, hosts=hosts)

    def match(self, path: str, method: str, host: str | None = None) -> RouteMatch:
        """Check prefix and delegate remaining path to the mounted router."""
        match: RouteMatch = super(Mount, self).match(path, method, host)
        if match.path and match.method:
            target: Callable = self.target
            return target(path[len(self.path):] or "/", method, host)

        return match


# ruff: noqa: FBT001, FBT003
