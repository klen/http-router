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


    router = Router(trim_last_slash=True)

    # Plain path
    @router.route('/simple')
    def simple(request):
        return 'simple'

    # Multiple paths are supported
    @router.route('/', '/home')
    def index(request):
        return 'index'

    # Bind HTTP Methods
    @router.route('/only-post', methods=['POST'])
    def only_post(request):
        return 'only-post'

    # Regex Expressions are supported
    @router.route('/regex(/opt)?')
    def optional(request):
        return 'opt'

    # Dynamic routes are here
    @router.route('/order/{id}')
    def order1(request, id=None):
        return 'order-%s' % id

    # Dynamic routes with regexp
    @router.route('/order/{id:\d+}')
    def order2(request, id=None):
        return 'order-%s' % id


    print(router('/order/100'))
    # {'id': '100'}, <function order2>


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

