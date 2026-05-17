import os
import shlex
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..podman import (
    context_hash,
    system_hash,
)
from ..system import (
    _execute,  # pyright: ignore[reportPrivateUsage]
    is_root,
    system_kernelCommandLine,
)

kwds = {"help": "Edit the systemfile"}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    editor = os.environ.get("EDITOR", "micro")
    retcode = _execute(shlex.join([*shlex.split(editor), "/etc/system/Systemfile"]))
    if retcode:
        print("Something went wrong while editing the systemfile", file=sys.stderr)
        sys.exit(retcode)

    if system_hash() == context_hash(f"KARGS={system_kernelCommandLine()}".encode()):
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
