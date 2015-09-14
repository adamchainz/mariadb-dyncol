# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import unittest

import six

from mariadb_dyncol import pack, unpack


def hexs(byte_string):
    if six.PY3:
        def conv(x):
            return x
    else:
        conv = ord
    return ''.join(("%02X" % conv(x) for x in byte_string)).encode('utf-8')


class DyncolTestCase(unittest.TestCase):
    def assert_hex(self, dicty, hexstring):
        byte_string = pack(dicty)
        assert isinstance(byte_string, six.binary_type)
        assert hexs(byte_string) == hexstring

        unpacked = unpack(byte_string)
        assert unpacked == dicty
