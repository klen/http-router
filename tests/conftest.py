"""Shared test fixtures."""
from __future__ import annotations

import pytest

from http_router import Router


@pytest.fixture
def router() -> Router:
    return Router()


@pytest.fixture
def trimmed_router() -> Router:
    return Router(trim_last_slash=True)
