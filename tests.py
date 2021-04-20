"""HTTP Router tests."""

import inspect
import typing as t
from re import compile as re

import pytest


@pytest.fixture
def router():
    from http_router import Router, NotFound, MethodNotAllowed, RouterError  # noqa

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
    assert not match.params

    router.route(re(r'params2/(?P<User>\w+)'))('test3 passed')
    match = router('params2/mike')
    assert match
    assert match.params == {'User': 'mike'}


def test_router_route_str(router):
    router.route('test.jpg')(True)
    match = router('test.jpg')
    assert match

    with pytest.raises(router.NotFound):
        router('test.jpeg')

    router.route('/any/{item}')(True)
    match = router('/any/test')
    assert match
    assert match.params == {'item': 'test'}

    router.route('/str/{item:str}')(True)
    match = router('/str/42')
    assert match
    assert match.params == {'item': '42'}

    router.route('/int/{item:int}')(True)
    match = router('/int/42')
    assert match
    assert match.params == {'item': 42}

    router.route(r'/regex/{item:\d{3}}')(True)
    match = router('/regex/422')
    assert match
    assert match.params == {'item': '422'}


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

    route = Route('/only-post', {'POST'}, None)
    assert route.methods
    assert route.match('/only-post', 'POST')
    assert not route.match('/only-post', '')

    route = Route('/only-post', set(), None)
    assert not route.methods


def test_dynamic_route():
    from http_router.routes import DynamicRoute

    route = DynamicRoute(r'/order/{id:int}', set(), None)
    match = route.match('/order/100', '')
    assert match
    assert match.params == {'id': 100}

    match = route.match('/order/unknown', '')
    assert not match
    assert not match.params

    route = DynamicRoute(re('/regex(/opt)?'), set(), None)
    match = route.match('/regex', '')
    assert match

    match = route.match('/regex/opt', '')
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

    match = router('/', 'POST')
    assert match.target == 'simple'
    assert not match.params

    match = router('/simple', 'DELETE')
    assert match.target == 'simple'
    assert not match.params

    router.route('/only-post', methods='post')('only-post')
    assert router.plain['/only-post'][0].methods == {'POST'}

    with pytest.raises(router.MethodNotAllowed):
        assert router('/only-post')

    match = router('/only-post', 'POST')
    assert match.target == 'only-post'
    assert not match.params

    router.route('/dynamic1/{id}')('dyn1')
    router.route('/dynamic2/{ id }')('dyn2')

    match = router('/dynamic1/11/')
    assert match.target == 'dyn1'
    assert match.params == {'id': '11'}

    match = router('/dynamic2/22/')
    assert match.target == 'dyn2'
    assert match.params == {'id': '22'}

    @router.route(r'/hello/{name:str}', methods='post')
    def hello():
        return 'hello'

    match = router('/hello/john/', 'POST')
    assert match.target() == 'hello'
    assert match.params == {'name': 'john'}

    @router.route('/params', var='value')
    def params(**opts):
        return opts

    match = router('/params', 'POST')
    assert match.target() == {'var': 'value'}

    assert router.routes()
    assert router.routes()[0].path == '/'


def test_mounts():
    from http_router import Router
    from http_router.routes import Mount

    route = Mount('/api/', set())
    assert route.path == '/api'
    match = route.match('/api/e1', '')
    assert not match

    route.route('/e1')('e1')
    match = route.match('/api/e1', 'GET')
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
    match = router('/')
    assert match.target is View


def test_nested_routers():
    from http_router import Router

    child = Router()
    child.route('/url', methods='PATCH')('child_url')
    match = child('/url', 'PATCH')
    assert match.target == 'child_url'

    root = Router()
    root.route('/child')(child)

    with pytest.raises(root.NotFound):
        root('/child')

    with pytest.raises(root.NotFound):
        root('/child/unknown')

    with pytest.raises(root.MethodNotAllowed):
        root('/child/url')

    match = root('/child/url', 'PATCH')
    assert match.target == 'child_url'


def test_readme():
    from http_router import Router

    router = Router(trim_last_slash=True)

    @router.route('/simple')
    def simple():
        return 'simple'

    match = router('/simple')
    assert match.target() == 'simple'
    assert match.params is None


def test_method_shortcuts(router):
    router.delete('/delete')('DELETE')
    router.get('/get')('GET')
    router.post('/post')('POST')

    for route in router.routes():
        method = route.target
        assert route.methods == {method}


def test_benchmark(router, benchmark):
    import random
    import string

    CHARS = string.ascii_letters + string.digits
    RANDOM = lambda: ''.join(random.choices(CHARS, k=10))  # noqa
    METHODS = ['GET', 'POST']

    routes = [f"/{ RANDOM() }/{ RANDOM() }" for _ in range(100)]
    routes += [f"/{ RANDOM() }/{{item}}/{ RANDOM() }" for _ in range(100)]
    random.shuffle(routes)

    paths = []
    for route in routes:
        router.route(route, methods=random.choice(METHODS))('OK')
        paths.append(route.format(item=RANDOM()))

    paths = [route.format(item=RANDOM()) for route in routes]

    def do_work():
        for path in paths:
            try:
                assert router(path)
            except router.MethodNotAllowed:
                pass

    benchmark.pedantic(do_work, iterations=10, rounds=100)


#  pylama:ignore=D
