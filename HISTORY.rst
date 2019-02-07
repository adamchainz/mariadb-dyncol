.. :changelog:

History
-------

Pending release
---------------

.. Insert new release notes below this line

3.0.0 (2019-02-07)
------------------

* Drop Python 2 support, only Python 3.4+ is supported now.

2.0.0 (2018-10-20)
------------------

* Use ``utf8mb4`` character set for encoding strings. This seemed to be broken
  for emoji on older versions of MariaDB (10.1 or 10.2?), so ``utf8`` was
  previously used, however this may have only been a display/``COLUMN_JSON``
  issue on such older versions. MariaDB internally now defaults to ``utf8mb44``
  for dynamic column strings. Since this changes the output of serialization
  slightly, please test before upgrading. Also you probably want to use
  ``utf8mb4`` for everything else MariaDB in your application if you aren't
  already - it is the default on MySQL 8+.

1.2.1 (2017-12-05)
------------------

* Fix a packaging error which caused the tests to be installed alongside the
  package.
* Don't pin version of ``six`` to 1.9.0

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
