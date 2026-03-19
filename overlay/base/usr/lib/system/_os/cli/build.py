import sys

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from ..dbus import build
from ..console import print_stderr
from .upgrade import ProgressState
from .upgrade import noop


kwds = {"help": "Build your system image"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--no-progress",
        help="Disable progress bar",
        action="store_true",
        dest="noProgress",
    )
    _ = parser.add_argument(
        "--quiet",
        help="Disable status output",
        action="store_true",
    )


def command(args: Namespace) -> None:
    quiet = cast(bool, args.quiet)
    if cast(bool, args.noProgress) or not sys.stdin.isatty():
        build(
            onstdout=noop if quiet else lambda x: print(x, end=""),
            onstderr=noop if quiet else lambda x: print_stderr(x, end=""),
        )
        return

    state = ProgressState(quiet)
    assert state.quiet == quiet
    try:
        build(
            onprogress=state.update,
            onstdout=state.stdout,
            onstderr=state.stderr,
        )

    finally:
        state.bar.finish()


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
