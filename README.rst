HTTP Router
###########

.. _description:

**http-router** -- A simple router for HTTP applications

The library is not a HTTP framework. It's an utilite to build the frameworks.
The main goal of the library to bind targets to http routes and match them.

.. _badges:

.. image:: https://github.com/klen/http-router/workflows/tests/badge.svg
    :target: https://github.com/klen/http-router/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/http-router
    :target: https://pypi.org/project/http-router/
    :alt: PYPI Version

.. image:: https://img.shields.io/pypi/pyversions/http-router
    :target: https://pypi.org/project/http-router/
    :alt: Python Versions

.. _contents:

.. contents::


.. _requirements:

Requirements
=============

- python 3.9, 3.10, 3.11, 3.12, 3.13, pypy3


.. _installation:

Installation
=============

**http-router** should be installed using pip: ::

    pip install http-router


Usage
=====

Create a router:

.. code:: python

    from http_router import Router


    # Initialize the router
    router = Router(trim_last_slash=True)


Define routes:

.. code:: python

    @router.route('/simple')
    def simple():
        return 'result from the fn'

Call the router with HTTP path and optionally method to get a match result.

.. code:: python

   match = router('/simple', method='GET')
   assert match, 'HTTP path is ok'
   assert match.target is simple

The router supports regex objects too:

.. code:: python

    import re

    @router.route(re.compile(r'/regexp/\w{3}-\d{2}/?'))
    def regex():
        return 'result from the fn'

But the lib has a simplier interface for the dynamic routes:

.. code:: python

    @router.route('/users/{username}')
    def users():
        return 'result from the fn'

By default this will capture characters up to the end of the path or the next
``/``.

Optionally, you can use a converter to specify the type of the argument like
``{variable_name:converter}``.

Converter types:

========= ====================================
``str``   (default) accepts any text without a slash
``int``   accepts positive integers
``float`` accepts positive floating point values
``path``  like string but also accepts slashes
``uuid``  accepts UUID strings
========= ====================================

Convertors are used by prefixing them with a colon, like so:

.. code:: python

    @router.route('/orders/{order_id:int}')
    def orders():
        return 'result from the fn'

Any unknown convertor will be parsed as a regex:

.. code:: python

    @router.route('/orders/{order_id:\d{3}}')
    def orders():
        return 'result from the fn'


Multiple paths are supported as well:

.. code:: python

    @router.route('/', '/home')
    def index():
        return 'index'


Handling HTTP methods:

.. code:: python

    @router.route('/only-post', methods=['POST'])
    def only_post():
        return 'only-post'


Submounting routes:

.. code:: python

   subrouter = Router()

   @subrouter.route('/items/{item}')
   def items():
        pass

    router = Router()
    router.route('/api')(subrouter)


   match = router('/api/items/12', method='GET')
   assert match, 'HTTP path is ok'
   assert match.target is items
    assert match.params == {"item": "12"}


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
