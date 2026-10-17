"""Router behavior tests."""
from __future__ import annotations

from re import compile as re
from uuid import UUID

import pytest

from http_router import Router

UUID_VALUE = "12345678-1234-5678-1234-567812345678"


def test_router_defaults(router: Router):
    assert router.trim_last_slash is False
    assert router.validator is not None
    assert router.NotFoundError is not None
    assert router.RouterError is not None
    assert router.InvalidMethodError is not None

    router.trim_last_slash = True

    assert router.trim_last_slash is True


def test_regex_route_matches_prefix(router: Router):
    target = router.route(re("test.jpg"))("test1 passed")

    assert target == "test1 passed"
    assert router("test.jpg").target == "test1 passed"
    assert router("testAjpg").target == "test1 passed"
    assert router("testAjpg/regex/can/be/dangerous").target == "test1 passed"


def test_regex_route_captures_named_groups(router: Router):
    router.route(re(r"params/(\w+)"))("unnamed")
    router.route(re(r"params2/(?P<User>\w+)"))("named")

    assert router("params/mike").params == {}
    assert router("params2/mike").params == {"User": "mike"}


def test_static_route(router: Router):
    router.route("test.jpg")(True)

    assert router("test.jpg").target is True

    with pytest.raises(router.NotFoundError):
        router("test.jpeg")


@pytest.mark.parametrize(
    ("path", "request_path", "expected_params"),
    [
        ("/any/{item}", "/any/test", {"item": "test"}),
        ("/str/{item:str}", "/str/42", {"item": "42"}),
        ("/int/{item:int}", "/int/42", {"item": 42}),
        (r"/regex/{item:\d{3}}", "/regex/422", {"item": "422"}),
    ],
)
def test_route_captures_typed_params(router: Router, path, request_path, expected_params):
    router.route(path)(True)

    match = router(request_path)

    assert match.target is True
    assert match.params == expected_params


def test_uuid_param_is_case_insensitive(router: Router):
    router.route("/u/{id:uuid}")(None)

    assert router(f"/u/{UUID_VALUE.upper()}").params == {"id": UUID(UUID_VALUE)}


def test_plain_route_falls_back_to_dynamic_route(router: Router):
    router.route("/items/foo", methods="post")("foo")
    router.route("/items/{item}")("item")

    assert router("/items/foo", "POST").target == "foo"
    assert router("/items/12", "GET").target == "item"
    assert router("/items/foo", "GET").target == "item"


@pytest.mark.parametrize(
    ("unquote_params", "expected"),
    [(False, "100%25 off.txt"), (True, "100% off.txt")],
)
def test_unquote_params(unquote_params, expected):
    router = Router(unquote_params=unquote_params)
    router.route("/files/{name}")("file")

    assert router("/files/100%25 off.txt").params == {"name": expected}


def test_unknown_path_raises_not_found(trimmed_router: Router):
    with pytest.raises(trimmed_router.NotFoundError):
        trimmed_router("/unknown")


def test_plain_route_ignores_method(trimmed_router: Router):
    trimmed_router.route("/", "/simple")("simple")

    root_match = trimmed_router("/", "POST")
    simple_match = trimmed_router("/simple", "DELETE")

    assert root_match.target == "simple"
    assert root_match.params is None
    assert simple_match.target == "simple"
    assert simple_match.params is None


def test_route_with_declared_methods(router: Router):
    router.route("/only-post", methods="post")("only-post")

    assert router.plain["/only-post"][0].methods == {"POST"}

    with pytest.raises(router.InvalidMethodError):
        router("/only-post")

    match = router("/only-post", "POST")
    assert match.target == "only-post"
    assert match.params is None


def test_dynamic_route_parses_and_trims_slash(trimmed_router: Router):
    trimmed_router.route("/dynamic1/{id}")("dyn1")
    trimmed_router.route("/dynamic2/{ id }")("dyn2")

    match1 = trimmed_router("/dynamic1/11/")
    match2 = trimmed_router("/dynamic2/22/")

    assert match1.target == "dyn1"
    assert match1.params == {"id": "11"}
    assert match2.target == "dyn2"
    assert match2.params == {"id": "22"}


def test_decorator_binds_target(trimmed_router: Router):
    @trimmed_router.route(r"/hello/{name:str}", methods="post")
    def hello():
        return "hello"

    match = trimmed_router("/hello/john/", "POST")

    assert match.target() == "hello"
    assert match.params == {"name": "john"}


def test_route_opts_are_passed_to_target(router: Router):
    @router.route("/params", var="value")
    def params(**opts):
        return opts

    match = router("/params", "POST")

    assert match.target() == {"var": "value"}


def test_routes_returns_sorted_paths(trimmed_router: Router):
    trimmed_router.route("/", "/simple")("simple")
    trimmed_router.route("/only-post")("only-post")

    assert [route.path for route in trimmed_router.routes()] == ["", "/only-post", "/simple"]


def test_match_params_are_immutable(router: Router):
    router.route("/u/{id}")("u")

    match = router("/u/a")

    assert match.params == {"id": "a"}
    with pytest.raises(TypeError):
        match.params["id"] = "b"
    assert router("/u/a").params == {"id": "a"}


def test_trailing_slash_matters_by_default(router: Router):
    router.route("/route1")("route1")
    router.route("/route2/")("route2")

    assert router("/route1").target == "route1"
    assert router("/route2/").target == "route2"

    with pytest.raises(router.NotFoundError):
        router("/route1/")

    with pytest.raises(router.NotFoundError):
        router("/route2")


def test_trailing_slash_ignored_when_configured(trimmed_router: Router):
    trimmed_router.route("/route1")("route1")
    trimmed_router.route("/route2/")("route2")

    assert trimmed_router("/route1").target == "route1"
    assert trimmed_router("/route2/").target == "route2"
    assert trimmed_router("/route1/").target == "route1"
    assert trimmed_router("/route2").target == "route2"


@pytest.mark.parametrize("method", ["POST", "post"])
def test_method_is_case_insensitive(router: Router, method):
    router.route("/x", methods="post")("x")

    assert router("/x", method).target == "x"


def test_invalid_method_raises(router: Router):
    router.route("/x", methods="post")("x")

    with pytest.raises(router.InvalidMethodError):
        router("/x", "GET")


def test_method_shortcuts(router: Router):
    router.delete("/delete")("DELETE")
    router.get("/get")("GET")
    router.post("/post")("POST")

    assert {route.path: route.methods for route in router.routes()} == {
        "/delete": {"DELETE"},
        "/get": {"GET"},
        "/post": {"POST"},
    }


# ruff: noqa: FBT003
