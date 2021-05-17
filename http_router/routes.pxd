# cython: language_level=3

from .router cimport Router


cdef class RouteMatch:

    cdef readonly bint path, method
    cdef readonly object target
    cdef readonly dict params


cdef class Route:

    cdef readonly str path
    cdef readonly set methods
    cdef readonly object target

    cpdef RouteMatch match(self, str path, str method)


cdef class DynamicRoute(Route):

    cdef readonly object pattern
    cdef readonly dict params


cdef class PrefixedRoute(Route):

    pass


cdef class Mount(PrefixedRoute):

    pass
