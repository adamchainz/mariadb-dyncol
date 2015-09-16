# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from .base import DyncolTestCase


class PackTests(DyncolTestCase):
    def test_empty(self):
        self.assert_hex({}, b"0400000000")

    def test_a_1(self):
        self.assert_hex({"a": 1}, b"0401000100000000006102")

    def test_a_minus1(self):
        self.assert_hex({"a": -1}, b"0401000100000000006101")

    def test_a_minus2(self):
        self.assert_hex({"a": -2}, b"0401000100000000006103")

    def test_a_0(self):
        self.assert_hex({"a": 0}, b"04010001000000000061")

    def test_a_128(self):
        self.assert_hex({"a": 128}, b"040100010000000000610001")

    def test_a_65535(self):
        self.assert_hex({"a": 65535}, b"04010001000000000061FEFF01")

    def test_a_1048576(self):
        self.assert_hex({"a": 1048576}, b"04010001000000000061000020")

    def test_ulonglongmax(self):
        self.assert_hex(
            {"a": 18446744073709551615},
            b"04010001000000010061FFFFFFFFFFFFFFFF"
        )

    def test_integer_overflow(self):
        with pytest.raises(OverflowError):
            self.assert_hex({"a": 2 ** 64}, b"unchecked")

    def test_integer_negative_overflow(self):
        with pytest.raises(OverflowError):
            self.assert_hex({"a": -(2 ** 32)}, b"unchecked")

    def test_c_1(self):
        self.assert_hex({"c": 1}, b"0401000100000000006302")

    def test_a_1_b_2(self):
        self.assert_hex(
            {"a": 1, "b": 2},
            b"0402000200000000000100100061620204"
        )

    def test_a_1_b_2_c_3(self):
        self.assert_hex(
            {"a": 1, "b": 2, "c": 3},
            b"0403000300000000000100100002002000616263020406"
        )

    def test_abc_123(self):
        self.assert_hex(
            {"abc": 123},
            b"040100030000000000616263F6"
        )

    def test_string_empty(self):
        self.assert_hex({"a": ""}, b"0401000100000003006121")

    def test_string_values(self):
        self.assert_hex({"a": "string"}, b"0401000100000003006121737472696E67")

    def test_a_unicode_poo(self):
        self.assert_hex({"a": "💩"}, b"0401000100000003006121F09F92A9")

    def test_None(self):
        self.assert_hex({"a": None}, b"0400000000")

    def test_dict(self):
        self.assert_hex(
            {"a": {"b": "c"}},
            b"04010001000000080061040100010000000300622163"
        )

    def test_float_1_0(self):
        self.assert_hex({"a": 1.0}, b"04010001000000020061000000000000F03F")

    def test_float_minus_3_415(self):
        self.assert_hex({"a": -3.415}, b"0401000100000002006152B81E85EB510BC0")

    def test_float_192873409809(self):
        self.assert_hex(
            {"a": 192873409809.0},
            b"040100010000000200610080885613744642"
        )

    def test_decimal_unsupported(self):
        with self.assertRaises(ValueError):
            self.assert_hex({"a": Decimal('1.3')}, b'unchecked')

    def test_datetime(self):
        self.assert_hex(
            {"a": datetime(year=1989, month=10, day=4,
                           hour=3, minute=4, second=55, microsecond=142859)},
            b"04010001000000050061448B0F0B2E72130300"
        )

    def test_datetime_2(self):
        self.assert_hex(
            {"a": datetime(year=2300, month=12, day=25,
                           hour=15, minute=55, second=12, microsecond=998134)},
            b"0401000100000005006199F911F63ACFDC0F00"
        )

    def test_date(self):
        self.assert_hex(
            {"a": date(year=2015, month=1, day=1)},
            b"0401000100000006006121BE0F"
        )

    def test_date_2(self):
        self.assert_hex(
            {"a": date(year=1, month=12, day=25)},
            b"04010001000000060061990300"
        )

    def test_time(self):
        self.assert_hex(
            {"a": time(hour=12, minute=2, second=3, microsecond=676767)},
            b"040100010000000700619F533A080C00"
        )

    def test_time_2(self):
        self.assert_hex(
            {"a": time(hour=3, minute=59, second=59, microsecond=999999)},
            b"040100010000000700613F42BFEF0300"
        )
