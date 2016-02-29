from copy import deepcopy
from math import isnan, isinf

from hypothesis import assume, given
from hypothesis.extra.datetime import datetimes
from hypothesis.strategies import (
    dictionaries, text, integers, floats, recursive
)

from mariadb_dyncol import DynColValueError, pack, unpack
from mariadb_dyncol.base import MAX_NAME_LENGTH, MAX_TOTAL_NAME_LENGTH  # priv.
from .base import check_against_db

valid_keys = text(
    min_size=1,
    average_size=10.0,
    max_size=MAX_NAME_LENGTH
).filter(
    lambda key: len(key.encode('utf-8')) <= MAX_NAME_LENGTH
)
valid_ints = integers(
    min_value=-(2 ** 31 - 1),
    max_value=(2 ** 64 - 1)
).filter(
    lambda i: abs(i) <= (2 ** 31 - 1) or 0 <= i <= 2 ** 64 - 1
)
valid_floats = floats().filter(
    lambda f: not isnan(f) and not isinf(f)
)
valid_datetimes = datetimes(timezones=[])
valid_dates = deepcopy(valid_datetimes).map(lambda dt: dt.date())
valid_times = deepcopy(valid_datetimes).map(lambda dt: dt.time())


def valid_dictionaries(keys, values):
    return dictionaries(keys, values, average_size=5).filter(
        lambda data: (
            sum(len(key.encode('utf-8')) for key in data) <=
            MAX_TOTAL_NAME_LENGTH
        ),
    )


def check_data(data):
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


recursive_values = recursive(
    (valid_ints | valid_floats | text() | valid_datetimes | valid_dates |
     valid_times),
    lambda children: valid_dictionaries(valid_keys, children)
)


@given(valid_dictionaries(valid_keys, recursive_values))
def test_recursively_defined(data):
    try:
        check_data(data)
    except DynColValueError:
        assume(False)
