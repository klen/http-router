from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from itertools import chain
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Self

from .exceptions import InvalidMethodError, NotFoundError, RouterError
from .utils import always_true, identity, parse_path, prepare_route_params

if TYPE_CHECKING:
    from .types import THostsArg, TMethodsArg, TPath, TVObj


class Router:
    """Route HTTP queries.

    A simple URL-path router that maps paths and HTTP methods to callable targets.
    Supports static routes, dynamic path parameters, and nested routers (mount).

    Example::

        router = Router(trim_last_slash=True)

        @router.get("/health")
        def health():
            return "ok"

        @router.route("/users/{id}")
        def get_user(id):
            return {"user_id": id}

        result = router("/users/42", method="GET")
    """

    NotFoundError: ClassVar[type[Exception]] = NotFoundError
    RouterError: ClassVar[type[Exception]] = RouterError
    InvalidMethodError: ClassVar[type[Exception]] = InvalidMethodError

    def __init__(
        self,
        *,
        trim_last_slash: bool = False,
        validator: Callable[[Any], bool] | None = None,
        converter: Callable | None = None,
        unquote_params: bool = True,
    ):
        """Initialize the router.

        :param trim_last_slash: Whether to strip trailing slashes before matching
            ``True``: ``/users/`` matches ``/users``
        :param validator: Validator for targets — must return ``True`` to accept
            Default is always-accepting.
        :param converter: Transformer applied to targets before binding
            Default is identity (no-op).
        :param unquote_params: Unquote captured path params after matching.
            Set ``False`` when the path is already decoded (e.g. ASGI).

        Example::

            router = Router(validator=lambda obj: hasattr(obj, "handle"))
        """
        self.trim_last_slash = trim_last_slash
        self.validator = validator or always_true
        self.converter = converter or identity
        self.unquote_params = unquote_params
        self.plain: defaultdict[str, list[Route]] = defaultdict(list)
        self.dynamic: list[Route] = []

    def __call__(self, path: str, method: str = "GET", host: str | None = None) -> RouteMatch:
        """Resolve a path+method(+host) to the matched route, or raise an error.

        :param path: URL path string (e.g. ``"/users/42"``)
        :param method: HTTP method (default ``"GET"``)
        :param host: Request host, compared verbatim (default ``None``, which only
            matches routes without ``hosts``).

        Returns a ``RouteMatch`` on success. Raises ``NotFoundError`` or
        ``InvalidMethodError`` if nothing matches.

        Example::

            result = router("/users/42", method="GET")
            print(result.target)   # the bound handler
            print(result.params)   # {"id": "42"}
        """
        match: RouteMatch = self.match(path, method, host)
        if not match.path:
            raise self.NotFoundError(path, method)

        if not match.method:
            raise self.InvalidMethodError(path, method)

        return match

    def __getattr__(self, method: str) -> Callable:
        """Shortcut to ``route()`` with a single HTTP method.

        Enable ``@router.get(...)``, ``@router.post(...)``, etc.
        """
        if method.startswith("__"):
            raise AttributeError(method)
        return partial(self.route, methods=method)

    def __route__(
        self,
        root: Router,
        prefix: str,
        *paths: str,
        methods: TMethodsArg | None = None,
        hosts: THostsArg | None = None,
        **__,
    ) -> Self:
        """Bind self as a nested (mounted) router on another ``Router``.

        :param root: Parent router to attach to
        :param prefix: Mount point (e.g. ``"/api"``)
        :param methods: Allowed HTTP methods for the mount prefix
        :param hosts: Allowed host(s) for the mount prefix, compared verbatim.
            ``None`` means any host.

        Example::

            api = Router()
            @api.route("/users")
            def list_users(): ...

            # Mount api under "/api" on the root router:
            router.route("/api", methods="GET")(api)

            # Now router("/api/users", "GET") → list_users
        """
        methods, hosts = prepare_route_params(methods, hosts)

        for path in (prefix, *paths):
            route = Mount(path, methods, router=self, hosts=hosts)
            root.dynamic.insert(0, route)

        return self

    @lru_cache(maxsize=1024)  # noqa: B019
    def match(self, path: str, method: str, host: str | None = None) -> RouteMatch:
        """Search for a matching route by path, HTTP method and host.

        Results are cached (1024 entries).

        :param path: URL path string
        :param method: HTTP method (upper-cased internally)
        :param host: Host string, compared verbatim. ``None`` only matches routes without
            ``hosts``.

        Returns ``RouteMatch`` with path/method flags set. If no match,
        returns a ``False``-evaluating match object (used for neighbor fallback).

        :raises NotFoundError: If no route matches the path at all
        """
        method = method.upper()
        if self.trim_last_slash:
            path = path.rstrip("/")

        route: Route
        match: RouteMatch
        neighbour: RouteMatch | None = None
        for route in chain(self.plain.get(path, ()), self.dynamic):
            match = route.match(path, method, host)
            if match.path:
                if match.method:
                    return match
                neighbour = match

        return RouteMatch(path=False, method=False) if neighbour is None else neighbour

    def bind(
        self,
        target: Any,
        *paths: TPath,
        methods: TMethodsArg | None = None,
        hosts: THostsArg | None = None,
        **opts,
    ) -> list[Route]:
        """Bind a callable target to one or more routes.

        Low-level alternative to the ``@route`` decorator.

        :param target: Callable or object to bind
        :param paths: One or more URL path strings/patterns
        :param methods: Allowed HTTP method(s)
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param opts: Extra keyword arguments passed to target via ``partial``.
            ``methods`` and ``hosts`` are reserved, so they're never passed on.

        Returns the list of created ``Route`` objects.
        """
        if opts:
            target = partial(target, **opts)

        methods, hosts = prepare_route_params(methods, hosts)

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
                    hosts=hosts,
                    unquote=self.unquote_params,
                )
                self.dynamic.append(route)

            else:
                route = Route(path, methods, target, hosts=hosts)
                self.plain[path].append(route)

            routes.append(route)

        return routes

    def route(
        self,
        *paths: TPath,
        methods: TMethodsArg | None = None,
        hosts: THostsArg | None = None,
        **opts,
    ) -> Callable[[TVObj], TVObj]:
        """Decorator to register a route with the router.

        :param paths: One or more URL path strings/patterns
        :param methods: Allowed HTTP method(s) (e.g. ``["GET", "POST"]``)
        :param hosts: Allowed host(s), compared verbatim. ``None`` means any host.
        :param opts: Extra keyword arguments passed to target via ``partial``.
            ``methods`` and ``hosts`` are reserved, so they're never passed on.

        Returns a decorator. The wrapped callable is validated, optionally
        converted, and bound to the specified paths.

        Example::

            @router.route("/users", methods=["GET", "POST"])
            def handle_users():
                ...

            @router.get("/users")  # shortcut for methods=["GET"]
            def list_users():
                ...

        Also supports router nesting: if the target has ``__route__``, it is
        mounted as a nested router instead of bound directly.
        """

        def wrapper(target: TVObj) -> TVObj:
            if hasattr(target, "__route__"):
                target.__route__(self, *paths, methods=methods, hosts=hosts, **opts)
                return target

            if not self.validator(target):
                raise self.RouterError("Invalid target: %r" % target)

            target = self.converter(target)
            self.bind(target, *paths, methods=methods, hosts=hosts, **opts)
            return target

        return wrapper

    def routes(self) -> list[Route]:
        """Return all registered routes, sorted by path.

        Useful for introspection, debugging or generating documentation.
        """
        return sorted(
            self.dynamic + [r for routes in self.plain.values() for r in routes],
        )


from .routes import DynamicRoute, Mount, Route, RouteMatch  # noqa: E402
