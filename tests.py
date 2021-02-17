"""HTTP Router tests."""

import inspect
import pytest
import typing as t


def test_parse():
    from http_router import parse

    assert isinstance(parse('/'), str)
    assert isinstance(parse('/test.jpg'), str)
    assert isinstance(parse('/{foo'), str)

    res = parse(r'/{foo}/')
    assert isinstance(res, t.Pattern)
    assert res.pattern == r'/(?P<foo>[^/]+)/$'

    res = parse(r'/{foo}/?')
    assert isinstance(res, t.Pattern)
    assert res.pattern == r'/(?P<foo>[^/]+)/?$'

    res = parse(r'/{foo:\d+}/')
    assert isinstance(res, t.Pattern)
    assert res.pattern == r'/(?P<foo>\d+)/$'

    res = parse(r'/{foo:\d{1,3}}/')
    assert isinstance(res, t.Pattern)
    assert res.pattern == r'/(?P<foo>\d{1,3})/$'


def test_route():
    from http_router import Route

    route = Route('/only-post', ['POST'])
    assert route.methods
    assert route.match('/only-post', 'POST')
    assert not route.match('/only-post')

    route = Route('/only-post')
    assert not route.methods


def test_dynamic_route():
    from http_router import DynamicRoute

    route = DynamicRoute(r'/order/{id:\d+}')
    match = route.match('/order/100')
    assert match.path
    assert match.path_params == {'id': '100'}

    match = route.match('/order/unknown')
    assert not match
    assert not match.path_params

    route = DynamicRoute('/regex(/opt)?')
    match = route.match('/regex')
    assert match

    match = route.match('/regex/opt')
    assert match


def test_router():
    """Base tests."""
    from http_router import Router

    router = Router(trim_last_slash=True)

    with pytest.raises(router.RouterError):
        router.route(lambda: 12)

    with pytest.raises(router.NotFound):
        assert router('/unknown')

    router.route('/', '/simple')('simple')

    cb, opts = router('/', 'POST')
    assert cb == 'simple'
    assert not opts

    cb, opts = router('/simple', 'DELETE')
    assert cb == 'simple'
    assert not opts

    router.route('/regex(/opt)?', methods=('GET', 'PATCH'))('opt')

    cb, opts = router('/regex', 'PATCH')
    assert cb == 'opt'
    assert not opts

    cb, opts = router('/regex/opt', 'PATCH')
    assert cb == 'opt'
    assert not opts

    router.route('/only-post', methods='post')('only-post')
    assert router.plain['/only-post'][0].methods == {'POST'}

    with pytest.raises(router.MethodNotAllowed):
        assert router('/only-post')

    cb, opts = router('/only-post', 'POST')
    assert cb == 'only-post'
    assert not opts

    router.route(r'/dynamic1/{id}/?')('dyn1')
    router.route(r'/dynamic2/{ id }/?')('dyn2')

    cb, opts = router('/dynamic1/11/')
    assert cb == 'dyn1'
    assert opts == {'id': '11'}

    cb, opts = router('/dynamic2/22/')
    assert cb == 'dyn2'
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

    assert router.routes()
    assert router.routes()[0].path == '/'


def test_mounts():
    from http_router import Mount

    route = Mount('/api/')
    assert route.pattern == '/api'
    match = route.match('/api/e1')
    assert not match

    route.route('/e1')('e1')
    match = route.match('/api/e1')
    assert match
    assert match.callback == 'e1'


def test_cb_validator():
    from http_router import Router

    # The router only accepts async functions
    router = Router(validate_cb=inspect.iscoroutinefunction)

    with pytest.raises(router.RouterError):
        router.route('/', '/simple')(lambda: 'simple')


def test_custom_route():
    from http_router import Router

    class View:

        methods = 'get', 'post'

        def __new__(cls, *args, **kwargs):
            """Init the class and call it."""
            self = super().__new__(cls)
            return self(*args, **kwargs)

        @classmethod
        def __route__(cls, router, *paths, **params):
            return router.bind(cls, *paths, methods=cls.methods)

    # The router only accepts async functions
    router = Router()
    router.route('/')(View)
    assert router.plain['/'][0].methods == {'GET', 'POST'}
    cb, opts = router('/')
    assert cb is View


def test_nested_routers():
    from http_router import Router

    child = Router()
    child.route('/url', methods='PATCH')('child_url')
    cb, _ = child('/url', 'PATCH')
    assert cb == 'child_url'

    root = Router()
    root.route('/child')(child)

    with pytest.raises(root.NotFound):
        root('/child')

    with pytest.raises(root.NotFound):
        root('/child/unknown')

    with pytest.raises(root.MethodNotAllowed):
        root('/child/url')

    cb, _ = root('/child/url', 'PATCH')
    assert cb is 'child_url'


def test_readme():
    from http_router import Router

    router = Router(trim_last_slash=True)

    @router.route('/simple')
    def simple():
        return 'simple'

    fn, path_params = router('/simple')
    assert fn() == 'simple'
    assert path_params is None

#  pylama:ignore=D
