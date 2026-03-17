import sys
import progressbar


from argparse import ArgumentParser
from argparse import Namespace

from typing import Callable
from typing import TextIO
from typing import cast
from typing import Any

from ..system import baseImage
from ..dbus import pull
from ..dbus import checkupdates
from ..dbus import upgrade_status
from ..dbus import upgrade
from ..console import print_stderr
from ..console import AlwaysUpdateProgressBar


kwds = {"help": "Perform a system upgrade"}


class ProgressState:
    MAX_LABEL_SIZE: int = 30

    def __init__(self) -> None:
        self.percent: int = 0
        self.last_line: str | None = None
        self.bar: AlwaysUpdateProgressBar = AlwaysUpdateProgressBar(
            widgets=[
                "Starting",
                " ",
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
        if self.last_line is not None:
            print(self.last_line, end="", file=file)
            if not self.last_line.endswith("\n"):
                print(file=file)

            self.last_line = None

        if line.startswith("[system] "):
            self.last_line = line
            status = line[9:].strip()
            if len(status) >= ProgressState.MAX_LABEL_SIZE:
                status = f"{status[: ProgressState.MAX_LABEL_SIZE - 3]}..."

            self.bar.widgets[0] = status.ljust(ProgressState.MAX_LABEL_SIZE)

        elif line.startswith("PROGRESS "):
            self.last_line = line
            status = line[9:].split("/")[1].split(" ", 1)[1].strip()
            if len(status) >= ProgressState.MAX_LABEL_SIZE:
                status = f"{status[: ProgressState.MAX_LABEL_SIZE - 3]}..."

            self.bar.widgets[0] = status.ljust(ProgressState.MAX_LABEL_SIZE)

        elif line.startswith("STEP "):
            self.last_line = line
            status = line[5:].split("/")[1].split(":", 1)[1].strip()
            if len(status) >= ProgressState.MAX_LABEL_SIZE:
                status = f"{status[: ProgressState.MAX_LABEL_SIZE - 3]}..."

            self.bar.widgets[0] = status.ljust(ProgressState.MAX_LABEL_SIZE)

        else:
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
        help="Disable progress bar",
        action="store_true",
        dest="noProgress",
    )
    _ = parser.add_argument(
        "--quiet",
        help="Disable status output",
        action="store_true",
    )


def noop(_: str) -> None:
    pass


def command(args: Namespace) -> None:
    quiet = cast(bool, args.quiet)
    onstdout: Callable[[str], None] = (
        noop if quiet else cast(Callable[[str], None], print)
    )
    onstderr: Callable[[str], None] = (
        noop if quiet else cast(Callable[[str], None], print_stderr)
    )
    if not cast(bool, args.noPull) and upgrade_status() != "pending":
        if not quiet:
            print("Checking for updates...", file=sys.stderr)

        updates = checkupdates(onstderr=onstderr)
        image = baseImage()
        if [x for x in updates if x.startswith(f"{image} ")]:
            pull(onstdout=onstdout, onstderr=onstderr)

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
