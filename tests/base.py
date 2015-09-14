# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import unittest

import six

from mariadb_dyncol import pack


def hexs(byte_string):
    if six.PY3:
        def conv(x):
            return x
    else:
        conv = ord
    return ''.join(("%02X" % conv(x) for x in byte_string)).encode('utf-8')


class DyncolTestCase(unittest.TestCase):
    def assert_hex(self, dicty, hexstring):
        created = pack(dicty)
        assert isinstance(created, six.binary_type)
        assert hexs(created) == hexstring
