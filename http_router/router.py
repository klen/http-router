from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from typing import Any, Callable, ClassVar, DefaultDict, List, Optional, Type, Union

from . import MethodNotAllowed, NotFound, RouterError  # noqa
from .types import TMethodsArg, TPath, TVMatch
from .utils import parse_path


class Router:
    """Route HTTP queries."""

    NotFound: ClassVar[Type[Exception]] = NotFound  # noqa
    RouterError: ClassVar[Type[Exception]] = RouterError  # noqa
    MethodNotAllowed: ClassVar[Type[Exception]] = MethodNotAllowed  # noqa

    def __init__(
        self,
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
        self.plain: DefaultDict[str, List[Route]] = defaultdict(list)
        self.dynamic: List[Route] = list()

    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        """Found a target for the given path and method."""
        if self.trim_last_slash:
            path = path.rstrip("/")

        match = self.match(path, method)
        if not match.path:
            raise self.NotFound(path, method)

        if not match.method:
            raise self.MethodNotAllowed(path, method)

        return match

    def __route__(self, root: Router, prefix: str, *_, **__):
        """Bind self as a nested router."""
        route = Mount(prefix, set(), router=self)
        root.dynamic.insert(0, route)
        return self

    @lru_cache(maxsize=1024)
    def match(self, path: str, method: str) -> RouteMatch:
        """Search a matched target for the given path and method."""
        neighbour = None
        for route in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match.path:
                if match.method:
                    return match
                neighbour = match

        return RouteMatch(False, False) if neighbour is None else neighbour

    def bind(
        self, target: Any, *paths: TPath, methods: Optional[TMethodsArg] = None, **opts
    ):
        """Bind a target to self."""
        if opts:
            target = partial(target, **opts)

        if isinstance(methods, str):
            methods = [methods]

        if methods is not None:
            methods = set(m.upper() for m in methods or [])

        routes = []

        for path in paths:
            if self.trim_last_slash and isinstance(path, str):
                path = path.rstrip("/")

            path, pattern, params = parse_path(path)

            if pattern:
                route: Route = DynamicRoute(
                    path, methods=methods, target=target, pattern=pattern, params=params
                )
                self.dynamic.append(route)

            else:
                route = Route(path, methods, target)
                self.plain[path].append(route)

            routes.append(route)

        return routes

    def route(
        self,
        path: Union[TVMatch, TPath],
        *paths: TPath,
        methods: Optional[TMethodsArg] = None,
        **opts,
    ) -> Callable:
        """Register a route."""

        def wrapper(target: TVMatch) -> TVMatch:
            if hasattr(target, "__route__"):
                target.__route__(self, *paths, methods=methods, **opts)
                return target

            if not self.validator(target):  # type: ignore
                raise self.RouterError("Invalid target: %r" % target)

            if not paths:
                raise self.RouterError("Invalid route. A HTTP Path is required.")

            target = self.converter(target)
            self.bind(target, *paths, methods=methods, **opts)
            return target

        if isinstance(path, TPath.__args__):  # type: ignore
            paths = (path, *paths)

        else:
            return wrapper(path)  # type: ignore

        return wrapper

    def routes(self) -> List[Route]:
        """Get a list of self routes."""
        return sorted(
            self.dynamic + [r for routes in self.plain.values() for r in routes]
        )

    def __getattr__(self, method: str) -> Callable:
        """Shortcut to the router methods."""
        return partial(self.route, methods=method)


from .routes import DynamicRoute, Mount, Route, RouteMatch  # noqa

# pylama: ignore=D
