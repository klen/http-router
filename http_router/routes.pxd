# cython: language_level=3

from .router cimport Router


cdef class RouteMatch:

    cdef readonly bint path, method
    cdef readonly object target
    cdef readonly object params


cdef class Route:

    cdef readonly str path
    cdef readonly object methods
    cdef readonly object hosts
    cdef readonly object target

    cpdef RouteMatch match(self, str path, str method, str host=*)


cdef class DynamicRoute(Route):

    cdef readonly object pattern
    cdef readonly dict params
    cdef readonly bint unquote


cdef class PrefixedRoute(Route):

    pass


cdef class Mount(PrefixedRoute):

    pass
