import os
from argparse import (
    ArgumentParser,
    Namespace,
)
from glob import iglob
from hashlib import sha256
from typing import (
    Any,
    cast,
)

from . import (
    REPO,
    file_hash,
    image_exists,
    image_labels,
)
from .config import parse_config

kwds: dict[str, str] = {
    "help": "Get the variant hash",
}


def register(parser: ArgumentParser) -> None:
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


def command(args: Namespace) -> None:
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
        perms = f"{os.stat(file)}".encode()
        if os.path.isdir(file):
            parts.append(("dir", file, _hash(perms + file.encode("utf-8"))))

        else:
            with open(file, "rb") as f:
                parts.append(("file", file, _hash(perms + f.read())))

    for file in sorted(
        [
            "build.py",
            "hash.py",
            "pull.py",
            "push.py",
            "__init__.py",
        ]
    ):
        file = f"make/{file}"
        perms = f"{os.stat(file)}".encode()
        with open(file, "rb") as f:
            parts.append(("file", f"make/{file}", _hash(perms + f.read())))

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
        m.update(file_hash(file).encode("utf-8"))

    for file in sorted(
        [
            "build.py",
            "hash.py",
            "pull.py",
            "push.py",
            "__init__.py",
        ]
    ):
        m.update(file_hash(f"make/{file}").encode("utf-8"))

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
