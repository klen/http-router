"""Route class tests."""
from __future__ import annotations

from re import compile as re
from typing import TYPE_CHECKING

from http_router.routes import DynamicRoute, Route

if TYPE_CHECKING:
    from http_router import Router


def test_route_requires_allowed_method():
    route = Route("/only-post", {"POST"}, None)

    assert route.methods == {"POST"}
    assert route.match("/only-post", "POST")
    assert not route.match("/only-post", "")


def test_route_without_methods_matches_any_method():
    route = Route("/only-post", set(), None)

    assert not route.methods
    assert route.match("/only-post", "GET")


def test_dynamic_route_converts_params():
    route = DynamicRoute(r"/order/{id:int}", set(), None)

    match = route.match("/order/100", "")

    assert match
    assert match.params == {"id": 100}


def test_dynamic_route_rejects_non_matching_path():
    route = DynamicRoute(r"/order/{id:int}", set(), None)

    match = route.match("/order/unknown", "")

    assert not match
    assert match.params is None


def test_dynamic_route_accepts_precompiled_pattern():
    route = DynamicRoute(re("/regex(/opt)?"), set(), None)

    assert route.match("/regex", "")
    assert route.match("/regex/opt", "")


def test_custom_route_class(router: Router):
    @router.route()
    class View:
        methods = ("get", "post")

        def __new__(cls, *args, **kwargs):
            self = super().__new__(cls)
            return self(*args, **kwargs)

        @classmethod
        def __route__(cls, router, *paths, **params):
            return router.bind(cls, "/", methods=cls.methods)

    assert router.plain["/"][0].methods == {"GET", "POST"}

    match = router("/")
    assert match.target is View
