from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import Any, cast

kwds: dict[str, str] = {
    "help": "What does this do?",
}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    pass


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
