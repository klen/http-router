"""HTTP Router tests."""

import inspect
import typing as t
from re import compile as re

import pytest


@pytest.fixture
def router():
    from http_router import Router, NotFound, MethodNotAllowed, RouterError

    return Router()


def test_router_basic(router):
    assert router
    assert not router.trim_last_slash
    assert router.validator
    assert router.NotFound
    assert router.RouterError
    assert router.MethodNotAllowed


def test_router_route_re(router):
    router.route(re('test.jpg'))('test1 passed')
    assert router('test.jpg').target == 'test1 passed'
    assert router('testAjpg').target == 'test1 passed'
    assert router('testAjpg/regex/can/be/dangerous').target == 'test1 passed'

    router.route(re(r'params/(\w+)'))('test2 passed')
    match = router('params/mike')
    assert match
    assert not match.path_params

    router.route(re(r'params2/(?P<User>\w+)'))('test3 passed')
    match = router('params2/mike')
    assert match
    assert match.path_params == {'User': 'mike'}


def test_router_route_str(router):
    router.route('test.jpg')(True)
    match = router('test.jpg')
    assert match

    with pytest.raises(router.NotFound):
        router('test.jpeg')

    router.route('/any/{item}')(True)
    match = router('/any/test')
    assert match
    assert match.path_params == {'item': 'test'}

    router.route('/str/{item:str}')(True)
    match = router('/str/42')
    assert match
    assert match.path_params == {'item': '42'}

    router.route('/int/{item:int}')(True)
    match = router('/int/42')
    assert match
    assert match.path_params == {'item': 42}

    router.route(r'/regex/{item:\d{3}}')(True)
    match = router('/regex/422')
    assert match
    assert match.path_params == {'item': '422'}


def test_parse_path():
    from http_router.utils import parse_path

    assert parse_path('/') == ('/', None, {})
    assert parse_path('/test.jpg') == ('/test.jpg', None, {})
    assert parse_path('/{foo') == ('/{foo', None, {})

    path, regex, params = parse_path(r'/{foo}/')
    assert isinstance(regex, t.Pattern)
    assert regex.pattern == r'^/(?P<foo>[^/]+)/$'
    assert path == '/{foo}/'
    assert params == {'foo': str}

    path, regex, params = parse_path(r'/{foo:int}/')
    assert isinstance(regex, t.Pattern)
    assert regex.pattern == r'^/(?P<foo>\d+)/$'
    assert path == '/{foo}/'
    assert params == {'foo': int}

    path, regex, params = parse_path(re(r'/(?P<foo>\d{1,3})/'))
    assert isinstance(regex, t.Pattern)
    assert params == {}
    assert path

    path, regex, params = parse_path(r'/api/v1/items/{item:str}/subitems/{ subitem:\d{3} }/find')
    assert path == '/api/v1/items/{item}/subitems/{subitem}/find'
    assert regex.match('/api/v1/items/foo/subitems/300/find')
    assert params['item']
    assert params['subitem']


def test_route():
    from http_router.routes import Route

    route = Route('/only-post', ['POST'])
    assert route.methods
    assert route.match('/only-post', 'POST')
    assert not route.match('/only-post')

    route = Route('/only-post')
    assert not route.methods


def test_dynamic_route():
    from http_router.routes import DynamicRoute

    route = DynamicRoute(r'/order/{id:int}')
    match = route.match('/order/100')
    assert match.path
    assert match.path_params == {'id': 100}

    match = route.match('/order/unknown')
    assert not match
    assert not match.path_params

    route = DynamicRoute(re('/regex(/opt)?'))
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

    router.route('/only-post', methods='post')('only-post')
    assert router.plain['/only-post'][0].methods == {'POST'}

    with pytest.raises(router.MethodNotAllowed):
        assert router('/only-post')

    cb, opts = router('/only-post', 'POST')
    assert cb == 'only-post'
    assert not opts

    router.route('/dynamic1/{id}')('dyn1')
    router.route('/dynamic2/{ id }')('dyn2')

    cb, opts = router('/dynamic1/11/')
    assert cb == 'dyn1'
    assert opts == {'id': '11'}

    cb, opts = router('/dynamic2/22/')
    assert cb == 'dyn2'
    assert opts == {'id': '22'}

    @router.route(r'/hello/{name:str}', methods='post')
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
    from http_router import Router
    from http_router.routes import Mount

    route = Mount('/api/')
    assert route.path == '/api'
    match = route.match('/api/e1')
    assert not match

    route.route('/e1')('e1')
    match = route.match('/api/e1')
    assert match
    assert match.target == 'e1'

    root = Router()
    subrouter = Router()

    root.route('/api')(1)
    root.route(re('/api/test'))(2)
    root.route('/api')(subrouter)
    subrouter.route('/test')(3)

    assert root('/api').target == 1
    assert root('/api/test').target == 3


def test_trim_last_slash():
    from http_router import Router

    router = Router()

    router.route('/route1')('route1')
    router.route('/route2/')('route2')

    assert router('/route1').target == 'route1'
    assert router('/route2/').target == 'route2'

    with pytest.raises(router.NotFound):
        assert not router('/route1/')

    with pytest.raises(router.NotFound):
        assert not router('/route2')

    router = Router(trim_last_slash=True)

    router.route('/route1')('route1')
    router.route('/route2/')('route2')

    assert router('/route1').target == 'route1'
    assert router('/route2/').target == 'route2'
    assert router('/route1/').target == 'route1'
    assert router('/route2').target == 'route2'


def test_cb_validator():
    from http_router import Router

    # The router only accepts async functions
    router = Router(validator=inspect.iscoroutinefunction)

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
    assert cb == 'child_url'


def test_readme():
    from http_router import Router

    router = Router(trim_last_slash=True)

    @router.route('/simple')
    def simple():
        return 'simple'

    fn, path_params = router('/simple')
    assert fn() == 'simple'
    assert path_params is None


def test_method_shortcuts(router):
    router.delete('/delete')('DELETE')
    router.get('/get')('GET')
    router.post('/post')('POST')

    for route in router.routes():
        method = route.target
        assert route.methods == {method}


#  pylama:ignore=D
