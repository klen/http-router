"""A simple HTTP path router.

Resolve URL paths to callable targets by method and dynamic parameters.

Example::

    from http_router import Router

    app = Router()

    @app.get("/health")
    def health():
        return "ok"

    @app.route("/users/{id}")
    def get_user(id):
        return {"id": id}

    result = app("/users/42", method="GET")
"""
from __future__ import annotations

from .exceptions import InvalidMethodError, NotFoundError, RouterError
from .router import Router
from .routes import DynamicRoute, Mount, PrefixedRoute, Route

__all__ = (
    "DynamicRoute",
    "InvalidMethodError",
    "Mount",
    "NotFoundError",
    "PrefixedRoute",
    "Route",
    "Router",
    "RouterError",
)
