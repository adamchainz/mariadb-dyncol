#!/usr/bin/env python
import io
import sys
import time
from contextlib import contextmanager

from tests import base, test_mariadb_dyncol


def main():
    nruns = 1000
    base.check_against_db = lambda *a, **kw: 0

    test_funcs = get_test_funcs()
    print("Running benchmark", file=sys.stderr)
    start = time.time()
    for _ in range(nruns):
        print(".", file=sys.stderr, end="")
        sys.stderr.flush()
        [test_func() for test_func in test_funcs]
    total = time.time() - start
    print("\n", file=sys.stderr)
    print(
        "Ran all tests {} times in {} seconds = {} seconds per run".format(
            nruns, total, total / nruns
        ),
        file=sys.stderr,
    )


def get_test_funcs():
    funcs = []
    for name in dir(test_mariadb_dyncol):
        if not name.startswith("test_"):
            continue

        testfunc = getattr(test_mariadb_dyncol, name)
        if hasattr(testfunc, "slow"):
            continue

        if hasattr(testfunc, "skipif") and testfunc.skipif.args[0]:
            continue

        funcs.append(testfunc)
    return funcs


@contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO.

    Note: This function and the following ``captured_std*`` are copied
          from CPython's ``test.support`` module."""
    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, io.StringIO())
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


def captured_stdout():
    """Capture the output of sys.stdout:

    with captured_stdout() as stdout:
        print("hello")
    self.assertEqual(stdout.getvalue(), "hello\n")
    """
    return captured_output("stdout")


if __name__ == "__main__":
    main()
