"""Host-restricted route tests."""
from __future__ import annotations

import pytest

from http_router import Router


@pytest.mark.parametrize("host", [None, "a.example.com"])
def test_route_without_hosts_matches_any_host(router: Router, host):
    router.route("/search")("search")

    assert router("/search", host=host).target == "search"


@pytest.mark.parametrize("path", ["/reports", "/reports/{id}"])
def test_route_matches_only_its_hosts(router: Router, path):
    router.route(path, hosts="admin.example.com")("admin")
    request_path = path.format(id="42")

    assert router(request_path, host="admin.example.com").target == "admin"
    with pytest.raises(router.NotFoundError):
        router(request_path, host="www.example.com")
    with pytest.raises(router.NotFoundError):
        router(request_path)


def test_route_matches_any_of_its_hosts(router: Router):
    router.route("/users", hosts=("a.example.com", "b.example.com"))("users")

    assert router("/users", host="a.example.com").target == "users"
    assert router("/users", host="b.example.com").target == "users"
    with pytest.raises(router.NotFoundError):
        router("/users", host="c.example.com")


@pytest.mark.parametrize("host", ["admin", "Admin.example.com", "admin.example.com:8080"])
def test_hosts_are_compared_verbatim(router: Router, host):
    router.route("/reports", hosts="admin.example.com")("reports")

    with pytest.raises(router.NotFoundError):
        router("/reports", host=host)


@pytest.mark.parametrize(
    ("path", "host", "expected"),
    [
        ("/items/new", "admin.example.com", "new"),
        ("/items/new", "www.example.com", "item"),
        ("/items/1", "admin.example.com", "item"),
    ],
)
def test_route_for_another_host_falls_through(router: Router, path, host, expected):
    router.route("/items/new", hosts="admin.example.com")("new")
    router.route("/items/{item}")("item")

    assert router(path, host=host).target == expected


def test_route_for_another_host_is_not_a_path_match(router: Router):
    router.route("/reports", hosts="admin.example.com")("reports")

    match = router.match("/reports", "GET", "www.example.com")

    assert (match.path, match.method) == (False, False)


@pytest.mark.parametrize("admin_first", [True, False])
def test_method_mismatch_on_the_host_outranks_another_host(router: Router, admin_first):
    routes = [
        ("/reports", "POST", "admin.example.com"),
        ("/reports", "GET", "www.example.com"),
    ]
    for path, method, host in routes if admin_first else reversed(routes):
        router.route(path, methods=method, hosts=host)(host)

    match = router.match("/reports", "GET", "admin.example.com")

    assert (match.path, match.method) == (True, False)
    with pytest.raises(router.InvalidMethodError):
        router("/reports", "GET", host="admin.example.com")


def test_match_accepts_host_positionally_and_caches_per_host(router: Router):
    router.route("/reports", hosts="admin.example.com")("reports")

    assert router.match("/reports", "GET", "admin.example.com").target == "reports"
    assert not router.match("/reports", "GET", "www.example.com")
    assert router.match("/reports", "GET", "admin.example.com").target == "reports"


def test_hosts_is_not_passed_to_target(router: Router):
    @router.route("/params", hosts="admin.example.com", var="value")
    def params(**opts):
        return opts

    assert router("/params", host="admin.example.com").target() == {"var": "value"}


def test_method_shortcut_accepts_hosts(router: Router):
    router.post("/reports", hosts="admin.example.com")("reports")

    assert router("/reports", "POST", host="admin.example.com").target == "reports"


def test_bind_accepts_hosts(router: Router):
    (route,) = router.bind("reports", "/reports", hosts="admin.example.com")

    assert route.hosts == {"admin.example.com"}
    assert router("/reports", host="admin.example.com").target == "reports"


def test_mount_matches_only_its_hosts():
    child = Router()
    child.route("/users")("users")
    root = Router()
    root.route("/api", hosts="api.example.com")(child)

    assert root("/api/users", host="api.example.com").target == "users"
    with pytest.raises(root.NotFoundError):
        root("/api/users", host="www.example.com")
    assert not root.match("/api/users", "GET", "www.example.com").path


@pytest.mark.parametrize(
    ("host", "expected"), [("a.example.com", "a_users"), ("b.example.com", "users")],
)
def test_mount_passes_host_to_mounted_router(host, expected):
    child = Router()
    child.route("/users", hosts="a.example.com")("a_users")
    child.route("/users")("users")
    root = Router()
    root.route("/api")(child)

    assert root("/api/users", host=host).target == expected
