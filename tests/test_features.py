"""Router configuration and lifecycle tests."""
from __future__ import annotations

import copy
import inspect
import pickle

import pytest

from http_router import Router


def test_validator_rejects_invalid_target():
    router = Router(validator=inspect.iscoroutinefunction)

    with pytest.raises(router.RouterError):
        router.route("/", "/simple")(lambda: "simple")


def test_converter_transforms_target():
    router = Router(converter=lambda v: lambda r: (r, v))

    router.route("/")("simple")
    match = router("/")

    assert match.target("test") == ("test", "simple")


@pytest.mark.parametrize(
    "clone",
    [copy.copy, copy.deepcopy, lambda router: pickle.loads(pickle.dumps(router))],
    ids=["copy", "deepcopy", "pickle"],
)
def test_router_can_be_cloned(router: Router, clone):
    router.route("/x")("hello")

    assert clone(router)("/x").target == "hello"


# ruff: noqa: S301
