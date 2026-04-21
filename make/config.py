import json
import os
from argparse import (
    ArgumentParser,
    Namespace,
)
from glob import iglob
from typing import (
    Any,
    cast,
)

kwds: dict[str, str] = {
    "help": "Output the JSON representation of the build config",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "-p",
        "--pretty",
        help="Output human readable JSON",
        action="store_true",
    )


def command(args: Namespace) -> None:
    pretty = cast(bool, args.pretty)
    print(json.dumps(parse_all_config(), indent=2 if pretty else None))


type ConfigItem = dict[str, str | None | list[str] | bool]
type Config = dict[str, dict[str, ConfigItem]]


def _get_config_data(
    lines: list[str], prefix: str, multiple: bool = False
) -> list[str] | str | None:
    data = [x[len(prefix) :] for x in lines if x.startswith(prefix)]
    assert len(data) < 2
    if not data:
        return [] if multiple else None

    data = data[0]
    if not multiple:
        return data

    return [x.strip() for x in data.split(",")]


def parse_config(containerfile: str) -> tuple[str, ConfigItem]:
    filename = os.path.basename(containerfile)
    assert filename.endswith(".Containerfile")
    with open(containerfile, "r") as f:
        lines = f.read().splitlines()

    config: ConfigItem = {}
    depends = cast(str | None, _get_config_data(lines, "# x-depends="))
    if depends is not None:
        config["depends"] = depends

    name = cast(str | None, _get_config_data(lines, "# x-name="))
    if name is not None:
        config["name"] = name

    config["templates"] = cast(
        list[str], _get_config_data(lines, "# x-templates=", multiple=True)
    )
    config["clean"] = bool(_get_config_data(lines, "# x-clean", multiple=True))
    config["iso"] = not bool(_get_config_data(lines, "# x-no-iso", multiple=True))
    return filename[:-14], config


def parse_all_config() -> Config:
    return {
        "variants": {
            k: v
            for x in iglob("variants/*.Containerfile")
            for k, v in [parse_config(x)]
        }
    }


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
