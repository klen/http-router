from __future__ import annotations


class RouterError(Exception):
    pass


class NotFoundError(RouterError):
    pass


class InvalidMethodError(RouterError):
    pass
