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


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--pre", action="store_true", help="Execute pre-session setup"
    )


def command(args: Namespace) -> None:
    if cast(bool, args.pre):
        cfg_path = os.path.expanduser("~/.config/niri")
        os.makedirs(cfg_path, exist_ok=True)
        kdl_path = os.path.join(cfg_path, "config.kdl")
        if not os.path.exists(kdl_path):
            os.symlink("/usr/share/niri/config.kdl", kdl_path)

        kdl_path = os.path.join(cfg_path, "monitors.kdl")
        if not os.path.exists(kdl_path):
            with open(kdl_path, "w") as f:
                _ = f.write("")

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
