import re
from collections import defaultdict
from urllib.parse import unquote


__version__ = "0.1.0"
__license__ = "MIT"


DYNR_RE = re.compile(r'^\{\s*(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<re>.+))*\s*\}$')
DYNS_RE = re.compile(r'(\{[^{}]*\})')
METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATH"}
RETYPE = type(re.compile('@'))


class RouterError(Exception):
    pass


class NotFound(RouterError):
    pass


class MethodNotAllowed(RouterError):
    pass


class Route:
    """Base plain route class."""

    def __init__(self, pattern, methods=None):
        if not isinstance(methods, (list, tuple)):
            methods = [methods]
        methods = set([m.upper() for m in methods if isinstance(m, str)])
        self.methods = methods & METHODS
        self.pattern = pattern

    def match(self, path):
        return path == self.pattern and {}

    def __hash__(self):
        return self.pattern

    def __repr__(self):
        return "<%s %r %r>" % (self.__class__.__name__, self.methods, self.pattern)


class DynamicRoute(Route):
    """Base dynamic route class."""

    def __init__(self, pattern, methods=None):
        super(DynamicRoute, self).__init__(pattern, methods)
        if isinstance(self.pattern, str):
            self.pattern = parse(self.pattern)

    def match(self, path):
        match = self.pattern.match(path)
        if match:
            return {key: unquote(value) for key, value in match.groupdict('').items()}


class Router:
    """Keep routes."""

    NotFound = NotFound
    RouterError = RouterError
    MethodNotAllowed = MethodNotAllowed

    def __init__(self, raise_not_found=True, trim_last_slash=False):
        self.plain = defaultdict(list)
        self.trim_last_slash = trim_last_slash
        self.raise_not_found = raise_not_found
        self.dynamic = list()

    def __call__(self, path, method="GET"):
        if self.trim_last_slash:
            path = path.rstrip('/') or '/'

        methods = set()
        for route, cb in self.plain.get(path, self.dynamic):
            match = route.match(path)
            if match is not None:
                methods |= route.methods
                if route.methods and method not in route.methods:
                    continue

                return cb, match

        if self.raise_not_found:
            if methods:
                raise self.MethodNotAllowed(path, method)

            raise self.NotFound(path, method)

    def bind(self, callback, *paths, methods=None):
        for path in paths:
            pattern = parse(path)
            if isinstance(pattern, RETYPE):
                self.dynamic.append((DynamicRoute(pattern, methods), callback))
                continue

            self.plain[pattern].append((Route(pattern, methods), callback))

    def route(self, path, *paths, methods=None):
        """Register a route."""

        if callable(path):
            raise RouterError('`route` cannot be used as a decorator without params (paths)')

        def wrapper(callback):
            self.bind(callback, path, *paths, methods=methods)
            return callback

        return wrapper


def parse(path):
    """Parse URL path and convert it to regexp if needed."""
    path = path.strip(' ')

    def parse_(match):
        [part] = match.groups()
        match = DYNR_RE.match(part)
        params = match.groupdict()
        params['re'] = params['re'] or '[^/]+'
        return '(?P<%s>%s)' % (params['var'], params['re'].strip())

    pattern = DYNS_RE.sub(parse_, path)

    parsed = re.sre_parse.parse(pattern)
    for case, _ in parsed:
        if case not in (re.sre_parse.LITERAL, re.sre_parse.ANY):
            break
    else:
        return pattern

    pattern = pattern.rstrip('$')
    return re.compile('%s$' % pattern)

# pylama: ignore=D
