import json
import os
import re
import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from datetime import datetime
from typing import (
    Any,
    cast,
)

import requests

from . import (
    REPO,
    image_exists,
    image_hash,
    image_labels,
    image_qualified_name,
    in_system,
    is_root,
)
from .hash import hash
from .pull import pull

kwds: dict[str, str] = {
    "help": "Check to see if a variant has updates and needs to be rebuilt",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--target",
        default="rootfs",
        metavar="VARIANT",
        help="Which variant to check",
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    target = cast(str, args.target)
    containerfile = f"variants/{target}.Containerfile"
    if target == "rootfs":
        containerfile = "rootfs.Containerfile"

    elif "-" in target and not os.path.exists(containerfile):
        _, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"

    image = image_qualified_name(f"{REPO}:{target}")
    exists = image_exists(image, True, False)
    if exists and not image_exists(image, False, False):
        try:
            pull(image)

        except subprocess.CalledProcessError:
            pass

    if exists:
        mirrors = cast(
            list[str],
            json.loads(image_labels(image, False).get("mirrorlist", "[]")),
        )

    else:
        mirrors = ["https://archive.archlinux.org/repos/2025/11/06/$repo/os/$arch"]

    m = None
    for mirror in mirrors:
        m = re.match(r"^(.+)\/(\d{4}\/\d{2}\/\d{2})\/\$repo\/os\/\$arch$", mirror)
        if m:
            break

    has_updates = False
    if m:
        current = m.group(2)
        now = datetime.now()
        new = f"{now.year}/{now.strftime('%m')}/{now.strftime('%d')}"
        # TODO only do mirrorlist check against rootfs, and be smarter about missed days
        if current != new:
            found_count = 0
            repos = ("core", "extra", "multilib")
            for repo in repos:
                # TODO make arch dynamic instead of hardcoded when more than x86_64 is added
                url = f"{m.group(1)}/{new}/{repo}/os/x86_64/{repo}.db"
                res = requests.head(url, timeout=20)
                if res.status_code == 200:
                    found_count += 1

                elif res.status_code != 404:
                    print(res.reason)
                    sys.exit(1)

            # Only update if all repos are available, we could be checking mid-rsync
            if found_count == len(repos):
                print(f"mirrorlist {current} -> {new}")
                has_updates = True

    new_hash = hash(target)
    current_hash = image_hash(image) if exists else ""
    if current_hash != new_hash:
        print(f"context {current_hash[:9] or '(none)'} -> {new_hash[:9]}")
        has_updates = True

    if not image_exists(image, False, False):
        if has_updates:
            sys.exit(2)

        return

    res = in_system(
        "-ec",
        " ".join(
            [
                "if [ -f /usr/bin/chronic ]; then",
                "  /usr/bin/chronic /usr/lib/system/initialize_pacman;",
                "else",
                "  /usr/lib/system/initialize_pacman > /dev/null;",
                "fi;",
                "if [ -f /usr/bin/checkupdates ];then",
                "  /usr/bin/checkupdates;",
                "fi",
            ]
        ),
        entrypoint="/bin/bash",
        target=image,
    )
    if res == 1:
        sys.exit(1)

    elif res == 2:
        has_updates = True

    if has_updates:
        sys.exit(2)


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
