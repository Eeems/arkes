import glob
import json
import os
import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from . import (
    REPO,
    in_system,
    is_root,
    podman_cmd,
)

kwds: dict[str, str] = {
    "help": "Build an ISO for a variant",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("target", action="extend", nargs="*", type=str)
    _ = parser.add_argument(
        "--no-local-image",
        help="If the image should be copied to the iso container storage",
        dest="localImage",
        action="store_false",
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    storage_info = json.loads(
        subprocess.check_output(
            [*podman_cmd("info"), "--format", "json"],
            text=True,
        )
    )
    store = storage_info["store"]
    graph_root = store["graphRoot"]
    run_root = store["runRoot"]
    driver = store["graphDriverName"]

    for target in cast(list[str], args.target):
        for path in glob.glob(f"/var/lib/system/arkes-{target}-*.iso"):
            os.unlink(path)

        image = f"{REPO}:{target}"
        _ = in_system(
            "_build",
            target=image,
            check=True,
            flags=["cap-add=SYS_ADMIN"],
        )
        _ = in_system(
            "iso",
            *([] if cast(bool, args.localImage) else ["--no-local-image"]),
            check=True,
            flags=[
                "cap-add=SYS_ADMIN",
                f"env=HOST_STORAGE_DRIVER={driver}",
            ],
            volumes=[
                f"{graph_root}:/host-storage",
                f"{run_root}:/host-runroot",
            ],
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
