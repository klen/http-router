"""Compiled and pure-python implementation parity tests."""
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

import pytest

import http_router


@pytest.fixture
def pure_http_router(tmp_path, monkeypatch):
    source = Path(http_router.__file__).parent
    package = tmp_path / "http_router_pure"
    package.mkdir()
    for name in ("__init__.py", "types.py", "exceptions.py", "utils.py", "router.py", "routes.py"):
        shutil.copy(source / name, package / name)

    monkeypatch.syspath_prepend(str(tmp_path))
    for name in list(sys.modules):
        if name.startswith("http_router_pure"):
            del sys.modules[name]

    yield importlib.import_module("http_router_pure")

    for name in list(sys.modules):
        if name.startswith("http_router_pure"):
            del sys.modules[name]


def test_implementations_parity(pure_http_router):
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

    assert run(http_router) == run(pure_http_router)
