"""HTTP Router tests."""

import pytest


def test_route():
    from http_router import Route

    route = Route('/only-post', ['POST', 'PUT'])
    assert route.match('/only-post', 'POST')
    assert route.match('/only-post', 'PUT')
    assert not route.match('/only-post', 'GET')


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

    _, cb = router('/', 'POST')
    assert cb() == 'simple'

    _, cb = router('/simple', 'DELETE')
    assert cb() == 'simple'

    _, cb = router('/regex', 'PATCH')
    assert cb() == 'opt'

    _, cb = router('/regex/opt', 'PATCH')
    assert cb() == 'opt'

    _, cb = router('/only-post', 'POST')
    assert cb() == 'only-post'

    with pytest.raises(router.NotFound):
        assert router('/only-post')

    params, cb = router('/hello/john/', 'POST')
    assert params == {'name': 'john'}
    assert cb() == 'dyn'


#  pylama:ignore=D
