# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import codecs

import six

from mariadb_dyncol import pack, unpack


def hexs(byte_string):
    if six.PY3:
        def conv(x):
            return x
    else:
        conv = ord
    return ''.join(("%02X" % conv(x) for x in byte_string)).encode('utf-8')


def unhexs(hexs_string):
    return codecs.decode(hexs_string, 'hex')


def check(dicty, hexstring, expected=None, hexstring_cut=False):
    byte_string = pack(dicty)
    assert isinstance(byte_string, six.binary_type)
    hexed = hexs(byte_string)
    if hexstring_cut:
        hexed = hexed[:len(hexstring)]
    assert hexed == hexstring

    unpacked = unpack(byte_string)
    # Nones are not stored and thus we shouldn't compare them
    if expected is None:
        expected = {k: v for k, v in dicty.items() if v is not None}
    assert unpacked == expected
