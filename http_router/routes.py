import abc
import dataclasses as dc
import typing as t
from urllib.parse import unquote

from .router import Router
from .utils import parse_path, INDENTITY


class RouteMatch:
    """Keeping route matching data."""

    __slots__ = 'path', 'method', 'target', 'path_params'

    def __init__(self, path: bool = False, method: bool = False,
                 target: t.Any = None, path_params: t.Mapping[str, t.Any] = None):

        self.path = path
        self.method = method
        self.target = target
        self.path_params = path_params

    def __bool__(self):
        return self.path and self.method

    def __iter__(self):
        return iter((self.target, self.path_params))

    def __str__(self):
        status = self.path and 200 or self.method and 404 or 405
        return f"RouteMatch {status} ({self.target}, {self.path_params!r})"


@dc.dataclass  # type: ignore  # mypy issue: https://github.com/python/mypy/issues/5374
class BaseRoute(metaclass=abc.ABCMeta):

    path: str
    methods: t.Set[str] = dc.field(default_factory=lambda: set())

    def __lt__(self, route: 'BaseRoute'):
        assert isinstance(route, BaseRoute), 'Only routes are supported'
        return self.path < route.path

    @abc.abstractmethod
    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        raise NotImplementedError


@dc.dataclass
class Route(BaseRoute):
    """Base plain route class."""

    target: t.Any = None

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        return RouteMatch(
            path == self.path, not self.methods or (method in self.methods), self.target)


@dc.dataclass
class DynamicRoute(Route):
    """Base dynamic route class."""

    pattern: t.Optional[t.Pattern] = None
    params: t.Dict = dc.field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.pattern is None:
            self.path, self.pattern, self.params = parse_path(self.path)
            assert self.pattern, 'Invalid path'

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        match = self.pattern.match(path)  # type: ignore  # checked in __post_init__
        if not match:
            return RouteMatch(target=self.target)

        path_params = {
            key: self.params.get(key, INDENTITY)(unquote(value))
            for key, value in match.groupdict().items()
        }

        return RouteMatch(
            bool(match), not self.methods or method in self.methods,
            self.target, path_params
        )


@dc.dataclass
class Mount(BaseRoute):
    """Support for nested routers."""

    router: Router = dc.field(default_factory=lambda: Router(), repr=False)

    def __post_init__(self):
        """Validate self prefix."""
        self.route = self.router.route
        prefix, pattern, _ = parse_path(self.path)
        if pattern:
            raise self.router.RouterError("Prefix doesn't support parameters")

        if not prefix.startswith('/'):
            raise self.router.RouterError("Prefix must start with /")

        self.path = prefix.rstrip('/')

    def match(self, path: str, method: str = 'GET') -> RouteMatch:
        """Is the route match the path."""
        if not path.startswith(self.path):
            return RouteMatch(False)

        try:
            cb, opts = self.router(path[len(self.path):], method=method)
            return RouteMatch(True, True, cb, opts)

        except self.router.NotFound:
            return RouteMatch(False)
