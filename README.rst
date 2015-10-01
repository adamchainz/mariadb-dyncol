==============
mariadb-dyncol
==============

.. image:: https://img.shields.io/pypi/v/mariadb-dyncol.svg
    :target: https://pypi.python.org/pypi/mariadb-dyncol

.. image:: https://travis-ci.org/adamchainz/mariadb-dyncol.png?branch=master
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

* Sensible type mapping
* Tested against binary data from MariaDB server and its test suite
* Python 2.7 and 3 compatible
* Fuzz tested with `hypothesis <http://hypothesis.readthedocs.org/en/latest/>`_

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

* ``int`` between ``-(2 ** 32) + 1`` and ``(2 ** 64) - 1``
* ``str`` up to 4GB
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
    b"0401000100000000006102"
    >>> mariadb_dyncol.pack({"a": "💩"})
    b"0401000100000003006121F09F92A9"

``unpack(bytestring)``
----------------------

Unpacks MariaDB dynamic columns data encoded byte string into a dict; the types
you can expect back are those listed above. This is suitable for fetching the
data direct from MariaDB and decoding in Python as opposed to with MariaDB's
``COLUMN_JSON`` function, preserving the types that JSON discards.

As noted above, ``DECIMAL`` values are not supported, and unpacking this
will raise ``DynColNotSupported``. Also strings will only be decoded with the
MySQL charset ``utf8mb4`` which corresponds to the full UTF-8 spec, and such
strings will raise ``DynColNotSupported`` as well.

Unsupported column formats, for example the old MariaDB numbered dynamic
columns format, or corrupt data, will raise ``DynColValueError``.

Examples:

.. code-block:: python

    >>> mariadb_dyncol.unpack(b"0401000100000003006121F09F92A9")
    {"a": "💩"}
    >>> mariadb_dyncol.unpack(b"0401000100000000006102")
    {"a": 1}
