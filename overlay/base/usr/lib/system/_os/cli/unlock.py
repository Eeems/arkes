import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..ostree import update_grub_config
from ..system import (
    execute,
    is_root,
)

kwds = {"help": "Make the current deploy mutable"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--hotfix",
        action="store_true",
        help="Retain changes accross reboots",
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    argv: list[str] = []
    hotfix = cast(bool, args.hotfix)
    if hotfix:
        argv.append("--hotfix")

    execute("ostree", "admin", "unlock", *argv)
    if hotfix:
        update_grub_config()


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
