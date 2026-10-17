"""Path parsing tests."""
from __future__ import annotations

from re import compile as re
from typing import Pattern

import pytest

from http_router.utils import parse_path


@pytest.mark.parametrize("path", ["/", "/test.jpg", "/{foo", "/{a{"])
def test_parse_path_returns_static_paths_unchanged(path):
    assert parse_path(path) == (path, None, {})


@pytest.mark.parametrize(
    ("path", "expected_pattern", "expected_params"),
    [
        ("/{foo}/", r"^/(?P<foo>[^/]+)/$", {"foo": str}),
        ("/{foo:int}/", r"^/(?P<foo>\d+)/$", {"foo": int}),
    ],
)
def test_parse_path_builds_typed_pattern(path, expected_pattern, expected_params):
    parsed_path, regex, params = parse_path(path)

    assert parsed_path == "/{foo}/"
    assert isinstance(regex, Pattern)
    assert regex.pattern == expected_pattern
    assert params == expected_params


def test_parse_path_keeps_compiled_pattern():
    path, regex, params = parse_path(re(r"/(?P<foo>\d{1,3})/"))

    assert path == r"/(?P<foo>\d{1,3})/"
    assert regex.pattern == r"/(?P<foo>\d{1,3})/"
    assert params == {}


def test_parse_path_with_multiple_params():
    path, regex, params = parse_path(
        r"/api/v1/items/{item:str}/subitems/{ subitem:\d{3} }/find",
    )

    assert path == "/api/v1/items/{item}/subitems/{subitem}/find"
    assert regex.match("/api/v1/items/foo/subitems/300/find")
    assert params["item"] is str
    assert params["subitem"]("300") == "300"
