import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..system import execute

kwds: dict[str, str] = {}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )


def command(args: Namespace) -> None:
    verbose: bool = cast(bool, args.verbose)
    run_parts_args: list[str] = ["--report"]
    if verbose:
        run_parts_args.append("--verbose")

    try:
        execute("run-parts", *run_parts_args, "/usr/lib/system/validate.d")

    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
