__version__ = "2.6.5"
__license__ = "MIT"


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


from .router import Router
from .routes import Route, DynamicRoute, PrefixedRoute, Mount

__all__ = (
    'DynamicRoute',
    'Mount',
    'PrefixedRoute',
    'Route',
    'Router',
)
