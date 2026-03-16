import sys
import progressbar


from argparse import ArgumentParser
from argparse import Namespace

from typing import TextIO
from typing import cast
from typing import Any


from ..system import baseImage
from ..dbus import pull
from ..dbus import checkupdates
from ..dbus import upgrade_status
from ..dbus import upgrade


kwds = {"help": "Perform a system upgrade"}


class _ProgressState:
    def __init__(self, bar: progressbar.ProgressBar) -> None:
        self.percent: int = 0
        self.bar: progressbar.ProgressBar = bar

    def update(self, progress: tuple[int, str]) -> None:
        percent, step = progress
        self.percent = percent
        self.bar.widgets[4] = step
        self.bar.update(percent)

    def _print(self, line: str, file: TextIO) -> None:
        self.bar.finish()
        print(line, end="", file=file)
        _ = self.bar.start()
        self.bar.update(self.percent)

    def stdout(self, line: str) -> None:
        self._print(line, sys.stdout)

    def stderr(self, line: str) -> None:
        self._print(line, sys.stderr)


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--no-pull",
        help="Do not pull base image updates",
        action="store_true",
        dest="noPull",
    )
    _ = parser.add_argument(
        "--no-progress",
        help="Disable progress bar and show upgrade output",
        action="store_true",
        dest="noProgress",
    )


def command(args: Namespace) -> None:
    if not cast(bool, args.noPull) and upgrade_status() != "pending":
        print("Checking for updates...")
        updates = checkupdates()
        image = baseImage()
        if [x for x in updates if x.startswith(f"{image} ")]:
            pull()

    if cast(bool, args.noProgress):
        upgrade()
        return

    state = _ProgressState(
        progressbar.ProgressBar(
            widgets=[progressbar.Bar(), " ", progressbar.Percentage(), " - ", "Build"],
            maxval=100,
        ).start()
    )
    try:
        upgrade(onprogress=state.update, onstdout=state.stdout, onstderr=state.stderr)

    finally:
        state.bar.finish()


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
