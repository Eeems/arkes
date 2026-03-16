import sys
import time
import progressbar


from argparse import ArgumentParser
from argparse import Namespace

from typing import override
from typing import TextIO
from typing import cast
from typing import Any

from ..system import baseImage
from ..dbus import pull
from ..dbus import checkupdates
from ..dbus import upgrade_status
from ..dbus import upgrade


kwds = {"help": "Perform a system upgrade"}


class AlwaysUpdateProgressBar(progressbar.ProgressBar):
    # Patched to always update
    @override
    def update(self, value: int | None = None):  # pyright: ignore[reportIncompatibleMethodOverride]
        if value is not None and value is not progressbar.UnknownLength:
            if not 0 <= value <= self.maxval:  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
                raise ValueError("Value out of range")

            self.currval = value  # pyright: ignore[reportAttributeAccessIssue, reportUnannotatedClassAttribute]

        # The following line was removed
        # if not self._need_update(): return
        if self.start_time is None:
            raise RuntimeError('You must call "start" before calling "update"')

        now = time.time()
        self.seconds_elapsed = now - self.start_time  # pyright: ignore[reportOperatorIssue, reportUnannotatedClassAttribute]
        self.next_update = self.currval + self.update_interval  # pyright: ignore[reportAttributeAccessIssue, reportUnannotatedClassAttribute, reportUnknownMemberType]
        _ = self.fd.write(self._format_line() + "\r")
        self.fd.flush()
        self.last_update_time = now  # pyright: ignore[reportUnannotatedClassAttribute]


class ProgressState:
    def __init__(self) -> None:
        self.percent: int = 0
        self.bar: AlwaysUpdateProgressBar = AlwaysUpdateProgressBar(
            widgets=[
                progressbar.Bar(),
                " ",
                progressbar.Percentage(),
            ],
            maxval=100,
        )
        _ = self.bar.start()
        self.bar.update(0)

    def update(self, percent: int) -> None:
        self.percent = percent
        self.bar.update(percent)

    def _print(self, line: str, file: TextIO) -> None:
        print("\r\033[K", end="", file=file)
        print(line, end="", file=file)
        if not line.endswith("\n"):
            print(file=file)

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

    state = ProgressState()
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
