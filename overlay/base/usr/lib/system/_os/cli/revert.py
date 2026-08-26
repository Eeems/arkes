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

kwds = {"help": "Revert the last system upgrade"}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    sys.exit(execute("os undeploy 0", check=False))


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
