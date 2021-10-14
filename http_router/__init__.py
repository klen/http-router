__version__ = "2.6.3"
__license__ = "MIT"


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


from .router import Router  # noqa
from .routes import Route, DynamicRoute, PrefixedRoute, Mount  # noqa
