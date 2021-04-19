"""Setup the library."""

from setuptools import setup, Extension


setup(
    ext_modules=[
        Extension("http_router.router", ["http_router/router.c"], extra_compile_args=['-O2']),
        Extension("http_router.routes", ["http_router/routes.c"], extra_compile_args=['-O2']),
    ]
)
