# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from mariadb_dyncol import (
    DynColLimitError, DynColTypeError, DynColValueError, MAX_NAME_LENGTH, pack,
)
from .base import DyncolTestCase, hexs


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

    def test_empty_key(self):
        self.assert_hex({"": ""}, b"04010000000000030021")

    def test_string_values(self):
        self.assert_hex({"a": "string"}, b"0401000100000003006121737472696E67")

    def test_a_unicode_poo(self):
        self.assert_hex({"a": "💩"}, b"0401000100000003006121F09F92A9")

    def test_unicode_poo_1(self):
        self.assert_hex({"💩": 1}, b"040100040000000000F09F92A902")

    def test_large_string_data(self):
        self.assert_hex(
            {'a': 'a' * (2 ** 12)},
            b'050100010000000300006121616161',
            hexstring_cut=True
        )

    def test_large_string_data_2(self):
        self.assert_hex(
            {'a': 'a' * (2 ** 13), 'b': 1},
            b'0502000200000003000001001000026162216161',
            hexstring_cut=True
        )

    def test_huge_string_data(self):
        self.assert_hex(
            {'a': 'a' * (2 ** 20)},
            b'06010001000000030000006121616161',
            hexstring_cut=True
        )

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

    def test_float_nan_not_stored(self):
        with pytest.raises(DynColValueError):
            pack({"a": float('nan')})

    def test_float_inf_not_stored(self):
        with pytest.raises(DynColValueError):
            pack({"a": float('inf')})

    def test_decimal_1(self):
        self.assert_hex(
            {'a': Decimal('1')},
            b'04010001000000040061090080000001'
        )

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


class MariaDBTests(DyncolTestCase):
    def test_1(self):
        self.assert_hex(
            {'адын': 1212},
            b'040100080000000000D0B0D0B4D18BD0BD7809'
        )

    def test_2(self):
        self.assert_hex(
            {"1212": 1212},
            b'040100040000000000313231327809'
        )

    def test_4(self):
        self.assert_hex(
            {"1212": 2, "www": 3},
            b'04020007000000000003001000777777313231320604',
        )

    def test_5(self):
        self.assert_hex(
            {"1": "AAA", "b": "BBB"},
            b'0402000200000003000100430031622141414121424242',
        )

    def test_255_chars(self):
        self.assert_hex(
            {'a' * 255: 1},
            b'040100FF0000000000' + b''.join([b'61'] * 255) + b'02'
        )

    def test_MAX_NAME_LENGTH_chars(self):
        long_key = 'a' * MAX_NAME_LENGTH
        long_key_encoded = long_key.encode('utf-8')
        self.assert_hex(
            {long_key: 1},
            b'040100FF3F00000000' + hexs(long_key_encoded) + b'02'
        )

    def test_name_overflow(self):
        with pytest.raises(DynColLimitError):
            pack({'a' * (MAX_NAME_LENGTH + 1): 1})

    def test_name_unicode_fits(self):
        long_key = ('💩' * 4095) + ('a' * 3)  # MAX_NAME_LENGTH bytes
        long_key_encoded = long_key.encode('utf8')
        self.assert_hex(
            {long_key: 1},
            b'040100FF3F00000000' + hexs(long_key_encoded) + b'02'
        )

    def test_name_unicode_overflow(self):
        long_key = ('💩' * 4095) + ('a' * 4)
        with pytest.raises(DynColLimitError):
            pack({long_key: 1})

    def test_total_name_length(self):
        long_key = 'a' * (MAX_NAME_LENGTH - 1)
        # No exception
        pack({
            long_key + '1': 1,
            long_key + '2': 1,
            long_key + '3': 1,
            long_key + '4': 1,
            'abc': 1    # Total up to here = TOTAL_MAX_NAME_LENGTH
        })

    def test_total_name_length_overflow(self):
        long_key = 'a' * (MAX_NAME_LENGTH - 1)
        with pytest.raises(DynColLimitError):
            pack({
                long_key + '1': 1,
                long_key + '2': 1,
                long_key + '3': 1,
                long_key + '4': 1,
                'abc': 1,  # Total up to here = TOTAL_MAX_NAME_LENGTH
                'a': 1,
            })

    def test_8(self):
        self.assert_hex(
            {'falafel': {'a': 1}, 'fala': {'b': 't'}},
            b'0402000B00000008000400C80066616C6166616C6166656C040100010000000'
            b'3006221740401000100000000006102'
        )

    def test_unknown_type(self):
        with pytest.raises(DynColTypeError):
            pack({'key': ['lists', 'not', 'supported']})
