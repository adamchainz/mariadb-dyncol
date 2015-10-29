# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import binascii
from datetime import date, datetime, time

import MySQLdb
import six

from mariadb_dyncol import pack, unpack


hexs = binascii.hexlify
unhexs = binascii.unhexlify


def check(dicty, hexstring, expected=None, hexstring_cut=False):
    byte_string = pack(dicty)
    assert isinstance(byte_string, six.binary_type)
    hexed = hexs(byte_string)
    if hexstring_cut:
        hexed = hexed[:len(hexstring)]
    assert hexed == hexstring

    # Verify against MariaDB
    check_against_db(dicty, byte_string)

    unpacked = unpack(byte_string)
    # Nones are not stored and thus we shouldn't compare them
    if expected is None:
        expected = {k: v for k, v in dicty.items() if v is not None}
    assert unpacked == expected


connection = None


def get_connection():
    global connection
    if connection is None:
        connection = MySQLdb.connect(
            host='localhost',
            charset='utf8',
        )
        cursor = connection.cursor()
        try:
            cursor.execute("SET GLOBAL max_allowed_packet = 1048576000")
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
