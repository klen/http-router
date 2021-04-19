"""Setup the library."""

from setuptools import setup, Extension


COMPILE_ARGS = ["-O2"]


setup(
    ext_modules=[
        Extension("http_router.router", ["http_router/router.c"], extra_compile_args=COMPILE_ARGS),
        Extension("http_router.routes", ["http_router/routes.c"], extra_compile_args=COMPILE_ARGS),
    ]
)
