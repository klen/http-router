import typing as t

from .router import Router


class RouteMatch:
    """Keeping route matching data."""

    target: t.Any
    path_params: t.Mapping[str, t.Any]

    def __init__(self, path: bool, method: bool,
                 target: t.Any = None, path_params: t.Mapping[str, t.Any] = None):
        ...

    def __bool__(self) -> bool:
        ...


class BaseRoute:

    path: str
    methods: t.Set[str]

    def __init__(self, path: str, methods: t.Set[str]):
        ...

    def __lt__(self, route: BaseRoute) -> bool:  # noqa
        ...

    def match(self, path: str, method: str) -> RouteMatch:
        ...


class Route(BaseRoute):
    """Base plain route class."""

    target: t.Any

    def __init__(self, path: str, methods: t.Set[str], target: t.Any = None):
        ...


class DynamicRoute(Route):
    """Base dynamic route class."""

    pattern: t.Pattern
    params: t.Dict

    def __init__(self, path: t.Union[str, t.Pattern], methods: t.Set[str],
                 target: t.Any = None, pattern: t.Pattern = None, params: t.Dict = None):
        ...


class Mount(BaseRoute):
    """Support for nested routers."""

    router: Router
    route: t.Callable

    def __init__(self, path: str, methods: t.Set[str] = None, router: Router = None):
        """Validate self prefix."""
        ...
