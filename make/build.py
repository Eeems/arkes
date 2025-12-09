import subprocess
import sys
import os

from datetime import datetime
from datetime import UTC
from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from . import is_root
from . import podman_cmd
from . import image_exists
from . import base_images
from . import image_labels
from . import podman
from . import REPO

from .pull import pull
from .push import push
from .hash import hash
from .config import parse_config

kwds: dict[str, str] = {
    "help": "Build a variant",
}


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--push",
        action="store_true",
        help="Push the image after the build",
    )
    _ = parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        help="Do not reuse the previous layer cache when building",
    )
    _ = parser.add_argument(
        "target",
        action="extend",
        nargs="+",
        type=str,
        metavar="VARIANT",
        help="Variant to build",
    )


def command(args: Namespace):
    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    for target in cast(list[str], args.target):
        build(target, cast(bool, args.cache))
        if cast(bool, args.push):
            push(target)


def build(target: str, cache: bool = True):
    now = datetime.now(UTC)
    build_args: dict[str, str] = {}
    containerfile = f"variants/{target}.Containerfile"
    if target == "rootfs":
        containerfile = "rootfs.Containerfile"

    elif "-" in target and not os.path.exists(containerfile):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        build_args["BASE_VARIANT_ID"] = f"{base_variant}"

    for base_image in base_images(containerfile, build_args):
        print(f"Base image {base_image}")
        if not image_exists(base_image, False, False):
            pull(base_image)

    build_tag = f"localhost/build:{target}"
    podman(
        "build",
        f"--tag={build_tag}",
        *[f"--build-arg={k}={v}" for k, v in build_args.items()],
        *[] if cache else ["--no-cache"],
        "--force-rm",
        "--pull=never",
        "--volume=/var/cache/pacman:/var/cache/pacman",
        f"--file={containerfile}",
        "--format=oci",
        "--timestamp=1735689640",
        ".",
    )
    if target == "rootfs":
        podman("tag", build_tag, f"{REPO}:{target}")
        podman("rmi", build_tag)
        return

    build_args["VERSION_ID"] = f"{now.strftime('%H%M%S')}{int(now.microsecond / 10000)}"
    build_args["HASH"] = hash(target)
    if "-" in target and not os.path.exists(f"variants/{target}.Containerfile"):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        image = f"{REPO}:{base_variant}"
        labels = image_labels(image, not image_exists(image, False, False))
        build_args["VARIANT"] = f"{labels['os-release.VARIANT']} ({template})"
        build_args["VARIANT_ID"] = f"{labels['os-release.VARIANT_ID']}-{template}"
        if not image_exists(f"{REPO}:{base_variant}", False, False):
            pull(f"{REPO}:{base_variant}")

    else:
        image = f"{REPO}:rootfs"
        labels = image_labels(image, not image_exists(image, False, False))
        variant_id, config = parse_config(containerfile)
        name = config.get("name", target)
        assert isinstance(name, str)
        build_args["VARIANT"] = name
        build_args["VARIANT_ID"] = variant_id

    build_args["MIRRORLIST"] = f"{labels['mirrorlist']}"
    build_args["VERSION"] = f"{labels['os-release.VERSION']}"
    build_args["VERSION_ID"] = f"{labels['os-release.VERSION_ID']}"
    build_args["NAME"] = f"{labels['os-release.NAME']}"
    build_args["PRETTY_NAME"] = f"{labels['os-release.PRETTY_NAME']}"
    build_args["ID"] = f"{labels['os-release.ID']}"
    build_args["HOME_URL"] = f"{labels['os-release.HOME_URL']}"
    build_args["BUG_REPORT_URL"] = f"{labels['os-release.BUG_REPORT_URL']}"
    build_args["PACKAGES"] = (
        subprocess.check_output(
            podman_cmd(
                "run",
                "--rm",
                "--entrypoint=/usr/sbin/pacman",
                build_tag,
                "-Q",
            )
        )
        .decode("utf-8")
        .strip()
    )
    build_args["BUILD_TAG"] = build_tag
    podman(
        "build",
        f"--tag={REPO}:{target}",
        *[f"--build-arg={k}={v}" for k, v in build_args.items()],
        "--force-rm",
        "--pull=never",
        "--file=variant.Containerfile",
        "--format=oci",
        "--timestamp=1735689640",
        ".",
    )
    podman("rmi", build_tag)


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
