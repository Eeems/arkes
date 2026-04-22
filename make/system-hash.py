from argparse import (
    ArgumentParser,
    Namespace,
)
from collections.abc import Callable
from typing import (
    Any,
    cast,
)

from . import _os  # pyright: ignore[reportPrivateUsage, reportPrivateLocalImportUsage]

context_hash = cast(Callable[[bytes], str], _os.podman.context_hash)  # pyright:ignore [reportUnknownMemberType]
system_kernelCommandLine = cast(
    Callable[[], str],
    _os.system.system_kernelCommandLine,  # pyright:ignore [reportUnknownMemberType]
)

kwds: dict[str, str] = {
    "help": "What does this do?",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--short", action="store_true", help="Display short hash")


def command(args: Namespace) -> None:
    sys_hash = context_hash(f"KARGS={system_kernelCommandLine()}".encode())
    if cast(bool, args.short):
        print(sys_hash[:9])
        return

    print(sys_hash)


if __name__ == "__main__":
    kwds["description"] = kwds["help"]
    del kwds["help"]
    parser = ArgumentParser(
        **cast(  # pyright: ignore[reportAny]
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            kwds,
        ),
    )
    register(parser)
    args = parser.parse_args()
    command(args)
