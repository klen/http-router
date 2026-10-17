# http-router

A simple, fast HTTP path router for Python.

Find a target function by URL-path and HTTP-method — the way you'd expect it to work.

## Quick Start

```python
from http_router import Router

app = Router()

@app.route("/health", methods="GET")
def health():
    return "ok"

@app.get("/users/{id}")
def get_user(id):
    return {"id": id}

@app.post("/users")
def create_user():
    return {"created": True}

# Handling requests:
result = app("/users/42", method="GET")
print(result)  # RouteMatch with target + params {"id": "42"}
```

## API Reference

### Router

The main entry point. Map paths to callable targets and resolve requests.

```python
from http_router import Router
```

#### `Router(**kwargs)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `trim_last_slash` | `False` | Strip trailing `/` from paths before matching |
| `validator` | `always_true` | Callable that must return `True` for the target |
| `converter` | `identity` | Callable that transforms the target before binding |

```python
app = Router(trim_last_slash=True)
```

#### `router(path, method="GET")` → RouteMatch / raises

Resolve a path+method to a matched route, or raise an error.

```python
result = app("/users/42", method="GET")

# Errors:
app("/not-found", "GET")        # NotFoundError
app("/users/42", "POST")         # InvalidMethodError (route only accepts GET)
```

#### `@router.route(*paths, methods=None)` → decorator

Register one or more routes. Decorator form is the primary way to bind targets.

```python
@app.route("/api/v1/users", "/api/v2/users")  # multiple paths, same target
def list_users():
    ...

@app.route("/users", methods=["GET", "POST"])
def handle_users():
    ...

# Shortcut: app.get, app.post, app.put, etc.
@app.get("/users")
def get_users(): ...

@app.post("/users")
def create_user(): ...
```

#### `router.bind(target, *paths, methods=None)` → list[Route]

Low-level binding without the decorator. Returns created `Route` objects.

```python
routes = app.bind(handler, "/users", "/api/users", methods="GET")
```

#### `router.routes()` → list[Route]

Get all registered routes (sorted by path). Useful for introspection or debugging.

```python
for route in app.routes():
    print(route.path, route.methods)
```

#### `router.route(*paths)(subrouter)` — mount a nested router

Bind this router as a nested (mounted) router on another router.

```python
api = Router()

@api.route("/users")
def list_users():
    return ["users"]

# Mount at "/api" under the main app:
app.route("/api", methods="GET")(api)

# Now app("/api/users", "GET") resolves to list_users
```

### Route Classes

| Class | Description |
|-------|-------------|
| `Route` | Static path route (`/users`) |
| `DynamicRoute` | Pattern route with params (`/users/{id}`) |
| `PrefixedRoute` | Prefix-based match (`/api/*`) |
| `Mount` | Nested router support (combines Prefix + sub-routes) |

### Exceptions

| Exception | When it's raised |
|-----------|-----------------|
| `NotFoundError` | Path has no matching route |
| `InvalidMethodError` | Path matches but HTTP method is not allowed |
| `RouterError` | Base class; also raised for invalid targets |

```python
from http_router import RouterError, NotFoundError, InvalidMethodError

try:
    app("/nonexistent", "GET")
except NotFoundError as e:
    ...
```

## Dynamic Routes (Path Parameters)

Use `{name}` in paths to capture URL segments:

```python
@app.route("/users/{id}")
def get_user(id):
    return {"user_id": id}

@app.route("/posts/{id}/comments")
def get_comments(id):
    return [{"post_id": id}]

@app.route("/items/{id:int}")  # int: auto-cast to int
def get_item(id):
    return {"id": id}  # id is already an int
```

### Default Converters

| Converter | Example Path | Description |
|-----------|-------------|-------------|
| `str` (default) | `/users/{id}` | Any string |
| `int` | `/items/{id:int}` | Integer |
| `float` | `/price/{amount:float}` | Float |
| `path` | `/files/{filename:path}` | Path with slashes |

## Nested Routers (Mount)

Use `route()` to compose routers:

```python
api = Router()

@api.route("/users")
def list_users(): ...

@api.get("/users/{id}")
def get_user(id): ...

# Mount api under "/api" on the main app:
app.route("/api", methods="GET")(api)

# Now these work:
app("/api/users", "GET")          # → list_users
app("/api/users/42", "GET")      # → get_user(id="42")
```

## Configuration Tips

### Trim trailing slashes

```python
app = Router(trim_last_slash=True)
# "/users/" → matches "/users"
```

### Custom validator / converter

```python
def is_callable(obj):
    return callable(obj) and not obj.__module__ == "builtins"

app = Router(validator=is_callable)
```

## Benchmarks (Pure Python)

| Test | ~ms per request |
|------|-----------------|
| Static route match | 0.25 |
| Dynamic route with 1 param | 0.38 |
| 100 routes search | ~2.5 |

## License

MIT
