"""HTTP Router tests."""
from __future__ import annotations

import copy
import importlib
import inspect
import pickle
import random
import shutil
import string
import sys
from contextlib import suppress
from pathlib import Path
from re import compile as re
from typing import Pattern
from uuid import UUID, uuid4

import pytest

import http_router
from http_router import Router
from http_router.routes import DynamicRoute, Mount, Route
from http_router.utils import parse_path


@pytest.fixture
def router() -> Router:
    return Router()


def test_router_basic(router: "Router"):
    assert router
    assert not router.trim_last_slash
    assert router.validator is not None
    assert router.NotFoundError is not None
    assert router.RouterError is not None
    assert router.InvalidMethodError is not None

    router.trim_last_slash = True
    assert router.trim_last_slash


def test_router_route_re(router: "Router"):
    res = router.route(re("test.jpg"))("test1 passed")
    assert res == "test1 passed"

    assert router("test.jpg").target == "test1 passed"
    assert router("testAjpg").target == "test1 passed"
    assert router("testAjpg/regex/can/be/dangerous").target == "test1 passed"

    router.route(re(r"params/(\w+)"))("test2 passed")
    match = router("params/mike")
    assert match
    assert not match.params

    router.route(re(r"params2/(?P<User>\w+)"))("test3 passed")
    match = router("params2/mike")
    assert match
    assert match.params == {"User": "mike"}


def test_router_route_str(router):
    router.route("test.jpg")(True)
    match = router("test.jpg")
    assert match

    with pytest.raises(router.NotFoundError):
        router("test.jpeg")

    router.route("/any/{item}")(True)
    match = router("/any/test")
    assert match
    assert match.params == {"item": "test"}

    router.route("/str/{item:str}")(True)
    match = router("/str/42")
    assert match
    assert match.params == {"item": "42"}

    router.route("/int/{item:int}")(True)
    match = router("/int/42")
    assert match
    assert match.params == {"item": 42}

    router.route(r"/regex/{item:\d{3}}")(True)
    match = router("/regex/422")
    assert match
    assert match.params == {"item": "422"}


def test_uuid_case_insensitive():


    router = Router()
    router.route("/u/{id:uuid}")(None)

    value = str(uuid4())
    assert router("/u/" + value.upper()).params == {"id": UUID(value)}


def test_parse_path():

    assert parse_path("/") == ("/", None, {})
    assert parse_path("/test.jpg") == ("/test.jpg", None, {})
    assert parse_path("/{foo") == ("/{foo", None, {})
    assert parse_path("/{a{") == ("/{a{", None, {})

    path, regex, params = parse_path(r"/{foo}/")
    assert isinstance(regex, Pattern)
    assert regex.pattern == r"^/(?P<foo>[^/]+)/$"
    assert path == "/{foo}/"
    assert params == {"foo": str}

    path, regex, params = parse_path(r"/{foo:int}/")
    assert isinstance(regex, Pattern)
    assert regex.pattern == r"^/(?P<foo>\d+)/$"
    assert path == "/{foo}/"
    assert params == {"foo": int}

    path, regex, params = parse_path(re(r"/(?P<foo>\d{1,3})/"))
    assert isinstance(regex, Pattern)
    assert params == {}
    assert path

    path, regex, params = parse_path(
        r"/api/v1/items/{item:str}/subitems/{ subitem:\d{3} }/find",
    )
    assert path == "/api/v1/items/{item}/subitems/{subitem}/find"
    assert regex.match("/api/v1/items/foo/subitems/300/find")
    assert params["item"]
    assert params["subitem"]


def test_route():

    route = Route("/only-post", {"POST"}, None)
    assert route.methods
    assert route.match("/only-post", "POST")
    assert not route.match("/only-post", "")

    route = Route("/only-post", set(), None)
    assert not route.methods
    assert route.match("/only-post", "GET").method  # empty methods == any method


def test_dynamic_route():

    route = DynamicRoute(r"/order/{id:int}", set(), None)
    match = route.match("/order/100", "")
    assert match
    assert match.params == {"id": 100}

    match = route.match("/order/unknown", "")
    assert not match
    assert not match.params

    route = DynamicRoute(re("/regex(/opt)?"), set(), None)
    match = route.match("/regex", "")
    assert match

    match = route.match("/regex/opt", "")
    assert match


def test_match_params_immutable():

    router = Router()
    router.route("/u/{id}")("u")

    match = router("/u/a")
    assert match.params == {"id": "a"}
    with pytest.raises(TypeError):
        match.params["id"] = "b"
    assert router("/u/a").params == {"id": "a"}


def test_router():
    """Base tests."""

    router = Router(trim_last_slash=True)

    with pytest.raises(router.NotFoundError):
        assert router("/unknown")

    router.route("/", "/simple")("simple")

    match = router("/", "POST")
    assert match.target == "simple"
    assert not match.params

    match = router("/simple", "DELETE")
    assert match.target == "simple"
    assert not match.params

    router.route("/only-post", methods="post")("only-post")
    assert router.plain["/only-post"][0].methods == {"POST"}

    with pytest.raises(router.InvalidMethodError):
        assert router("/only-post")

    match = router("/only-post", "POST")
    assert match.target == "only-post"
    assert not match.params

    router.route("/dynamic1/{id}")("dyn1")
    router.route("/dynamic2/{ id }")("dyn2")

    match = router("/dynamic1/11/")
    assert match.target == "dyn1"
    assert match.params == {"id": "11"}

    match = router("/dynamic2/22/")
    assert match.target == "dyn2"
    assert match.params == {"id": "22"}

    @router.route(r"/hello/{name:str}", methods="post")
    def hello():
        return "hello"

    match = router("/hello/john/", "POST")
    assert match.target() == "hello"
    assert match.params == {"name": "john"}

    @router.route("/params", var="value")
    def params(**opts):
        return opts

    match = router("/params", "POST")
    assert match.target() == {"var": "value"}

    assert router.routes()
    assert router.routes()[0].path == ""


def test_mounts():

    router = Router()
    route = Mount("/api/", set(), router)
    assert route.path == "/api"
    match = route.match("/api/e1", "")
    assert not match

    router.route("/e1")("e1")
    match = route.match("/api/e1", "UNKNOWN")
    assert match
    assert match.target == "e1"

    root = Router()
    subrouter = Router()

    root.route("/api")(1)
    root.route(re("/api/test"))(2)
    root.route("/api")(subrouter)
    subrouter.route("/test")(3)

    assert root("/api").target == 1
    assert root("/api/test").target == 3


def test_mount_fallthrough():

    root = Router()
    api_v2 = Router()
    api_v2.route("/x")("v2")
    root.route("/api/v2")(api_v2)

    api = Router()
    api.route("/x")("v1")
    root.route("/api")(api)

    assert root("/api/x").target == "v1"
    assert root("/api/v2/x").target == "v2"


def test_mount_trim_last_slash():

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


def test_trim_last_slash():

    router = Router()

    router.route("/route1")("route1")
    router.route("/route2/")("route2")

    assert router("/route1").target == "route1"
    assert router("/route2/").target == "route2"

    with pytest.raises(router.NotFoundError):
        assert not router("/route1/")

    with pytest.raises(router.NotFoundError):
        assert not router("/route2")

    router = Router(trim_last_slash=True)

    router.route("/route1")("route1")
    router.route("/route2/")("route2")

    assert router("/route1").target == "route1"
    assert router("/route2/").target == "route2"
    assert router("/route1/").target == "route1"
    assert router("/route2").target == "route2"


def test_validator():

    # The router only accepts async functions
    router = Router(validator=inspect.iscoroutinefunction)

    with pytest.raises(router.RouterError):
        router.route("/", "/simple")(lambda: "simple")


def test_converter():

    # The router only accepts async functions
    router = Router(converter=lambda v: lambda r: (r, v))

    router.route("/")("simple")
    match = router("/")
    assert match.target("test") == ("test", "simple")


def test_router_copy_pickle():


    router = Router()
    router.route("/x")("hello")

    for clone in (copy.copy(router), copy.deepcopy(router), pickle.loads(pickle.dumps(router))):
        assert clone("/x").target == "hello"


def test_custom_route():

    router = Router()

    @router.route()
    class View:
        methods = "get", "post"

        def __new__(cls, *args, **kwargs):
            """Init the class and call it."""
            self = super().__new__(cls)
            return self(*args, **kwargs)

        @classmethod
        def __route__(cls, router, *paths, **params):
            return router.bind(cls, "/", methods=cls.methods)

    assert router.plain["/"][0].methods == {"GET", "POST"}
    match = router("/")
    assert match.target is View


def test_nested_routers():

    child = Router()
    child.route("/url", methods="PATCH")("child_url")
    match = child("/url", "PATCH")
    assert match.target == "child_url"

    root = Router()
    root.route("/child")(child)

    with pytest.raises(root.NotFoundError):
        root("/child")

    with pytest.raises(root.NotFoundError):
        root("/child/unknown")

    with pytest.raises(root.InvalidMethodError):
        root("/child/url")

    match = root("/child/url", "PATCH")
    assert match.target == "child_url"


def test_method_case_insensitive():

    router = Router()
    router.route("/x", methods="post")("x")

    assert router("/x", "POST").target == "x"
    assert router("/x", "post").target == "x"

    with pytest.raises(router.InvalidMethodError):
        router("/x", "GET")


def test_method_shortcuts(router):
    router.delete("/delete")("DELETE")
    router.get("/get")("GET")
    router.post("/post")("POST")

    for route in router.routes():
        method = route.target
        assert route.methods == {method}


def test_benchmark(router, benchmark):

    chars = string.ascii_letters + string.digits
    randpath = lambda: "".join(random.choices(chars, k=10))  # noqa: E731
    methods = "GET", "POST"

    routes = [f"/{ randpath() }/{ randpath() }" for _ in range(100)]
    routes += [f"/{ randpath() }/{{item}}/{ randpath() }" for _ in range(100)]
    random.shuffle(routes)

    paths = []
    for route in routes:
        router.route(route, methods=random.choice(methods))("OK")
        paths.append(route.format(item=randpath()))

    paths = [route.format(item=randpath()) for route in routes]

    def do_work():
        router.match.cache_clear()
        for path in paths:
            with suppress(router.InvalidMethodError):
                assert router(path)

    benchmark(do_work)


def test_readme_examples():

    subrouter = Router()

    @subrouter.route("/items/{item}")
    def items():
        pass

    router = Router()
    router.route("/api")(subrouter)

    match = router("/api/items/12", method="GET")
    assert match, "HTTP path is ok"
    assert match.target is items
    assert match.params == {"item": "12"}


def test_implementations_parity(tmp_path):
    pkg = Path(http_router.__file__).parent
    dest = tmp_path / "http_router_pure"
    dest.mkdir()
    for name in ("__init__.py", "types.py", "exceptions.py", "utils.py", "router.py", "routes.py"):
        shutil.copy(pkg / name, dest / name)

    sys.path.insert(0, str(tmp_path))
    try:
        pure = importlib.import_module("http_router_pure")
    finally:
        sys.path.pop(0)

    def run(impl):
        router = impl.Router(trim_last_slash=True)
        router.route("/simple")("simple")
        router.route("/orders/{id:int}", methods="post")("order")
        router.route("/hello/{name:str}")("hello")

        sub = impl.Router()
        sub.route("/")("index")
        sub.route("/items/{item}")("item")
        router.route("/api")(sub)

        def call(path, method):
            try:
                match = router(path, method)
            except router.RouterError as exc:
                return (type(exc).__name__,)
            params = dict(match.params) if match.params is not None else None
            return ("ok", match.target, params)

        return [
            call(path, method)
            for path, method in (
                ("/simple", "GET"),
                ("/simple/", "GET"),
                ("/orders/42", "POST"),
                ("/orders/42", "post"),
                ("/orders/42", "GET"),
                ("/orders/nope", "POST"),
                ("/hello/john/", "POST"),
                ("/api", "GET"),
                ("/api/", "GET"),
                ("/api/items/12", "GET"),
                ("/unknown", "GET"),
            )
        ]

    assert run(http_router) == run(pure)


# ruff: noqa: FBT003, S301, S311
