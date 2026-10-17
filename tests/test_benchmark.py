"""Router benchmark."""
from __future__ import annotations

import random
import string
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http_router import Router


def test_benchmark(router: Router, benchmark):
    rng = random.Random(0)
    chars = string.ascii_letters + string.digits

    def randpath():
        return "".join(rng.choices(chars, k=10))

    methods = "GET", "POST"
    routes = [f"/{randpath()}/{randpath()}" for _ in range(100)]
    routes += [f"/{randpath()}/{{item}}/{randpath()}" for _ in range(100)]
    rng.shuffle(routes)

    paths = []
    for route in routes:
        router.route(route, methods=rng.choice(methods))("OK")
        paths.append(route.format(item=randpath()))

    def do_work():
        router.match.cache_clear()
        for path in paths:
            with suppress(router.InvalidMethodError):
                assert router(path)

    benchmark(do_work)


# ruff: noqa: S311
