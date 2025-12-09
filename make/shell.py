import sys
import _os.console  # pyright: ignore[reportMissingImports]

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast
from typing import Protocol

from . import image_exists
from . import podman_cmd
from .pull import pull


class ShellCallable(Protocol):
    def __call__(self, *args: str) -> None: ...


shell = cast(ShellCallable, _os.console.shell)  # pyright:ignore [reportUnknownMemberType]

kwds: dict[str, str] = {
    "help": "Open the shell for a variant",
}


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--variant",
        default="base",
        help="Which variant to use, defaults to base.",
    )


def command(args: Namespace):
    image = f"ghcr.io/eeems/arkes:{cast(str, args.variant)}"
    if not image_exists(image, False, True):
        if not image_exists(image, True, True):
            print(f"{image} does not exist")
            sys.exit(1)

        pull(image)

    shell(*podman_cmd("run", "--rm", "-it", image))


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
