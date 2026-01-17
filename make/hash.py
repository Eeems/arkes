import os

from hashlib import sha256
from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast
from glob import iglob

from . import image_labels
from . import image_exists
from . import REPO

from .config import parse_config

kwds: dict[str, str] = {
    "help": "Get the variant hash",
}


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--debug", action="store_true", help="Show all pieces of the hash"
    )
    _ = parser.add_argument(
        "target",
        action="extend",
        nargs="+",
        type=str,
        metavar="VARIANT",
        help="Variant to hash",
    )


def command(args: Namespace):
    for target in cast(list[str], args.target):
        if not cast(bool, args.debug):
            print(f"{target}: {hash(target)[:9]}")
            continue

        print(f"{target}: {hash(target)[:9]}\n  ", end="")
        print("\n  ".join([f"{t.ljust(5)} {n}: {h}" for t, n, h in hash_parts(target)]))


def _hash(value: bytes) -> str:
    m = sha256()
    m.update(value)
    return m.hexdigest()[:9]


def hash_parts(target: str) -> list[tuple[str, str, str]]:
    parts: list[tuple[str, str, str]] = []
    containerfile = (
        f"variants/{target}.Containerfile"
        if target != "rootfs"
        else "rootfs.Containerfile"
    )
    # TODO also include hash from x-depends
    if "-" in target and not os.path.exists(containerfile):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        image = f"{REPO}:{base_variant}"
        labels = image_labels(image, not image_exists(image, False, False))
        parts.append(("image", image, labels["hash"][:9]))

    elif target != "rootfs":
        _, config = parse_config(containerfile)
        depends = config.get("depends", "rootfs")
        image = f"{REPO}:{depends}"
        labels = image_labels(image, not image_exists(image, False, False))
        parts.append(("image", image, labels["hash"][:9]))

    with open(containerfile, "rb") as f:
        parts.append(("file", containerfile, _hash(f.read())))

    for file in sorted(iglob(f"overlay/{target}/**", recursive=True)):
        if os.path.isdir(file):
            parts.append(("dir", file, _hash(file.encode("utf-8"))))

        else:
            with open(file, "rb") as f:
                parts.append(("file", file, _hash(f.read())))

    for file in sorted(
        [
            "build.py",
            "hash.py",
            "pull.py",
            "push.py",
            "__init__.py",
        ]
    ):
        with open(f"make/{file}", "rb") as f:
            parts.append(("file", f"make/{file}", _hash(f.read())))

    return parts


def hash(target: str) -> str:
    m = sha256()
    containerfile = (
        f"variants/{target}.Containerfile"
        if target != "rootfs"
        else "rootfs.Containerfile"
    )
    if "-" in target and not os.path.exists(containerfile):
        base_variant, template = target.rsplit("-", 1)
        containerfile = f"templates/{template}.Containerfile"
        image = f"{REPO}:{base_variant}"
        labels = image_labels(image, not image_exists(image, False, False))
        m.update(labels["hash"].encode("utf-8"))

    with open(containerfile, "rb") as f:
        m.update(f.read())

    for file in sorted(iglob(f"overlay/{target}/**", recursive=True)):
        if os.path.isdir(file):
            m.update(file.encode("utf-8"))

        else:
            with open(file, "rb") as f:
                m.update(f.read())

    for file in sorted(
        [
            "build.py",
            "hash.py",
            "pull.py",
            "push.py",
            "__init__.py",
        ]
    ):
        with open(f"make/{file}", "rb") as f:
            m.update(f.read())

    return m.hexdigest()


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
