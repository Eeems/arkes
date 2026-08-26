import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..ostree import (
    deploy,
    update_loader_entries,
)
from ..system import is_root


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--branch", default="system")
    _ = parser.add_argument("--sysroot", default="/")


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    sysroot = cast(str, args.sysroot)
    _ = deploy(cast(str, args.branch), sysroot)
    update_loader_entries(sysroot)


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
