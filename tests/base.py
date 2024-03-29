from __future__ import annotations

import binascii
import os
from datetime import date
from datetime import datetime
from datetime import time
from typing import Any

import pymysql

from mariadb_dyncol import pack
from mariadb_dyncol import unpack

hexs = binascii.hexlify
unhexs = binascii.unhexlify


def check(
    input: dict[str, Any],
    expected: bytes | None = None,
    expected_prefix: bytes | None = None,
) -> None:
    if expected is not None:
        assert expected_prefix is None

    packed = pack(input)
    assert isinstance(packed, bytes)

    packed_hex = hexs(packed)
    if expected is not None:
        assert packed_hex == expected
    elif expected_prefix is not None:
        packed_hex_prefix = packed_hex[: len(expected_prefix)]
        assert packed_hex_prefix == expected_prefix

    check_against_db(input, packed)

    unpacked = unpack(packed)

    # Nones are not stored and thus we shouldn't compare them
    expected_unpacked = {k: v for k, v in input.items() if v is not None}
    assert unpacked == expected_unpacked


connection = None


def get_connection() -> Any:
    global connection
    if connection is None:
        connection = pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            password=os.environ["MYSQL_PASSWORD"],
            charset="utf8mb4",
        )
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT VERSION()")
            row = cursor.fetchone()
            assert row is not None
            version = row[0]
        finally:
            cursor.close()
        assert "MariaDB" in version
    return connection


def check_against_db(dicty: dict[str, Any], byte_string: bytes) -> None:
    connection = get_connection()
    cursor = connection.cursor()
    try:
        # Basic validity check
        cursor.execute("SELECT COLUMN_CHECK(%s) AS r", (byte_string,))
        result = cursor.fetchone()[0]
        assert result == 1, f"MariaDB did not validate {hexs(byte_string)!r}"
        # In depth check of re-creating with COLUMN_CREATE
        sql, params = column_create(dicty)
        sql = "SELECT " + sql + " AS v"
        cursor.execute(sql, params)
        result = cursor.fetchone()[0]
        assert hexs(byte_string) == hexs(result)
    finally:
        cursor.close()


def column_create(dicty: dict[str, Any]) -> tuple[str, list[Any]]:
    # COLUMN_CREATE() with no args is invalid so hardcode empty dict
    if not dicty:
        return "COLUMN_DELETE(COLUMN_CREATE('a', 1), 'a')", []

    sql = []
    params: list[Any] = []
    for key, value in dicty.items():
        sql.append("%s")
        params.append(key)
        if isinstance(value, dict):
            subsql, subparams = column_create(value)
            sql.append(subsql)
            params.extend(subparams)
        elif value is None:
            sql.append("NULL")
        elif isinstance(value, (int, str)):
            sql.append("%s")
            params.append(value)
        elif isinstance(value, float):
            # str(float) breaks the query, instead use repr direct as SQL
            sql.append(repr(value) + " AS DOUBLE")
        else:
            sql.append("%s AS " + type_map[type(value)])
            params.append(value)

    return "COLUMN_CREATE(" + ", ".join(sql) + ")", params


type_map = {date: "DATE", datetime: "DATETIME", time: "TIME"}
