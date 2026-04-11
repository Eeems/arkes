import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from collections.abc import Callable
from typing import (
    Any,
    cast,
)

import _os.podman  # noqa: E402 #pyright:ignore [reportMissingImports]

from . import REPO, is_root

_pull = cast(Callable[[str, str | None], None], _os.podman.pull)  # pyright:ignore [reportUnknownMemberType]


def pull(
    image: str,
    arch: str | None = None,
) -> None:
    _pull(image, arch)


kwds: dict[str, str] = {
    "help": "Pull one or more tags from the remote repository",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "target",
        action="extend",
        nargs="+",
        type=str,
        metavar="TAG",
        help="Tag to pull",
    )
    _ = parser.add_argument("--arch", default=None)


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    for target in cast(list[str], args.target):
        pull(f"{REPO}:{target}", cast(str | None, args.arch))


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
