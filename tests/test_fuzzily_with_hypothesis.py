from __future__ import annotations

from math import isinf
from math import isnan
from typing import Any

from hypothesis import assume
from hypothesis import given
from hypothesis.strategies import dates
from hypothesis.strategies import datetimes
from hypothesis.strategies import dictionaries
from hypothesis.strategies import floats
from hypothesis.strategies import integers
from hypothesis.strategies import recursive
from hypothesis.strategies import text
from hypothesis.strategies import times

from .base import check_against_db
from mariadb_dyncol import DynColValueError
from mariadb_dyncol import pack
from mariadb_dyncol import unpack
from mariadb_dyncol.base import MAX_NAME_LENGTH
from mariadb_dyncol.base import MAX_TOTAL_NAME_LENGTH

valid_keys = text(min_size=1, max_size=MAX_NAME_LENGTH).filter(
    lambda key: len(key.encode("utf-8")) <= MAX_NAME_LENGTH
)
valid_ints = integers(min_value=-(2**31 - 1), max_value=(2**64 - 1)).filter(
    lambda i: abs(i) <= (2**31 - 1) or 0 <= i <= 2**64 - 1
)
valid_floats = floats().filter(lambda f: not isnan(f) and not isinf(f))
valid_datetimes = datetimes()
valid_dates = dates()
valid_times = times()


def valid_dictionaries(keys: Any, values: Any) -> Any:
    return dictionaries(keys, values).filter(
        lambda data: (
            sum(len(key.encode("utf-8")) for key in data) <= MAX_TOTAL_NAME_LENGTH
        )
    )


def check_data(data: dict[str, Any]) -> None:
    packed = pack(data)
    check_against_db(data, packed)
    assert unpack(packed) == data


@given(valid_dictionaries(valid_keys, valid_ints))
def test_ints(data):
    check_data(data)


@given(valid_dictionaries(valid_keys, valid_floats))
def test_floats(data):
    try:
        check_data(data)
    except DynColValueError:
        assume(False)


@given(valid_dictionaries(valid_keys, text()))
def test_strings(data):
    check_data(data)


@given(valid_dictionaries(valid_keys, valid_datetimes))
def test_datetimes(data):
    check_data(data)


@given(valid_dictionaries(valid_keys, valid_dates))
def test_dates(data):
    check_data(data)


@given(valid_dictionaries(valid_keys, valid_times))
def test_times(data):
    check_data(data)


def filter_recursive_values(children):
    return valid_dictionaries(valid_keys, children)


recursive_values = recursive(
    (valid_ints | valid_floats | text() | valid_datetimes | valid_dates | valid_times),
    filter_recursive_values,
)


@given(valid_dictionaries(valid_keys, recursive_values))
def test_recursively_defined(data):
    try:
        check_data(data)
    except DynColValueError:
        assume(False)
