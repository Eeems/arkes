import string
from argparse import (
    ArgumentParser,
    Namespace,
)
from glob import glob
from hashlib import sha256
from typing import (
    Any,
    cast,
)

if __name__ == "__main__":
    import os
    import sys
    from collections.abc import Callable

    here = os.path.dirname(__file__)
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(here),
            "overlay/base/usr/lib/system",
        ),
    )
    if here in sys.path:
        sys.path.remove(here)

    import _os.system  # pyright: ignore[reportMissingImports]

    file_hash = cast(Callable[[str], str], _os.system.file_hash)  # pyright:ignore [reportUnknownMemberType]

else:
    from . import file_hash

kwds: dict[str, str] = {
    "help": "Get the hash for the niricfg tool's builder",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--no-newline",
        dest="newline",
        action="store_false",
        help="Don't print the trailing newline",
    )


def command(args: Namespace) -> None:
    m = sha256()
    for file in sorted(
        [
            ".github/workflows/tool-niricfg.yaml",
            "make/niricfg.py",
            "make/hash-niricfg.py",
            *glob("tools/niricfg/Containerfile", recursive=True),
        ]
    ):
        m.update(file_hash(file).encode("utf-8"))

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
