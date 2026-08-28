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
from .config import all_targets

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

    targets = cast(list[str], args.target)
    invalid = [target for target in targets if target not in all_targets() - {"rootfs"}]
    if invalid:
        print(
            f"Invalid ISO target(s): {', '.join(invalid)}",
            file=sys.stderr,
        )
        sys.exit(1)

    storage_info = cast(
        dict[str, dict[str, str]],
        json.loads(
            subprocess.check_output(
                [*podman_cmd("info"), "--format", "json"],
                text=True,
            )
        ),
    )
    store = storage_info["store"]
    for target in targets:
        old_iso = glob.glob(f"/var/lib/system/arkes-{target}-*.iso")
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
                f"env=HOST_STORAGE_DRIVER={store['graphDriverName']}",
            ],
            volumes=[
                f"{store['graphRoot']}:/host-storage",
                f"{store['runRoot']}:/host-runroot",
            ],
        )
        for path in old_iso:
            os.unlink(path)


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
