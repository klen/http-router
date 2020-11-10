import re
from collections import defaultdict
from urllib.parse import unquote


__version__ = "0.0.0"
__license__ = "MIT"


DYNR_RE = re.compile(r'^\{(?P<var>[a-zA-Z][_a-zA-Z0-9]*)(?::(?P<re>.+))*\}$')
DYNS_RE = re.compile(r'(\{[^{}]*\})')
METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATH"}
RETYPE = type(re.compile('@'))


class NotFound(Exception):
    pass


class Route:
    """Base plain route class."""

    def __init__(self, pattern, methods=None):
        if not isinstance(methods, (list, tuple)):
            methods = [methods]
        methods = set([m.upper() for m in methods if isinstance(m, str)])
        self.methods = methods & METHODS
        self.pattern = pattern

    def match(self, path, method="GET"):
        return (
            (not self.methods or method in self.methods) and
            path == self.pattern
        ) or None

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

    def match(self, path, method="GET"):
        if self.methods and method not in self.methods:
            return

        match = self.pattern.match(path)
        if match:
            return {key: unquote(value) for key, value in match.groupdict('').items()}


class Router:
    """Keep routes."""

    NotFound = NotFound

    def __init__(self, default=None, trim_last_slash=False):
        self.plain = defaultdict(list)
        self.trim_last_slash = trim_last_slash
        self.dynamic = list()
        if default:
            self.default = default

    def __call__(self, path, method="GET"):
        if self.trim_last_slash:
            path = path.rstrip('/') or '/'
        for route, cb in self.plain.get(path, self.dynamic):
            match = route.match(path, method)
            if match is not None:
                return match, cb

        return None, self.default(path, method)

    def bind(self, callback, *paths, methods=None):
        for path in paths:
            pattern = parse(path)
            if isinstance(pattern, RETYPE):
                self.dynamic.append((DynamicRoute(pattern, methods), callback))
                continue

            self.plain[pattern].append((Route(pattern, methods), callback))

    def default(self, path, method):
        """The default callback."""
        raise NotFound(path, method)

    def route(self, *paths, methods=None):
        """Register a route."""

        def wrapper(callback):
            self.bind(callback, *paths, methods=methods)
            return callback

        # Support for @app.register(func)
        if len(paths) == 1 and callable(paths[0]):
            callback = paths[0]

            paths = []
            return wrapper(callback)

        return wrapper


def parse(path):
    """Parse URL path and convert it to regexp if needed."""
    path = path.strip(' ')

    def parse_(match):
        [part] = match.groups()
        match = DYNR_RE.match(part)
        params = match.groupdict()
        return '(?P<%s>%s)' % (params['var'], params['re'] or '[^/]+')

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
