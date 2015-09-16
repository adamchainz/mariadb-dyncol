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


def pack(dicty):
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
            encvalue = pack(value)
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

    flags = 4  # means this contains named dynamic columns
    enc_names = b''.join(names)

    buf = [
        struct.pack(
            '<BHH',
            flags,
            column_count,
            len(enc_names)
        ),
    ]
    buf.extend(column_directory)
    buf.append(enc_names)
    buf.extend(data)
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


def unpack(buf):
    flags, column_count, len_names = struct.unpack_from('<BHH', buf, offset=0)
    if flags != 4:
        raise ValueError("Unknown dynamic columns format")

    if column_count == 0:
        return {}

    header_end = 1 + 2 + 2
    column_directory_end = header_end + 4 * column_count
    names_end = column_directory_end + len_names

    column_directory = buf[header_end:column_directory_end]
    enc_names = buf[column_directory_end:names_end]
    data = buf[names_end:]

    names = {}
    values = {}

    last_name_offset = None
    last_data_offset = None
    last_dtype = None

    for i in range(column_count):
        name_offset, data_offset_dtype = struct.unpack_from(
            '<HH',
            column_directory,
            offset=i * 4
        )
        data_offset = data_offset_dtype >> 4
        dtype = data_offset_dtype & 0xF

        # Store *last* column's name
        if last_name_offset is not None:
            names[i - 1] = enc_names[last_name_offset:name_offset].decode('utf-8')
        last_name_offset = name_offset

        #
        if last_data_offset is not None:
            values[i - 1] = decode(last_dtype, data[last_data_offset:data_offset])
        last_data_offset = data_offset
        last_dtype = dtype

    names[column_count - 1] = enc_names[last_name_offset:].decode('utf-8')
    values[column_count - 1] = decode(last_dtype, data[last_data_offset:])

    # join data and names
    return {
        names[i]: values[i]
        for i in range(column_count)
    }


def decode(dtype, encvalue):
    if dtype == DYN_COL_INT:
        return decode_int(encvalue)
    elif dtype == DYN_COL_UINT:
        return decode_uint(encvalue)
    elif dtype == DYN_COL_DOUBLE:
        return decode_double(encvalue)
    elif dtype == DYN_COL_STRING:
        return decode_string(encvalue)
    elif dtype == DYN_COL_DATETIME:
        return decode_datetime(encvalue)
    elif dtype == DYN_COL_DATE:
        return decode_date(encvalue)
    elif dtype == DYN_COL_TIME:
        return decode_time(encvalue)
    elif dtype == DYN_COL_DYNCOL:
        return unpack(encvalue)
    else:
        raise ValueError()


def decode_int(encvalue):
    if len(encvalue) == 0:
        return 0
    elif len(encvalue) == 1:
        code = 'B'
    elif len(encvalue) == 2:
        code = 'H'
    elif len(encvalue) == 3:
        code = 'I'
        encvalue += b'\x00'
    elif len(encvalue) == 4:
        code = 'I'
    else:
        raise ValueError()

    dvalue, = struct.unpack(code, encvalue)

    value = dvalue >> 1
    if dvalue & 1:
        value = -1 * value - 1
    return value


def decode_uint(encvalue):
    value, = struct.unpack('Q', encvalue)
    return value


def decode_double(encvalue):
    value, = struct.unpack('d', encvalue)
    return value


def decode_string(encvalue):
    if not encvalue.startswith(b'\x21'):
        raise ValueError("Can only decode strings with MySQL charset utf8mb4")
    return encvalue[1:].decode('utf-8')


def decode_datetime(encvalue):
    d = decode_date(encvalue[:3])
    t = decode_time(encvalue[3:])
    return datetime.combine(d, t)


def decode_date(encvalue):
    val, = struct.unpack('I', encvalue + b'\x00')
    return date(
        day=val & 0x1F,
        month=(val >> 5) & 0xF,
        year=(val >> 9)
    )


def decode_time(encvalue):
    val, = struct.unpack('Q', encvalue + b'\x00\x00')
    return time(
        microsecond=val & 0xFFFFF,
        second=(val >> 20) & 0x3F,
        minute=(val >> 26) & 0x3F,
        hour=(val >> 32)
    )
