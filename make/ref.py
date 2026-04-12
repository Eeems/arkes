from argparse import (
    ArgumentParser,
    Namespace,
)
from re import sub as re_sub
from typing import (
    Any,
    cast,
)

kwds: dict[str, str] = {
    "help": "What does this do?",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("ref", help="ref name to convert")


def ref(ref: str) -> str:
    return re_sub(r"^[.-]+", "", re_sub(r"[^a-zA-Z0-9_.-]", "-", ref))


def command(args: Namespace) -> None:
    print(ref(cast(str, args.ref)))


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
