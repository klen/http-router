# cython: language_level=3

from .routes cimport DynamicRoute, Mount, Route, RouteMatch


cdef class Router:

    cdef readonly object plain
    cdef readonly list dynamic

    cdef public bint trim_last_slash
    cdef public object validator
    cdef public object converter
