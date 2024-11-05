from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Optional,
)

from .exceptions import InvalidMethodError, NotFoundError, RouterError
from .utils import parse_path

if TYPE_CHECKING:
    from .types import TMethodsArg, TPath, TVObj


class Router:
    """Route HTTP queries."""

    NotFoundError: ClassVar[type[Exception]] = NotFoundError
    RouterError: ClassVar[type[Exception]] = RouterError
    InvalidMethodError: ClassVar[type[Exception]] = InvalidMethodError

    def __init__(
        self,
        *,
        trim_last_slash: bool = False,
        validator: Optional[Callable[[Any], bool]] = None,
        converter: Optional[Callable] = None,
    ):
        """Initialize the router.

        :param trim_last_slash: Ignore a last slash
        :param validator: Validate objects to route
        :param converter: Convert objects to route

        """
        self.trim_last_slash = trim_last_slash
        self.validator = validator or (lambda _: True)
        self.converter = converter or (lambda v: v)
        self.plain: defaultdict[str, list[Route]] = defaultdict(list)
        self.dynamic: list[Route] = []

    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip("/")

        match = self.match(path, method)
        if not match.path:
            raise self.NotFoundError(path, method)

        if not match.method:
            raise self.InvalidMethodError(path, method)

        return match

    def __getattr__(self, method: str) -> Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)

    def __route__(self, root: Router, prefix: str, *_, **__) -> Router:
        """Bind self as a nested router."""
        route = Mount(prefix, set(), router=self)
        root.dynamic.insert(0, route)
        return self

    @lru_cache(maxsize=1024)  # noqa: B019
    def match(self, path: str, method: str) -> RouteMatch:
        """Search a matched target for the given path and method."""
        neighbour = None
        for route in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match.path:
                if match.method:
                    return match
                neighbour = match

        return RouteMatch(path=False, method=False) if neighbour is None else neighbour

    def bind(
        self,
        target: Any,
        *paths: TPath,
        methods: Optional[TMethodsArg] = None,
        **opts,
    ) -> list[Route]:
        """Bind a target to self."""
        if opts:
            target = partial(target, **opts)

        if isinstance(methods, str):
            methods = [methods]

        if methods is not None:
            methods = {m.upper() for m in methods or []}

        routes = []

        for src in paths:
            path = src
            if self.trim_last_slash and isinstance(path, str):
                path = path.rstrip("/")

            path, pattern, params = parse_path(path)

            if pattern:
                route: Route = DynamicRoute(
                    path,
                    methods=methods,
                    target=target,
                    pattern=pattern,
                    params=params,
                )
                self.dynamic.append(route)

            else:
                route = Route(path, methods, target)
                self.plain[path].append(route)

            routes.append(route)

        return routes

    def route(
        self,
        *paths: TPath,
        methods: Optional[TMethodsArg] = None,
        **opts,
    ) -> Callable[[TVObj], TVObj]:
        """Register a route."""

        def wrapper(target: TVObj) -> TVObj:
            if hasattr(target, "__route__"):
                target.__route__(self, *paths, methods=methods, **opts)
                return target

            if not self.validator(target):
                raise self.RouterError("Invalid target: %r" % target)

            target = self.converter(target)
            self.bind(target, *paths, methods=methods, **opts)
            return target

        return wrapper

    def routes(self) -> list[Route]:
        """Get a list of self routes."""
        return sorted(
            self.dynamic + [r for routes in self.plain.values() for r in routes],
        )


from .routes import DynamicRoute, Mount, Route, RouteMatch  # noqa: E402
