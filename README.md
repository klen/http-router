# http-router

[![Tests](https://github.com/klen/http-router/actions/workflows/tests.yml/badge.svg)](https://github.com/klen/http-router/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/http-router)](https://pypi.org/project/http-router/)
[![Python versions](https://img.shields.io/pypi/pyversions/http-router)](https://pypi.org/project/http-router/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A small, fast HTTP path router for Python.

Give it a URL path and an HTTP method, and it hands you the callable you bound
to that route — together with any path parameters it captured. No framework, no
request object, no magic.

```python
from http_router import Router

router = Router()

@router.get("/users/{id}")
def get_user(id):
    return {"id": id}

match = router("/users/42", "GET")
match.target(**match.params)  # {"id": "42"}
```

## Features

- Static (`/users`), dynamic (`/users/{id}`) and regex routes.
- Typed path parameters: `str`, `int`, `float`, `path`, `uuid`.
- Any HTTP method, with shortcuts like `router.get` and `router.post`.
- Compose applications from nested routers.
- Optional Cython acceleration, with a pure-Python fallback.
- Python 3.10+ (tested on 3.10–3.15 and PyPy).

## Install

```bash
pip install http-router
```

## Quick start

```python
from http_router import Router

router = Router()

@router.get("/health")
def health():
    return "ok"

@router.get("/users/{id}")
def get_user(id):
    return {"id": id}

@router.post("/users")
def create_user():
    return {"created": True}

result = router("/users/42", method="GET")
print(result)          # <RouteMatch path:True method:True - ...>
print(result.target)   # <function get_user>
print(result.params)   # {'id': '42'}
```

`router(...)` returns a `RouteMatch`:

| Attribute | Meaning |
|-----------|---------|
| `path` | Whether a route matched the path |
| `method` | Whether the route allows the HTTP method |
| `target` | The callable bound to the route |
| `params` | Captured path parameters, or `None` for static routes |

A `RouteMatch` is truthy only when **both** `path` and `method` match.

## Path parameters

Wrap a segment in `{...}` to capture it. Values are passed to the target as
keyword arguments.

```python
@router.route("/users/{id}")
def get_user(id):
    return {"user_id": id}

@router.route("/posts/{id}/comments")
def get_comments(id):
    return [{"post_id": id}]
```

### Converters

Add a type after `:` to validate the segment and convert its value.

| Converter | Example | Result |
|-----------|---------|--------|
| `str` (default) | `/users/{id}` | `"42"` |
| `int` | `/items/{id:int}` | `42` |
| `float` | `/price/{amount:float}` | `4.2` |
| `path` | `/files/{name:path}` | `"a/b/c"` (matches `/`) |
| `uuid` | `/u/{id:uuid}` | `UUID("...")` (case-insensitive) |

```python
@router.get("/items/{id:int}")
def get_item(id):
    return {"id": id}  # id is already an int
```

### Regex routes

Pass a compiled pattern to use your own regex. Only **named** groups become
parameters, and the pattern matches a prefix of the path, like `re.match`.

```python
from re import compile as re

@router.route(re(r"/orders/(?P<id>\d+)"))
def get_order(id):
    return {"id": id}
```

## HTTP methods

Restrict a route to one or more methods with `methods=`. Methods are matched
case-insensitively and stored uppercased.

```python
@router.route("/users", methods=["GET", "POST"])
def users():
    ...

# Shorthand for a single method:
@router.get("/health")
def health(): ...

@router.post("/users/{id}/ban")
def ban_user(id): ...

@router.put("/users/{id}")
def update_user(id): ...
```

A route registered without `methods` accepts every method.

## Nested routers

Build small routers and mount them under a prefix. The mounted router sees the
remaining path.

```python
api = Router()

@api.get("/users")
def list_users():
    return ["users"]

@api.get("/users/{id}")
def get_user(id):
    return {"id": id}

router = Router()
router.route("/api")(api)   # mount under /api

router("/api/users", "GET")     # → list_users
router("/api/users/42", "GET")  # → get_user(id="42")
```

## ASGI application

The router is not tied to any framework, so an ASGI app is a thin wrapper
around a lookup and a call. Targets may be async.

```python
import json

from http_router import InvalidMethodError, NotFoundError, Router

router = Router(unquote_params=False)  # ASGI paths are already decoded


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.route("/users", methods=["GET", "POST"])
async def users():
    return {"users": []}


@router.get("/users/{id:int}")
async def get_user(id):
    return {"id": id}


async def asgi(scope, receive, send):
    if scope["type"] != "http":
        return

    try:
        match = router(scope["path"], scope["method"])
    except NotFoundError:
        return await respond(send, 404, {"error": "not found"})
    except InvalidMethodError:
        return await respond(send, 405, {"error": "method not allowed"})

    await respond(send, 200, await match.target(**(match.params or {})))


async def respond(send, status, data):
    body = json.dumps(data).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})
```

Serve it with any ASGI server:

```bash
uvicorn app:asgi
```

## Errors

`router(...)` raises when it cannot resolve a request:

```python
from http_router import NotFoundError, InvalidMethodError

router("/nonexistent")            # NotFoundError
router("/users/42", "POST")       # InvalidMethodError (route only allows GET)
```

| Exception | When it is raised |
|-----------|-------------------|
| `NotFoundError` | No route matches the path |
| `InvalidMethodError` | The path matches, but the method is not allowed |
| `RouterError` | Base class; also raised for rejected targets |

If you want to check without raising, call `router.match(path, method)` — it returns
a falsy `RouteMatch` instead. Results are cached (1024 entries).

## API reference

### `Router(**kwargs)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `trim_last_slash` | `False` | Strip a trailing `/` before matching |
| `validator` | `always_true` | Must return `True` to accept a target |
| `converter` | `identity` | Transforms the target before binding |
| `unquote_params` | `True` | URL-decode captured parameters |

```python
router = Router(trim_last_slash=True)

# Reject targets that don't look like views:
router = Router(validator=lambda target: hasattr(target, "handle"))

# Wrap each bound target:
router = Router(converter=lambda target: lambda request: target())
```

Set `unquote_params=False` when the path is already decoded (for example in an
ASGI server).

### Router methods

```python
router(path, method="GET")                     # resolve, or raise RouterError
router.match(path, method)                     # resolve, never raises (cached)
router.route(*paths, methods=None, **opts)     # decorator / registrar
router.bind(target, *paths, methods=None, **opts)  # bind without a decorator
router.routes()                                # all routes, sorted by path
```

Extra `opts` are passed to the target as keyword arguments:

```python
@router.route("/params", var="value")
def params(**opts):
    return opts
```

```python
routes = router.bind(handler, "/users", "/api/users", methods="GET")
```

### Route classes

| Class | Description |
|-------|-------------|
| `Route` | Static path route (`/users`) |
| `DynamicRoute` | Pattern route with parameters (`/users/{id}`) |
| `PrefixedRoute` | Matches any path with a given prefix |
| `Mount` | A nested router mounted under a prefix |

## Development

```bash
uv sync --all-extras   # install dependencies
uv run pytest          # run the test suite
uv run ruff check .    # lint
uv run mypy            # type-check
```

## License

MIT
