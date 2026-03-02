from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from . import podman
from . import BUILDER

kwds: dict[str, str] = {
    "help": "Build the niricfg tool",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--build-image", action="store_true", dest="build_image")


def command(args: Namespace) -> None:
    image = f"{BUILDER}:niricfg"
    if cast(bool, args.build_image):
        podman(
            "build",
            f"--tag={image}",
            "--file=tools/niricfg/Containerfile",
            "tools/niricfg",
        )

    podman(
        "run",
        "--rm",
        "--volume=./tools/niricfg:/src:rw",
        "--workdir=/src",
        image,
        "bash",
        "-c",
        "yes | flet build linux",
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
