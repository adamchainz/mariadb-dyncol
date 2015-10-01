# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time
from decimal import Decimal
from math import isinf, isnan

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

MAX_TOTAL_NAME_LENGTH = 65535
MAX_NAME_LENGTH = (MAX_TOTAL_NAME_LENGTH // 4)


class DynColLimitError(Exception):
    """
    Indicates that some limit has been reached
    """


class DynColTypeError(TypeError):
    """
    Indicates that a type is wrong
    """


class DynColValueError(ValueError):
    """
    Indicates that a value is wrong
    """


class DynColNotSupported(Exception):
    """
    Indicates a limitation in this implementation
    """


def pack(dicty):
    """
    Convert a mapping into the MariaDB dynamic columns format
    """
    column_count = 0
    column_directory = []
    directory_offset = 0
    name_offset = 0
    names = []
    data_offset = 0
    data = []
    total_encname_length = 0

    for name in sorted(six.iterkeys(dicty), key=name_order):
        value = dicty[name]
        if value is None:
            continue

        encname = name.encode('utf-8')
        if len(encname) > MAX_NAME_LENGTH:
            raise DynColLimitError("Key too long: " + name)
        total_encname_length += len(encname)
        if total_encname_length > MAX_TOTAL_NAME_LENGTH:
            raise DynColLimitError("Total length of keys too long")

        if isinstance(value, six.integer_types):
            dtype, encvalue = encode_int(value)
        elif isinstance(value, float):
            dtype, encvalue = encode_float(value)
        elif isinstance(value, six.string_types):
            dtype, encvalue = encode_string(value)
        elif isinstance(value, datetime):
            dtype, encvalue = encode_datetime(value)
        elif isinstance(value, Decimal):
            raise DynColNotSupported("Can't encode Decimal values currently")
            # dtype, encvalue = encode_decimal(value)
        elif isinstance(value, date):
            dtype, encvalue = encode_date(value)
        elif isinstance(value, time):
            dtype, encvalue = encode_time(value)
        elif isinstance(value, dict):
            dtype = DYN_COL_DYNCOL
            encvalue = pack(value)
        else:
            raise DynColTypeError("Unencodable type {}".format(type(value)))

        column_count += 1
        column_directory.append(name_offset)
        column_directory.append((data_offset << 4) + dtype)
        names.append(encname)
        name_offset += len(encname)
        data.append(encvalue)
        data_offset += len(encvalue)

        directory_offset += 2

    data_size_flag, coldir_size_code, odd_sized_datacode = data_size(data)

    flags = (
        4 |  # means this contains named dynamic columns
        data_size_flag
    )
    enc_names = b''.join(names)

    buf = [
        struct.pack(
            '<BHH',
            flags,
            column_count,
            len(enc_names)
        ),
    ]
    if not odd_sized_datacode:
        buf.append(
            struct.pack(
                '<' + ('H' + coldir_size_code) * (len(column_directory) // 2),
                *column_directory
            )
        )
    else:
        for i, val in enumerate(column_directory):
            if i % 2 == 0:
                # name_offset
                buf.append(struct.pack('<H', val))
            else:
                # data_offset + dtype, have to cut last byte
                val = struct.pack('<' + coldir_size_code, val)
                buf.append(val[:-1])
    buf.append(enc_names)
    buf.extend(data)
    return b''.join(buf)


def name_order(name):
    # Keys are ordered by name length then name
    return len(name), name


def data_size(data):
    data_len = sum(len(d) for d in data)
    if data_len <= 2 ** 12:
        return 0, 'H', False
    elif data_len < 2 ** 20:
        return 1, 'L', True
    elif data_len < 2 ** 28:
        return 2, 'L', False
    else:
        raise ValueError("Too much data")


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
            raise DynColValueError("int {} too large".format(value))

        encoded = struct.pack(code, encoded)
        if cut_last_byte:
            encoded = encoded[:-1]
    return dtype, encoded


def encode_float(value):
    if isnan(value) or isinf(value):
        raise DynColValueError("Float value not encodeable: {}".format(value))
    return DYN_COL_DOUBLE, struct.pack('d', value)


def encode_string(value):
    encoded = value.encode('utf-8')
    return DYN_COL_STRING, b'\x21' + encoded  # 0x21 = utf8mb4 charset number


# def encode_decimal(value):
#     buf = bytearray()
#     intg = int(value)
#     intg_digits = 9
#     buf.extend(struct.pack('>I', intg))

#     frac = value - intg
#     if frac:
#         frac_digits = 1
#         frac_piece = int(str(frac)[2:])  # ugh
#         buf.extend(struct.pack('B', frac_piece))
#     else:
#         frac_digits = 0

#     header = struct.pack('>BB', intg_digits, frac_digits)
#     buf[0] |= 0x80  # Flip the top bit
#     return DYN_COL_DECIMAL, header + bytes(buf)


def encode_datetime(value):
    _, enc_date = encode_date(value)
    _, enc_time = encode_time(value)
    return DYN_COL_DATETIME, enc_date + enc_time


def encode_date(value):
    # We don't need any validation since datetime.date is more limited than the
    # MySQL format
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
    """
    Convert MariaDB dynamic columns data in a byte string into a dict
    """
    flags, column_count, len_names = struct.unpack_from('<BHH', buf, offset=0)
    data_offset_code, coldata_size, data_offset_mask = decode_data_size(flags)
    if (flags & 0xFC) != 4:
        raise DynColValueError("Unknown dynamic columns format")

    if column_count == 0:
        return {}

    header_end = 1 + 2 + 2
    column_directory_end = header_end + coldata_size * column_count
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
        if coldata_size % 2 == 0:
            name_offset, data_offset_dtype = struct.unpack_from(
                '<H' + data_offset_code,
                column_directory,
                offset=i * coldata_size
            )
        else:
            name_offset, = struct.unpack_from(
                '<H',
                column_directory,
                offset=i * coldata_size
            )
            # can't struct.unpack the 3 bytes so hack around
            dodt_bytes = column_directory[(i * coldata_size + 2):
                                          (i * coldata_size + 5)] + b'\x00'
            data_offset_dtype, = struct.unpack('<' + data_offset_code,
                                               dodt_bytes)

        data_offset_dtype &= data_offset_mask
        data_offset = data_offset_dtype >> 4
        dtype = data_offset_dtype & 0xF

        # Store *last* column's name
        if last_name_offset is not None:
            names[i - 1] = (
                enc_names[last_name_offset:name_offset].decode('utf-8')
            )
        last_name_offset = name_offset

        #
        if last_data_offset is not None:
            values[i - 1] = decode(last_dtype,
                                   data[last_data_offset:data_offset])
        last_data_offset = data_offset
        last_dtype = dtype

    names[column_count - 1] = enc_names[last_name_offset:].decode('utf-8')
    values[column_count - 1] = decode(last_dtype, data[last_data_offset:])

    # join data and names
    return {
        names[i]: values[i]
        for i in range(column_count)
    }


def decode_data_size(flags):
    t = flags & 0x03
    if t == 0:
        return 'H', 4, 0xFFFF
    elif t == 1:
        return 'L', 5, 0xFFFFFF
    elif t == 2:
        return 'L', 6, 0xFFFFFFFF
    else:
        raise ValueError("Unknown dynamic columns format")


def decode(dtype, encvalue):
    if dtype == DYN_COL_INT:
        return decode_int(encvalue)
    elif dtype == DYN_COL_UINT:
        return decode_uint(encvalue)
    elif dtype == DYN_COL_DOUBLE:
        return decode_double(encvalue)
    elif dtype == DYN_COL_STRING:
        return decode_string(encvalue)
    elif dtype == DYN_COL_DECIMAL:
        raise DynColNotSupported("Can't decode Decimal values currently")
        # return decode_decimal(encvalue)
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
        raise DynColNotSupported(
            "Can only decode strings with MySQL charset utf8mb4"
        )
    return encvalue[1:].decode('utf-8')


# def decode_decimal(encvalue):
#     num_intg, num_frac = struct.unpack('>BB', encvalue[:2])
#     intg, = struct.unpack('>I', encvalue[2:6])
#     intg ^= 0x80000000
#     if num_frac == 0:
#         frac = 0
#     else:
#         frac, = struct.unpack('>B', encvalue[6:])
#     return Decimal(str(intg) + '.' + str(frac))


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
