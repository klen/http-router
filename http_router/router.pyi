import typing as t

from .typing import CBV, CB, TYPE_METHODS, TYPE_PATH
from .routes import RouteMatch, BaseRoute


class Router:

    NotFound: t.ClassVar[t.Type[Exception]]
    RouterError: t.ClassVar[t.Type[Exception]]
    MethodNotAllowed: t.ClassVar[t.Type[Exception]]

    def __init__(self, trim_last_slash: bool = False, validator: CBV = None):
        ...

    def __call__(self, path: str, method: str = "GET") -> RouteMatch:
        ...

    def __route__(self, root: 'Router', prefix: str, *paths: t.Any,
                  methods: TYPE_METHODS = None, **params):
        ...

    def __getattr__(self, method: str) -> t.Callable:
        ...

    def bind(self, target: t.Any, *paths: TYPE_PATH, methods: TYPE_METHODS = None, **opts):
        ...

    def route(self, path: t.Union[CB, TYPE_PATH], *paths: TYPE_PATH,
              methods: TYPE_METHODS = None, **opts) -> t.Any:
        ...

    def routes(self) -> t.List[BaseRoute]:
        ...
