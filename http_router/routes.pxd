# cython: language_level=3
# cython: profile=True

from .router cimport Router


cdef class RouteMatch:

    cdef bint path, method
    cdef readonly object target
    cdef readonly dict params


cdef class BaseRoute:

    cdef readonly str path
    cdef readonly set methods

    cpdef RouteMatch match(self, str path, str method)

cdef class Route(BaseRoute):

    cdef readonly object target


cdef class DynamicRoute(Route):

    cdef readonly object pattern
    cdef readonly dict params


cdef class Mount(BaseRoute):

    cdef readonly Router router
    cdef readonly object route
