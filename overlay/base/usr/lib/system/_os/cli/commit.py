import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..ostree import commit
from ..system import is_root


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--branch", default="system")
    _ = parser.add_argument("rootfs")


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    commit(cast(str, args.branch), cast(str, args.rootfs))


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
