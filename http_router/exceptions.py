class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass
