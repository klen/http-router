"""Setup the library."""

import os
import sys

from Cython.Build import cythonize
from setuptools import setup

NO_EXTENSIONS = sys.implementation.name != "cpython" or bool(
    os.environ.get("HTTP_ROUTER_NO_EXTENSIONS")
)

print("*********************")
print("* Pure Python build *" if NO_EXTENSIONS else "* Accelerated build *")
print("*********************")

setup(
    setup_requires=["wheel"],
    ext_modules=[]
    if NO_EXTENSIONS
    else cythonize("http_router/*.pyx", language_level=3),
)
