# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time
from decimal import Decimal

import struct

import six

DYN_COL_INT = 0
DYN_COL_UINT = 1
DYN_COL_DOUBLE = 2
DYN_COL_STRING = 3
DYN_COL_DECIMAL = 4
DYN_COL_DATETIME = 5
DYN_COL_DATE = 6
DYN_COL_TIME = 7
DYN_COL_DYNCOL = 8


def column_create(dicty):
    buf = []

    flags = struct.pack('B', 4)
    buf.append(flags)

    column_count = 0
    column_directory = []
    directory_offset = 0
    name_offset = 0
    names = []
    data_offset = 0
    data = []
    for name, value in sorted(six.iteritems(dicty)):
        if value is None:
            continue

        encname = name.encode('utf-8')
        if isinstance(value, six.integer_types):
            dtype, encvalue = encode_int(value)
        elif isinstance(value, float):
            dtype, encvalue = encode_float(value)
        elif isinstance(value, six.string_types):
            dtype, encvalue = encode_string(value)
        elif isinstance(value, datetime):
            dtype, encvalue = encode_datetime(value)
        elif isinstance(value, Decimal):
            raise ValueError("Decimal objects are not currently supported")
        elif isinstance(value, date):
            dtype, encvalue = encode_date(value)
        elif isinstance(value, time):
            dtype, encvalue = encode_time(value)
        elif isinstance(value, dict):
            dtype = DYN_COL_DYNCOL
            encvalue = column_create(value)
        else:
            raise TypeError("Unencodable type {}".format(type(value)))

        column_count += 1
        column_directory.append(struct.pack('H', name_offset))
        column_directory.append(struct.pack('H', (data_offset << 4) + dtype))
        names.append(encname)
        name_offset += len(encname)
        data.append(encvalue)
        data_offset += len(encvalue)

        directory_offset += 2

    buf.append(struct.pack('H', column_count))
    enc_names = b''.join(names)
    buf.append(struct.pack('H', len(enc_names)))
    buf.append(b''.join(column_directory))
    buf.append(enc_names)
    buf.append(b''.join(data))

    return b''.join(buf)


def encode_int(value):
    """
    Stored in the schema:
    0: no data
    -1: 1
     1: 2
    -2: 3
     2: 4
    ...
    """
    dtype = DYN_COL_INT
    if value == 0:
        encoded = b''
    else:
        encoded = 2 * value
        if value < 0:
            encoded = -1 * encoded - 1

        cut_last_byte = False
        if encoded <= (2 ** 8 - 1):
            code = 'B'
        elif encoded <= (2 ** 16 - 1):
            code = 'H'
        elif encoded <= (2 ** 24 - 1):
            # Want 3 bytes but only 4 bytes possible with struct
            code = 'I'
            cut_last_byte = True
        elif encoded <= (2 ** 32 - 1):
            code = 'I'
        elif value <= (2 ** 64 - 1) and value > 0:
            dtype = DYN_COL_UINT
            code = 'Q'
            encoded = value
        else:
            raise OverflowError("int {} too large".format(value))

        encoded = struct.pack(code, encoded)
        if cut_last_byte:
            encoded = encoded[:-1]
    return dtype, encoded


def encode_float(value):
    return DYN_COL_DOUBLE, struct.pack('d', value)


def encode_string(value):
    encoded = value.encode('utf-8')
    return DYN_COL_STRING, b'\x21' + encoded  # 0x21 = utf8mb4 charset number


def encode_datetime(value):
    _, enc_date = encode_date(value)
    _, enc_time = encode_time(value)
    return DYN_COL_DATETIME, enc_date + enc_time


def encode_date(value):
    val = value.day | value.month << 5 | value.year << 9
    return DYN_COL_DATE, struct.pack('I', val)[:-1]


def encode_time(value):
    val = (
        value.microsecond |
        value.second << 20 |
        value.minute << 26 |
        value.hour << 32
    )
    return DYN_COL_TIME, struct.pack('Q', val)[:6]
