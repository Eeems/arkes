import string

from glob import glob
from hashlib import sha256
from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

kwds: dict[str, str] = {
    "help": "Get the hash for the builder tool",
}


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--no-newline",
        dest="newline",
        action="store_false",
        help="Don't print the trailing newline",
    )


def command(args: Namespace):
    m = sha256()
    for path in sorted(
        [
            ".github/workflows/tool-builder.yaml",
            "make/builder.py",
            "make/hash-builder.py",
            *glob("tools/builder/**"),
        ]
    ):
        with open(path, "rb") as f:
            m.update(f.read())

    print(hex_to_base62(m.hexdigest()), end="\n" if cast(bool, args.newline) else "")


# Do not use /usr/lib/system/_os version of this to avoid external dependencies while loading
def hex_to_base62(hex_digest: str) -> str:
    if hex_digest.startswith("sha256:"):
        hex_digest = hex_digest[7:]

    return (
        "".join(
            (string.digits + string.ascii_lowercase + string.ascii_uppercase)[
                int(hex_digest, 16) // (62**i) % 62
            ]
            for i in range(50)
        )[::-1].lstrip("0")
        or "0"
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
