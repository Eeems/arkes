import os

from argparse import ArgumentParser
from argparse import Namespace

from typing import cast

from ..niri import getOutputs
from ..niri import setOutputScale
from ..niri import setVolumeOut
from ..niri import getVolumeOut
from ..niri import setVolumeIn
from ..niri import getVolumeIn


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--pre", action="store_true", help="Execute pre-session setup"
    )


def command(args: Namespace):
    if cast(bool, args.pre):
        os.makedirs("/usr/local/share/niri/", exist_ok=True)
        if not os.path.exists("/usr/local/share/niri/config.kdl"):
            with open("/usr/local/share/niri/config.kdl", "w") as f:
                _ = f.write("\n")

        return

    # TODO load settings from a config file
    for display in getOutputs().keys():
        _ = setOutputScale(display, 100)

    # Ensure volumes are clipped to the max allowed
    _ = setVolumeOut(getVolumeOut())
    _ = setVolumeIn(getVolumeIn())
    config = os.path.expanduser("~/.config/waypaper/config.ini")
    if not os.path.exists(config):
        os.symlink("/usr/share/waypaper/config.ini", config)


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
