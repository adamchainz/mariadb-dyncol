.. :changelog:

History
-------

Pending release
---------------

* New release notes go here

1.2.0 (2016-05-24)
------------------

* Disallowed ``str`` values on Python 2 - always use ``unicode``
* Added a benchmark script and made some optimizations that add up to a speed
  boost of about 10%.

1.1.0 (2015-10-13)
------------------

* Tests now verify every operation against MariaDB's ``COLUMN_CHECK`` and
  ``COLUMN_CREATE`` functions
* Fixed column order when >1 UTF8 byte characters are involved
* Fix encoding ``int``\s around size boundaries
* Fix encoding ``time``\s and ``datetime``\s with microseconds=0
* Fix encoding float ``-0.0``
* Fix a data size boundaries off-by-one error
* Fix decoding ``utf8mb4`` strings

1.0.0 (2015-10-09)
------------------

* Support to pack and unpack the named dynamic columns format. No support for
  DECIMAL values or strings with a non utf8mb4 charset.
