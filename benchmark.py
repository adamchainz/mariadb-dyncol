#!/usr/bin/env python
from __future__ import annotations

import io
import sys
import time
from contextlib import contextmanager
from typing import Any
from typing import Callable
from typing import ContextManager
from typing import Generator
from typing import IO

from tests import base
from tests import test_mariadb_dyncol


def main() -> None:
    nruns = 1000

    def check_against_db(*args: Any, **kwargs: Any) -> None:
        ...

    base.check_against_db = check_against_db

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


def get_test_funcs() -> list[Callable[[], None]]:
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
def captured_output(stream_name: str) -> Generator[IO[Any], None, None]:
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


def captured_stdout() -> ContextManager[IO[Any]]:
    """Capture the output of sys.stdout:

    with captured_stdout() as stdout:
        print("hello")
    self.assertEqual(stdout.getvalue(), "hello\n")
    """
    return captured_output("stdout")


if __name__ == "__main__":
    main()
