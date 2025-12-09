import os
import sys
import shlex

from argparse import ArgumentParser
from argparse import Namespace
from typing import cast
from typing import Any

from ..system import is_root
from ..system import system_kernelCommandLine
from ..system import _execute  # pyright: ignore[reportPrivateUsage]
from ..podman import context_hash
from ..podman import system_hash

kwds = {"help": "Edit the systemfile"}


def register(_: ArgumentParser):
    pass


def command(_: Namespace):
    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    editor = os.environ.get("EDITOR", "micro")
    retcode = _execute(shlex.join([editor, "/etc/system/Systemfile"]))
    if retcode:
        print("Something went wrong while editing the systemfile")
        sys.exit(retcode)

    if system_hash() == context_hash(
        f"KARGS={system_kernelCommandLine()}".encode("utf-8")
    ):
        print("Systemfile context has not been modified")
        return

    print("System context has changed")
    while True:
        choice = input("Perform upgrade? (y/N):")
        match choice.lower():
            case "n" | "":
                break

            case "y":
                sys.exit(_execute("os upgrade"))

            case _:
                continue


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
