import typing as t
from collections.abc import Iterator

from .router import Router


class RouteMatch:
    """Keeping route matching data."""

    path: bool
    method: bool
    target: t.Any
    path_params: t.Mapping[str, t.Any]

    def __init__(self, path: bool = False, method: bool = False,
                 target: t.Any = None, path_params: t.Mapping[str, t.Any] = None):

        ...

    def __bool__(self) -> bool:
        ...

    def __iter__(self) -> Iterator:
        ...

    def __str__(self) -> str:
        ...


class BaseRoute:

    path: str
    methods: t.Set[str]

    def __init__(self, path: str, methods: t.Sequence[str] = None):
        ...

    def __lt__(self, route: BaseRoute) -> bool:  # noqa
        ...

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        ...


class Route(BaseRoute):
    """Base plain route class."""

    target: t.Any

    def __init__(self, path: str, methods: t.Sequence[str] = None, target: t.Any = None):
        ...

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        ...


class DynamicRoute(Route):
    """Base dynamic route class."""

    pattern: t.Pattern
    params: t.Dict

    def __init__(self, path: t.Union[str, t.Pattern], methods: t.Sequence[str] = None,
                 target: t.Any = None, pattern: t.Pattern = None, params: t.Dict = None):
        ...

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        ...


class Mount(BaseRoute):
    """Support for nested routers."""

    router: Router
    route: t.Callable

    def __init__(self, path: str, methods: t.Sequence[str] = None, router: Router = None):
        """Validate self prefix."""
        ...

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        ...
