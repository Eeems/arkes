import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..ostree import undeploy
from ..system import is_root

kwds = {"help": "Revert the last system upgrade"}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    undeploy(0)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
