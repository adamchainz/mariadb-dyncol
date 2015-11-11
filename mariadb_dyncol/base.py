# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time
from decimal import Decimal
from math import isinf, isnan
from struct import pack as struct_pack
from struct import unpack as struct_unpack
from struct import unpack_from as struct_unpack_from

from six import iteritems as six_iteritems
from six import iterkeys as six_iterkeys
from six import PY2, text_type
from six.moves import range as six_moves_range

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

    dicty_names_encoded = {
        key.encode('utf-8'): value
        for key, value in six_iteritems(dicty)
    }

    for encname in sorted(six_iterkeys(dicty_names_encoded), key=name_order):
        value = dicty_names_encoded[encname]
        if value is None:
            continue

        if len(encname) > MAX_NAME_LENGTH:
            raise DynColLimitError("Key too long: " + encname.decode('utf-8'))
        total_encname_length += len(encname)
        if total_encname_length > MAX_TOTAL_NAME_LENGTH:
            raise DynColLimitError("Total length of keys too long")

        try:
            encode_func = ENCODE_FUNCS[type(value)]
        except KeyError:
            raise DynColTypeError("Unencodable type {}".format(type(value)))
        dtype, encvalue = encode_func(value)

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
        struct_pack(
            '<BHH',
            flags,
            column_count,
            len(enc_names)
        ),
    ]
    if not odd_sized_datacode:
        buf.append(
            struct_pack(
                '<' + ('H' + coldir_size_code) * (len(column_directory) // 2),
                *column_directory
            )
        )
    else:
        for i, val in enumerate(column_directory):
            if i % 2 == 0:
                # name_offset
                buf.append(struct_pack('<H', val))
            else:
                # data_offset + dtype, have to cut last byte
                val = struct_pack('<' + coldir_size_code, val)
                buf.append(val[:-1])
    buf.append(enc_names)
    buf.extend(data)
    return b''.join(buf)


def name_order(name):
    # Keys are ordered by name length then name
    return len(name), name


def data_size(data):
    data_len = sum(len(d) for d in data)
    if data_len < 0xfff:
        return 0, 'H', False
    elif data_len < 0xfffff:
        return 1, 'L', True
    elif data_len < 0xfffffff:
        return 2, 'L', False
    else:
        raise ValueError("Too much data")


def encode_int(value):
    if value < 0:
        dtype = DYN_COL_INT
        encvalue = -(value << 1) - 1
        if value < -(2 ** 32 - 1):
            raise DynColValueError("int {} out of range".format(value))
    else:
        if value <= (2 ** 63 - 1):
            dtype = DYN_COL_INT
            encvalue = value << 1
        elif value <= (2 ** 64 - 1):
            dtype = DYN_COL_UINT
            encvalue = value
        else:
            raise DynColValueError("int {} out of range".format(value))

    to_enc = []
    while encvalue:
        to_enc.append(encvalue & 0xff)
        encvalue = encvalue >> 8
    return dtype, struct_pack('B' * len(to_enc), *to_enc)


def encode_float(value):
    if isnan(value) or isinf(value):
        raise DynColValueError("Float value not encodeable: {}".format(value))
    encvalue = struct_pack('d', value)

    # -0.0 is not supported in SQL, change to 0.0
    if encvalue == b'\x00\x00\x00\x00\x00\x00\x00\x80':
        encvalue = b'\x00\x00\x00\x00\x00\x00\x00\x00'

    return DYN_COL_DOUBLE, encvalue


def encode_string(value):
    return DYN_COL_STRING, b'\x21' + value.encode('utf-8')
    # 0x21 = utf8 charset number
    # N.B. not using utf8mb4 as it appears there is a bug with emoticons being
    # backed as question marks, e.g.
    # > select column_json(column_create('💩', 1)) as r\G
    # *************************** 1. row ***************************
    # r: {"?":1}


def encode_decimal(value):
    raise DynColNotSupported("Can't encode Decimal values currently")


# def encode_decimal(value):
#     buf = bytearray()
#     intg = int(value)
#     intg_digits = 9
#     buf.extend(struct_pack('>I', intg))

#     frac = value - intg
#     if frac:
#         frac_digits = 1
#         frac_piece = int(str(frac)[2:])  # ugh
#         buf.extend(struct_pack('B', frac_piece))
#     else:
#         frac_digits = 0

#     header = struct_pack('>BB', intg_digits, frac_digits)
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
    return DYN_COL_DATE, struct_pack('I', val)[:-1]


def encode_time(value):
    if value.microsecond > 0:
        val = (
            value.microsecond |
            value.second << 20 |
            value.minute << 26 |
            value.hour << 32
        )
        return DYN_COL_TIME, struct_pack('Q', val)[:6]
    else:
        val = (
            value.second |
            value.minute << 6 |
            value.hour << 12
        )
        return DYN_COL_TIME, struct_pack('I', val)[:3]


def encode_dict(value):
    return DYN_COL_DYNCOL, pack(value)


ENCODE_FUNCS = {
    int: encode_int,
    date: encode_date,
    datetime: encode_datetime,
    time: encode_time,
    float: encode_float,
    text_type: encode_string,
    Decimal: encode_decimal,
    dict: encode_dict,
}

if PY2:
    from __builtin__ import long  # Avoid python 3 lint error
    ENCODE_FUNCS[long] = encode_int


def unpack(buf):
    """
    Convert MariaDB dynamic columns data in a byte string into a dict
    """
    flags, column_count, len_names = struct_unpack_from('<BHH', buf)
    data_offset_code, coldata_size, data_offset_mask = decode_data_size(flags)
    if (flags & 0xFC) != 4:
        raise DynColValueError("Unknown dynamic columns format")

    if column_count == 0:
        return {}

    column_directory_end = (1 + 2 + 2) + coldata_size * column_count
    names_end = column_directory_end + len_names

    column_directory = buf[(1 + 2 + 2):column_directory_end]
    enc_names = buf[column_directory_end:names_end]
    data = buf[names_end:]

    names = {}
    values = {}

    last_name_offset = None
    last_data_offset = None
    last_dtype = None

    for i in six_moves_range(column_count):
        if coldata_size % 2 == 0:
            name_offset, data_offset_dtype = struct_unpack_from(
                '<H' + data_offset_code,
                column_directory,
                offset=i * coldata_size
            )
        else:
            name_offset, = struct_unpack_from(
                '<H',
                column_directory,
                offset=i * coldata_size
            )
            # can't struct_unpack the 3 bytes so hack around
            dodt_bytes = column_directory[(i * coldata_size + 2):
                                          (i * coldata_size + 5)] + b'\x00'
            data_offset_dtype, = struct_unpack('<' + data_offset_code,
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
        for i in six_moves_range(column_count)
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
    try:
        decode_func = DECODE_FUNCS[dtype]
    except KeyError:
        raise ValueError()
    return decode_func(encvalue)


def decode_int(encvalue):
    value = 0
    for i, b in enumerate(bytearray(encvalue)):
        value += b << (8 * i)
    if value & 1:
        return -(value >> 1) - 1
    else:
        return (value >> 1)


def decode_uint(encvalue):
    value, = struct_unpack('Q', encvalue)
    return value


def decode_double(encvalue):
    value, = struct_unpack('d', encvalue)
    return value


def decode_string(encvalue):
    if not encvalue.startswith((b'\x21', b'\x2D')):
        raise DynColNotSupported(
            "Can only decode strings with MySQL charsets utf8 or utf8mb4"
        )
    return encvalue[1:].decode('utf-8')


def decode_decimal(encvalue):
    raise DynColNotSupported("Can't decode Decimal values currently")


# def decode_decimal(encvalue):
#     num_intg, num_frac = struct_unpack('>BB', encvalue[:2])
#     intg, = struct_unpack('>I', encvalue[2:6])
#     intg ^= 0x80000000
#     if num_frac == 0:
#         frac = 0
#     else:
#         frac, = struct_unpack('>B', encvalue[6:])
#     return Decimal(str(intg) + '.' + str(frac))


def decode_datetime(encvalue):
    d = decode_date(encvalue[:3])
    t = decode_time(encvalue[3:])
    return datetime.combine(d, t)


def decode_date(encvalue):
    val, = struct_unpack('I', encvalue + b'\x00')
    return date(
        day=val & 0x1F,
        month=(val >> 5) & 0xF,
        year=(val >> 9)
    )


def decode_time(encvalue):
    if len(encvalue) == 6:
        val, = struct_unpack('Q', encvalue + b'\x00\x00')
        return time(
            microsecond=val & 0xFFFFF,
            second=(val >> 20) & 0x3F,
            minute=(val >> 26) & 0x3F,
            hour=(val >> 32)
        )
    else:  # must be 3
        val, = struct_unpack('I', encvalue + b'\x00')
        return time(
            microsecond=0,
            second=(val) & 0x3F,
            minute=(val >> 6) & 0x3F,
            hour=(val >> 12)
        )

DECODE_FUNCS = {
    DYN_COL_INT: decode_int,
    DYN_COL_UINT: decode_uint,
    DYN_COL_DOUBLE: decode_double,
    DYN_COL_STRING: decode_string,
    DYN_COL_DECIMAL: decode_decimal,
    DYN_COL_DATETIME: decode_datetime,
    DYN_COL_DATE: decode_date,
    DYN_COL_TIME: decode_time,
    DYN_COL_DYNCOL: unpack,
}
