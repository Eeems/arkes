import json
import os
import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from datetime import (
    UTC,
    datetime,
)
from platform import uname
from typing import (
    Any,
    cast,
)

from . import (
    REPO,
    base_images,
    execute,
    image_exists,
    image_labels,
    is_root,
    podman,
    podman_cmd,
)
from .config import parse_config
from .hash import hash
from .pull import pull
from .push import push
from .rootfs import get_build_args

kwds: dict[str, str] = {
    "help": "Build a variant",
}


def register(parser: ArgumentParser) -> None:
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
    _ = parser.add_argument("--arch", default=None)


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    for target in cast(list[str], args.target):
        build(target, cast(bool, args.cache), cast(str | None, args.arch))
        if cast(bool, args.push):
            push(target)


binfmt_fix = """
for x in /usr/lib/binfmt.d/*.conf; do
  sed 's/\\(:[^C:]*\\)$/\\1C/' "$x" | sudo tee /etc/binfmt.d/$(basename $x) > /dev/null
done
"""


def build(target: str, cache: bool = True, arch: str | None = None) -> None:
    machine = uname().machine
    if arch is None:
        arch = machine

    if arch != machine and not os.path.exists(f"/etc/binfmt.d/qemu-{arch}-static.conf"):
        print(
            "Creating binfmt.d configuration that allows setuid to be properly handled in qemu-static"
        )
        execute("bash", "c", binfmt_fix)
        execute("systemctl", "restart", "systemd-binfmt")

    now = datetime.now(UTC)
    build_args: dict[str, str] = {}
    containerfile = f"variants/{target}.Containerfile"
    if target == "rootfs":
        containerfile = "rootfs.Containerfile"

    elif "-" in target and not os.path.exists(containerfile):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        build_args["BASE_VARIANT_ID"] = f"{base_variant}"

    build_args["PACSTRAP"], build_args["PACSTRAP_PLATFORM"] = pacstrap(arch)
    build_args["PACKAGES"] = " ".join(packages(arch))
    config = get_build_args()
    mirrorlist = mirrors(
        arch,
        config["ARCHIVE_YEAR"],
        config["ARCHIVE_MONTH"],
        config["ARCHIVE_DAY"],
    )
    build_args["MIRRORS"] = " ".join(mirrorlist)
    build_args["REPOS"] = " ".join(repos(arch))
    build_args["MIRRORLIST"] = json.dumps(mirrorlist)
    for base_image in base_images(containerfile, build_args):
        print(f"Base image {base_image}")
        if not image_exists(base_image, False, False):
            pull(base_image, arch)

    build_tag = f"localhost/build:{target}"
    if target == "rootfs":
        build_args["HASH"] = hash(target)

    match arch:
        case "x86_64":
            platform = "amd64"

        case "aarch64":
            platform = "arm64"

        case _:
            raise NotImplementedError(f"{arch} is not supported yet")

    podman(
        "build",
        f"--tag={build_tag}",
        *[f"--build-arg={k}={v}" for k, v in build_args.items()],
        *[] if cache else ["--no-cache"],
        "--force-rm",
        "--cap-add=SYS_ADMIN",
        "--pull=never",
        "--volume=/var/cache/pacman:/var/cache/pacman",
        f"--file={containerfile}",
        "--format=oci",
        "--timestamp=1735689640",
        f"--platform=linux/{platform}",
        ".",
    )
    if target == "rootfs":
        podman("tag", build_tag, f"{REPO}:{target}")
        podman("rmi", build_tag)
        return

    build_args["HASH"] = hash(target)
    if "-" in target and not os.path.exists(f"variants/{target}.Containerfile"):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        image = f"{REPO}:{base_variant}"
        labels = image_labels(image, not image_exists(image, False, False))
        build_args["VARIANT"] = f"{labels['os-release.VARIANT']} ({template})"
        build_args["VARIANT_ID"] = f"{labels['os-release.VARIANT_ID']}-{template}"
        build_args["VERSION_ID"] = f"{labels['os-release.VERSION_ID']}"
        if not image_exists(f"{REPO}:{base_variant}", False, False):
            pull(f"{REPO}:{base_variant}", arch)

    else:
        image = f"{REPO}:rootfs"
        labels = image_labels(image, not image_exists(image, False, False))
        variant_id, config = parse_config(containerfile)
        name = config.get("name", target)
        assert isinstance(name, str)
        build_args["VARIANT"] = name
        build_args["VARIANT_ID"] = variant_id
        build_args["VERSION_ID"] = (
            f"{now.strftime('%H%M%S')}{int(now.microsecond / 10000)}"
        )

    build_args["VERSION"] = f"{labels['os-release.VERSION']}"
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
        f"--platform=linux/{platform}",
        ".",
    )
    podman("rmi", build_tag)


def mirrors(arch: str, year: str, month: str, day: str) -> list[str]:
    match arch:
        case "x86_64":
            return [
                f"https://archive.archlinux.org/repos/{year}/{month}/{day}/$repo/os/$arch",
                f"https://umea.archive.pkgbuild.com/repos/{year}/{month}/{day}/$repo/os/$arch",
            ]

        case "aarch64":
            return [
                f"https://pkgmirror.sametimetomorrow.net/$arch/repos/{year}/{month}/{day}/$repo",
            ]

        case _:
            raise NotImplementedError(f"{arch} is not supported yet")


def repos(arch: str) -> tuple[str, ...]:
    match arch:
        case "x86_64":
            return "core", "extra", "multilib"

        case "aarch64":
            return "core", "extra", "alarm", "aur"

        case _:
            raise NotImplementedError(f"{arch} is not supported yet")


def pacstrap(arch: str) -> tuple[str, str]:
    match arch:
        case "x86_64":
            return (
                "docker.io/library/archlinux:base-devel-20260104.0.477168",
                "linux/amd64",
            )

        case "aarch64":
            return "docker.io/danhunsaker/archlinuxarm:20260405", "linux/amd64"

        case _:
            raise NotImplementedError(f"{arch} is not supported yet")


def packages(arch: str) -> list[str]:
    match arch:
        case "x86_64":
            return [
                "base",
                "moreutils",
                "mkinitcpio",
            ]

        case "aarch64":
            return packages("x86_64") + [
                "archlinuxarm-keyring",
            ]

        case _:
            raise NotImplementedError(f"{arch} is not supported yet")


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
