# cython: language_level=3


cdef class Router:

    cdef readonly dict plain
    cdef readonly list dynamic

    cdef public bint trim_last_slash
    cdef public object validator
    cdef public object converter
