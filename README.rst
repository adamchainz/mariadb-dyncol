==============
mariadb-dyncol
==============

.. image:: https://img.shields.io/pypi/v/mariadb-dyncol.svg
    :target: https://pypi.python.org/pypi/mariadb-dyncol

.. image:: https://img.shields.io/travis/adamchainz/mariadb-dyncol/master.svg
        :target: https://travis-ci.org/adamchainz/mariadb-dyncol

.. image:: https://img.shields.io/pypi/dm/mariadb-dyncol.svg
        :target: https://pypi.python.org/pypi/mariadb-dyncol

Pack/unpack Python ``dict``\s into/out of MariaDB's **Dynamic Columns** format.

A quick example:

.. code-block:: python

    >>> mariadb_dyncol.pack({"key": "value"})
    b'\x04\x01\x00\x03\x00\x00\x00\x03\x00key!value'
    >>> mariadb_dyncol.unpack(mariadb_dyncol.pack({"key": "value"}))
    {'key': 'value'}

Features
========

* Sensible type mapping from Python to SQL
* Tested on Python 2.7, 3.4, and 3.5
* Tested against examples from MariaDB, including property/fuzz testing with
  `hypothesis <https://hypothesis.readthedocs.io/en/latest/>`_ (which is
  amazing and found many bugs)

Why?
====

The normal way for adding data into dynamic columns fields is with the
``COLUMN_CREATE`` function, and its relatives. This allows you to do things
like:

.. code-block:: sql

    INSERT INTO mytable (attrs) VALUES (COLUMN_CREATE('key', 'value'))

Unfortunately the Django ORM is restricted and cannot use database functions
like this in every instance, at least not until Django 1.9. It was this
limitation I hit whilst implementing a dynamic columns field for my project
`django-mysql <https://github.com/adamchainz/django-mysql>`_ that spurred the
creation of this library.

By pre-packing the dynamic columns, the above query can just insert the blob
of data directly:

.. code-block:: sql

    INSERT INTO mytable (attrs) VALUES (X'0401000300000003006B65792176616C7565')

Asides from being more easily implemented with the Django ORM, this approach
of packing/unpacking dynamic columns in Python also has some advantages:

* All data types are properly preserved in Python. The only way MariaDB
  provides of pulling back all values for a dynamic columns field is to call
  ``COLUMN_JSON``, but JSON only supports strings and integers. Also
  ``COLUMN_JSON`` has a depth limit of 10, but the format has no actual limit.
* The CPU overhead of packing/unpacking the dynamic columns is moved from you
  database server to your (presumably more scalable) clients.

API
===

All functions and names are accessible as attributes of the ``mariadb_dyncol``
module, which you can import with ``import mariadb_dyncol``.

``pack(mapping)``
-----------------

Packs the given mapping (a ``dict``) into the MariaDB Dynamic Columns
format for named columns and returns it as a byte string (Python 3's ``bytes``,
Python 2's ``str``). This is suitable for then inserting into a table as part
of a normal query.

The ``dict``\'s keys must all be unicode strings, and the values must all be
one of the supported data types:

* ``int`` between ``-(2 ** 32) + 1`` and ``(2 ** 64) - 1`` (Python 2: ``long``
  is supported too)
* ``str`` up to 4GB encoded in UTF-8 (Python 2: ``unicode``)
* ``float`` - anything except ``NaN`` or ``+/- inf``
* ``datetime.datetime`` - full range supported
* ``datetime.date`` - full range supported
* ``datetime.time`` - full range supported
* Any ``dict`` that is valid by these rules, allowing nested keys. There is no
  nesting limit except from for MariaDB's ``COLUMN_JSON`` function which
  restricts the depth to 10

Note that this does not support the ``DECIMAL`` type that MariaDB does (and
would naturally map to Python's ``Decimal``) - it is a little more fiddly to
pack/unpack, though certainly possible, and pull requests are welcomed. If you
try and pack a ``Decimal``, a ``DynColNotSupported`` exception will be raised.

There are other restrictions on the UTF-8 encoded column names as documented in
MariaDB:

* The maximum length of a column name is 16383 bytes
* The maximum length of all column names (at one level in nested hierarchies)
  is 65535 bytes

All other unsupported types will raise a ``DynColTypeError``. Out of range
values will raise a ``DynColValueError``.

Examples:

.. code-block:: python

    >>> mariadb_dyncol.pack({"a": 1})
    b'\x04\x01\x00\x01\x00\x00\x00\x00\x00a\x02'
    >>> mariadb_dyncol.pack({"a": "💩"})
    b'\x04\x01\x00\x01\x00\x00\x00\x03\x00a!\xf0\x9f\x92\xa9'

``unpack(bytestring)``
----------------------

Unpacks MariaDB dynamic columns data encoded byte string into a dict; the types
you can expect back are those listed above. This is suitable for fetching the
data direct from MariaDB and decoding in Python as opposed to with MariaDB's
``COLUMN_JSON`` function, preserving the types that JSON discards.

As noted above, ``DECIMAL`` values are not supported, and unpacking this
will raise ``DynColNotSupported``. Also strings will only be decoded with the
MySQL charsets ``utf8`` or ``utf8mb4``; strings with other charsets will raise
``DynColNotSupported`` as well.

Unsupported column formats, for example the old MariaDB numbered dynamic
columns format, or corrupt data, will raise ``DynColValueError``.

Examples:

.. code-block:: python

    >>> mariadb_dyncol.unpack(b'\x04\x01\x00\x01\x00\x00\x00\x03\x00a!\xf0\x9f\x92\xa9')
    {"a": "💩"}
    >>> mariadb_dyncol.unpack(b'\x04\x01\x00\x01\x00\x00\x00\x00\x00a\x02')
    {"a": 1}
