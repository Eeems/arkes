from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from . import podman
from . import BUILDER

kwds: dict[str, str] = {
    "help": "Build the niricfg tool builder",
}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    podman(
        "build",
        f"--tag={BUILDER}:niricfg",
        "--file=tools/niricfg/Containerfile",
        "tools/niricfg",
    )


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
