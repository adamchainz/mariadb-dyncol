# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import binascii
from datetime import date, datetime, time

import pymysql
import six

from mariadb_dyncol import pack, unpack

hexs = binascii.hexlify
unhexs = binascii.unhexlify


def check(input, expected=None, expected_prefix=None):
    if expected is not None:
        assert expected_prefix is None

    packed = pack(input)
    assert isinstance(packed, six.binary_type)

    packed_hex = hexs(packed)
    if expected is not None:
        assert packed_hex == expected
    elif expected_prefix is not None:
        packed_hex_prefix = packed_hex[:len(expected_prefix)]
        assert packed_hex_prefix == expected_prefix

    check_against_db(input, packed)

    unpacked = unpack(packed)

    # Nones are not stored and thus we shouldn't compare them
    expected_unpacked = {k: v for k, v in input.items() if v is not None}
    assert unpacked == expected_unpacked


connection = None


def get_connection():
    global connection
    if connection is None:
        connection = pymysql.connect(
            host='localhost',
            charset='utf8mb4',
        )
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        finally:
            cursor.close()
        assert 'MariaDB' in version
    return connection


def check_against_db(dicty, byte_string):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        # Basic validity check
        cursor.execute("SELECT COLUMN_CHECK(%s) AS r", (byte_string,))
        result = cursor.fetchone()[0]
        assert result == 1, (
            "MariaDB did not validate %s" % hexs(byte_string)
        )
        # In depth check of re-creating with COLUMN_CREATE
        sql, params = column_create(dicty)
        sql = 'SELECT ' + sql + ' AS v'
        cursor.execute(sql, params)
        result = cursor.fetchone()[0]
        assert hexs(byte_string) == hexs(result)
    finally:
        cursor.close()


def column_create(dicty):
    # COLUMN_CREATE() with no args is invalid so hardcode empty dict
    if not dicty:
        return "COLUMN_DELETE(COLUMN_CREATE('a', 1), 'a')", []

    sql = []
    params = []
    for key, value in six.iteritems(dicty):
        sql.append('%s')
        params.append(key)
        if isinstance(value, dict):
            subsql, subparams = column_create(value)
            sql.append(subsql)
            params.extend(subparams)
        elif value is None:
            sql.append('NULL')
        elif isinstance(value, six.integer_types + six.string_types):
            sql.append('%s')
            params.append(value)
        elif isinstance(value, float):
            # str(float) broken on Python 2, breaks the query
            sql.append(repr(value) + ' AS DOUBLE')
        else:
            sql.append('%s AS ' + type_map[type(value)])
            params.append(value)

    sql = 'COLUMN_CREATE(' + ', '.join(sql) + ')'
    return sql, params


type_map = {
    date: 'DATE',
    datetime: 'DATETIME',
    time: 'TIME',
}
