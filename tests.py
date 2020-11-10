"""HTTP Router tests."""

import pytest


def test_route():
    from http_router import Route

    route = Route('/only-post', ['POST', 'PUT'])
    assert route.match('/only-post', 'POST') is not None
    assert route.match('/only-post', 'PUT') is not None
    assert route.match('/only-post', 'GET') is None


def test_dynamic_route():
    from http_router import DynamicRoute

    route = DynamicRoute(r'/order/{id:\d+}')
    assert {'id': '100'} == route.match('/order/100', 'POST')
    assert not route.match('/order/unknown', 'POST')


def test_router():
    """Base tests."""
    from http_router import Router

    router = Router(trim_last_slash=True)

    router.route('/', '/simple')(lambda: 'simple')
    router.route('/regex(/opt)?')(lambda: 'opt')
    router.route('/only-post', methods='post')(lambda: 'only-post')
    router.route(r'/hello/{name:\w+}/?', methods='post')(lambda: 'dyn')

    with pytest.raises(router.NotFound):
        assert router('/unknown')

    cb, opts = router('/', 'POST')
    assert cb() == 'simple'
    assert opts == {}

    cb, opts = router('/simple', 'DELETE')
    assert cb() == 'simple'
    assert opts == {}

    cb, opts = router('/regex', 'PATCH')
    assert cb() == 'opt'
    assert opts == {}

    cb, opts = router('/regex/opt', 'PATCH')
    assert cb() == 'opt'
    assert opts == {}

    cb, opts = router('/only-post', 'POST')
    assert cb() == 'only-post'
    assert opts == {}

    with pytest.raises(router.NotFound):
        assert router('/only-post')

    cb, opts = router('/hello/john/', 'POST')
    assert cb() == 'dyn'
    assert opts == {'name': 'john'}


#  pylama:ignore=D
