import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..ostree import prune
from ..system import is_root

kwds = {"help": "Prune unused data from the ostree"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--branch", default="system", help="System branch to prune")


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    prune(cast(str, args.branch))


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
