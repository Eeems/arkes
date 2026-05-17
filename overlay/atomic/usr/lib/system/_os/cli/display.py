import argparse
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from collections.abc import Callable
from typing import (
    Any,
    cast,
)

from ..niri import (
    getOutputs,
    getOutputScale,
    setOutputScale,
)
from ..system import chronic

kwds = {"help": "Control system display"}


def register(parser: ArgumentParser) -> None:
    parser.set_defaults(parser=parser)
    subparsers = parser.add_subparsers()
    subparser = subparsers.add_parser("scale", help="Get the current system volume")
    _ = subparser.add_argument(
        "--display", help="Display to interact with", default=None
    )
    _ = subparser.add_argument("scale", nargs="?", type=int)
    subparser.set_defaults(func2=command_scale)
    subparser = subparsers.add_parser("list", help="List all displays")
    subparser.set_defaults(func2=command_list)
    subparser = subparsers.add_parser("off", help="Turn off all displays")
    subparser.set_defaults(func2=command_off)
    subparser = subparsers.add_parser("on", help="Turn on all displays")
    subparser.set_defaults(func2=command_on)


def command(args: Namespace) -> None:
    if not hasattr(args, "func2"):
        args.parser.print_help()  # pyright:ignore [reportAny]
        sys.exit(1)

    cast(Callable[[argparse.Namespace], None], args.func2)(args)


def command_scale(args: Namespace) -> None:
    display = cast(str | None, args.display)
    if display is None:
        display = list(getOutputs().keys())[0]

    scale = cast(str | None, args.scale)
    if scale is None:
        print(f"{getOutputScale(display)}%")

    else:
        print(f"{setOutputScale(display, int(scale))}%")


def command_list(_: Namespace) -> None:
    print("\n".join(getOutputs().keys()))


def command_off(_: Namespace) -> None:
    for display in getOutputs().keys():
        chronic("niri", "msg", "output", display, "off")


def command_on(_: Namespace) -> None:
    for display in getOutputs().keys():
        chronic("niri", "msg", "output", display, "on")


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
