# cython: language_level=3

from .routes cimport RouteMatch


cdef class Router:

    cdef readonly bint trim_last_slash
    cdef readonly object validator
    cdef public dict plain
    cdef public list dynamic
