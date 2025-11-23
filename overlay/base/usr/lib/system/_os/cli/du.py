import os
import sys
import subprocess

from argparse import ArgumentParser
from argparse import Namespace
from typing import cast
from typing import Any

from ..system import is_root
from ..ostree import deployments

kwds = {"help": "Output size of current deployments"}


def register(_: ArgumentParser):
    pass


def command(_: Namespace):
    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    _deployments = list(deployments())
    sizes = list(
        reversed(
            subprocess.check_output(
                [
                    "du",
                    "-hs",
                    *[x.path for x in reversed(_deployments)],
                ]
            )
            .strip()
            .decode("utf-8")
            .split("\n")
        )
    )
    for deployment in _deployments:
        diffsize = sizes[deployment.index].split()[0]
        size = (
            subprocess.check_output(["du", "-hs", deployment.path])
            .strip()
            .decode("utf-8")
            .split()[0]
        )
        print(f"{deployment.index}: {size} (+{diffsize})", end="")
        if deployment.type:
            print(f" ({deployment.type})", end="")

        print()

    size = size = (
        subprocess.check_output(
            [
                "du",
                "-hs",
                *set([os.path.dirname(x.path) for x in _deployments]),
            ]
        )
        .strip()
        .decode("utf-8")
        .split()[0]
    )
    print(f"total: {size}")


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
