"""Mount and nested router tests."""
from __future__ import annotations

from re import compile as re

import pytest

from http_router import Router
from http_router.routes import Mount


@pytest.fixture
def mounted_router() -> Router:
    child = Router()
    child.route("/url", methods="PATCH")("child_url")
    root = Router()
    root.route("/child")(child)
    return root


def test_mount_delegates_to_mounted_router(router: Router):
    route = Mount("/api/", set(), router)

    assert route.path == "/api"
    assert not route.match("/api/e1", "")

    router.route("/e1")("e1")

    assert route.match("/api/e1", "UNKNOWN").target == "e1"


def test_nested_router():
    root = Router()
    subrouter = Router()
    root.route("/api")(1)
    root.route(re("/api/test"))(2)
    subrouter.route("/test")(3)
    root.route("/api")(subrouter)

    assert root("/api").target == 1
    assert root("/api/test").target == 3


def test_nested_router_fallthrough():
    root = Router()

    api_v2 = Router()
    api_v2.route("/x")("v2")
    root.route("/api/v2")(api_v2)

    api = Router()
    api.route("/x")("v1")
    root.route("/api")(api)

    assert root("/api/x").target == "v1"
    assert root("/api/v2/x").target == "v2"


def test_mount_respects_trim_last_slash():
    sub = Router(trim_last_slash=True)
    sub.route("/u")("u")
    root = Router()
    root.route("/api")(sub)

    assert root("/api/u/").target == "u"


def test_mount_root_route():
    sub = Router()
    sub.route("/")("index")
    root = Router()
    root.route("/api")(sub)

    assert root("/api").target == "index"
    assert root("/api/").target == "index"


def test_mount_methods_and_prefixes():
    sub = Router()
    sub.route("/u")("u")
    root = Router()
    root.route("/a", "/b", methods="POST")(sub)

    with pytest.raises(root.InvalidMethodError):
        root("/a/u")

    assert root("/a/u", "POST").target == "u"
    assert root("/b/u", "POST").target == "u"


def test_nested_router_raises_for_unknown_path(mounted_router: Router):
    with pytest.raises(mounted_router.NotFoundError):
        mounted_router("/child")

    with pytest.raises(mounted_router.NotFoundError):
        mounted_router("/child/unknown")


def test_nested_router_raises_for_invalid_method(mounted_router: Router):
    with pytest.raises(mounted_router.InvalidMethodError):
        mounted_router("/child/url")


def test_nested_router_matches_allowed_method(mounted_router: Router):
    assert mounted_router("/child/url", "PATCH").target == "child_url"


def test_readme_example_mounted_router(router: Router):
    subrouter = Router()

    @subrouter.route("/items/{item}")
    def items():
        pass

    router.route("/api")(subrouter)

    match = router("/api/items/12", method="GET")

    assert match
    assert match.target is items
    assert match.params == {"item": "12"}
