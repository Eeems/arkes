import sys

from argparse import ArgumentParser
from argparse import Namespace
from typing import cast
from typing import Any

from ..system import is_root
from ..system import in_nspawn_system_cmd
from ..console import shell

kwds = {"help": "Open a console of the booted system in a temporary container."}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--etc",
        choices=["overlay", "bind", "ro", "rw"],
        default="ro",
        help="How the /etc directory should be mounted",
    )
    _ = parser.add_argument(
        "--home",
        choices=["overlay", "bind", "ro", "rw"],
        default="ro",
        help="How the /home directory should be mounted",
    )
    _ = parser.add_argument(
        "--var",
        choices=["overlay", "bind", "ro", "rw"],
        default="ro",
        help="How the /var directory should be mounted",
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    _args = in_nspawn_system_cmd(
        "--chdir=/root",
        "bash",
        etc=cast(str, args.etc),
        home=cast(str, args.home),
        var=cast(str, args.var),
    )
    _args.remove("--pipe")
    ret = shell(*_args)
    if ret:
        sys.exit(ret)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
