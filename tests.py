"""HTTP Router tests."""

import pytest


def test_parse():
    from http_router import parse, RETYPE

    assert isinstance(parse('/'), str)
    assert isinstance(parse('/test.jpg'), str)
    assert isinstance(parse('/{foo'), str)

    res = parse(r'/{foo}/')
    assert isinstance(res, RETYPE)
    assert res.pattern == r'/(?P<foo>[^/]+)/$'

    res = parse(r'/{foo}/?')
    assert isinstance(res, RETYPE)
    assert res.pattern == r'/(?P<foo>[^/]+)/?$'

    res = parse(r'/{foo:\d+}/')
    assert isinstance(res, RETYPE)
    assert res.pattern == r'/(?P<foo>\d+)/$'

    res = parse(r'/{foo:\d{1,3}}/')
    assert isinstance(res, RETYPE)
    assert res.pattern == r'/(?P<foo>\d{1,3})/$'


def test_route():
    from http_router import Route

    route = Route('/only-post', ['POST', 'PUT'])
    assert route.match('/only-post') is not None


def test_dynamic_route():
    from http_router import DynamicRoute

    route = DynamicRoute(r'/order/{id:\d+}')
    assert {'id': '100'} == route.match('/order/100')
    assert not route.match('/order/unknown')


def test_router():
    """Base tests."""
    from http_router import Router

    router = Router(trim_last_slash=True)

    router.route('/', '/simple')(lambda: 'simple')
    router.route('/regex(/opt)?')(lambda: 'opt')
    router.route('/only-post', methods='post')(lambda: 'only-post')
    router.route(r'/dynamic1/{id}/?')(lambda: 'dyn1')
    router.route(r'/dynamic2/{ id }/?')(lambda: 'dyn2')

    with pytest.raises(router.RouterError):
        router.route(lambda: 12)

    with pytest.raises(router.NotFound):
        assert router('/unknown')

    with pytest.raises(router.MethodNotAllowed):
        assert router('/only-post')

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

    cb, opts = router('/dynamic1/11/')
    assert cb() == 'dyn1'
    assert opts == {'id': '11'}

    cb, opts = router('/dynamic2/22/')
    assert cb() == 'dyn2'
    assert opts == {'id': '22'}

    @router.route(r'/hello/{ name:\w+ }/?', methods='post')
    def hello():
        return 'hello'

    cb, opts = router('/hello/john/', 'POST')
    assert cb() == 'hello'
    assert opts == {'name': 'john'}

    @router.route('/params', var='value')
    def params(**opts):
        return opts

    cb, opts = router('/params', 'POST')
    assert cb() == {'var': 'value'}

#  pylama:ignore=D
