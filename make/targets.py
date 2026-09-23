from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from .config import all_targets

kwds: dict[str, str] = {
    "help": "Lists all valid build targets",
}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    for target in sorted(all_targets()):
        print(target)


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
