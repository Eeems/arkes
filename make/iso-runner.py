from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from . import (
    BUILDER,
    podman,
)

IMAGE = f"{BUILDER}:iso-runner"

kwds: dict[str, str] = {
    "help": "Build the iso-runner tool image",
}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    podman(
        "build",
        f"--tag={IMAGE}",
        "--file=tools/iso-runner/Containerfile",
        "tools/iso-runner",
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