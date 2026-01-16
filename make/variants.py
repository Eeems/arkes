from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from .config import parse_all_config
from .config import Config

kwds: dict[str, str] = {
    "help": "Lists all configured variants",
}


def register(_: ArgumentParser):
    pass


def command(_: Namespace):
    config: Config = parse_all_config()
    variants: list[str] = []
    for variant, data in cast(
        dict[str, dict[str, str | None | list[str]]], config["variants"]
    ).items():
        if variant in ("check", "rootfs"):
            raise ValueError(f"Invalid use of protected variant name: {variant}")

        variants.append(variant)
        for template in cast(list[str], data["templates"]):
            variants.append(f"{variant}-{template}")

    variants.sort()
    print("\n".join(variants))


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
