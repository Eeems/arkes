import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..ostree import (
    undeploy,
    update_loader_entries,
)
from ..system import is_root

kwds = {"help": "Remove a deployment by index"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("index", type=int, help="Deployment index to remove")


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    undeploy(cast(int, args.index))
    update_loader_entries()


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
