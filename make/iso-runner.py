import subprocess
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

DEFAULT_SOURCE_URL = "https://github.com/Eeems/arkes"

kwds: dict[str, str] = {
    "help": "Build the iso-runner tool image",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="org.opencontainers.image.source label",
    )
    _ = parser.add_argument(
        "--revision",
        default=None,
        help="org.opencontainers.image.revision label",
    )


def command(args: Namespace) -> None:
    revision = cast(str | None, args.revision)
    if not revision:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()

    source_url = cast(str, args.source_url)
    podman(
        "build",
        "--cap-add=SYS_ADMIN",
        f"--tag={IMAGE}",
        f"--label=org.opencontainers.image.source={source_url}",
        f"--label=org.opencontainers.image.revision={revision}",
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
