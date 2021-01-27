HTTP Router
###########

.. _description:

**http-router** -- A simple router for HTTP applications

.. _badges:

.. image:: https://github.com/klen/http-router/workflows/tests/badge.svg
    :target: https://github.com/klen/http-router/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/http-router
    :target: https://pypi.org/project/http-router/
    :alt: PYPI Version

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.7

.. _installation:

Installation
=============

**http-router** should be installed using pip: ::

    pip install http-router


Usage
=====

.. code:: python
    
    from http_router import Router


    # Initialize the router
    router = Router(trim_last_slash=True)


    # Plain path
    # ----------
    @router.route('/simple')
    def simple():
        return 'simple'


    # Get a binded function and options by the given path
    fn, path_params = router('/simple')
    print(fn, path_params)
    #
    # >> <function simple> None
    #
    assert fn() == 'simple'

    # The Router will raise a Router.NotFound for an unknown path
    try:
        fn, path_params = router('/unknown')
    except router.NotFound as exc:
        print("%r" % exc)
        #
        # >> NotFound('/unknown', 'GET')
        #


    # Multiple paths are supported as well
    # ------------------------------------
    @router.route('/', '/home')
    def index():
        return 'index'


    print(router('/'))
    #
    # >> RouteMatch 200 (<function index>, None)
    #

    print(router('/home'))
    #
    # >> RouteMatch 200 (<function index>, None)
    #


    # Bind HTTP Methods
    # -----------------
    @router.route('/only-post', methods=['POST'])
    def only_post():
        return 'only-post'


    # The Router will raise a Router.MethodNotAllowed for an unsupported method
    try:
        print(router('/only-post', method='GET'))
    except router.MethodNotAllowed as exc:
        print("%r" % exc)

        #
        # >> MethodNotAllowed('/only-post', 'GET')
        #

    print(router('/only-post', method='POST'))
    #
    # >> RouteMatch 200 (<function only-post>, None)
    #


    # Regex Expressions are supported
    # -------------------------------
    @router.route('/regex(/opt)?')
    def optional():
        return 'opt'


    print(router('/regex', method='POST'))
    #
    # >> RouteMatch 200 (<function optional>, {})
    #

    print(router('/regex/opt', method='POST'))
    #
    # >> RouteMatch 200 (<function optional>, {})
    #


    # Dynamic routes are here
    # -----------------------
    @router.route('/order1/{id}')
    def order1(id=None):
        return 'order-%s' % id


    print(router('/order1/42'))
    #
    # >> RouteMatch 200 (<function order1>, {'id': '42'})
    #


    # Dynamic routes with regex
    # -------------------------
    @router.route(r'/order2/{ id:\d{3} }')
    def order2(id=None):
        return 'order-%s' % id


    print(router('/order2/100'))
    #
    # >> RouteMatch 200 (<function order1>, {'id': '100'})
    #

    try:
        print(router('/order2/03'))
    except router.NotFound:
        pass


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/http-router/issues

.. _contributing:

Contributing
============

Development of the project happens at: https://github.com/klen/http-router

.. _license:

License
========

Licensed under a `MIT license`_.


.. _links:

.. _klen: https://github.com/klen
.. _MIT license: http://opensource.org/licenses/MIT

