__version__ = "2.0.20"
__license__ = "MIT"


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


from .router import Router  # noqa
