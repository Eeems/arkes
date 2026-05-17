import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..podman import build
from ..system import (
    is_root,
    system_kernelCommandLine,
)

kwds = {}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    build(buildArgs={"KARGS": system_kernelCommandLine()})


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
