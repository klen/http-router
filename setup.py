"""Setup the library."""

import os
import sys
from setuptools import setup, Extension


NO_EXTENSIONS = (
    sys.implementation.name != 'cpython' or
    bool(os.environ.get("HTTP_ROUTER_NO_EXTENSIONS"))
)
EXT_MODULES = [] if NO_EXTENSIONS else [
    Extension("http_router.router", ["http_router/router.c"], extra_compile_args=['-O2']),
    Extension("http_router.routes", ["http_router/routes.c"], extra_compile_args=['-O2']),
]

setup(
    setup_requires=["wheel"],
    ext_modules=EXT_MODULES,
)
