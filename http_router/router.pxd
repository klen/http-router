# cython: language_level=3


cdef class Router:

    cdef public bint trim_last_slash
    cdef public object validator
    cdef public dict plain
    cdef public list dynamic
