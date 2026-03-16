from argparse import ArgumentParser
from argparse import Namespace
from typing import cast
from typing import Any

import progressbar

from ..system import baseImage
from ..dbus import pull
from ..dbus import checkupdates
from ..dbus import upgrade_status
from ..dbus import upgrade


kwds = {"help": "Perform a system upgrade"}


def _on_progress(
    progress_bar: progressbar.ProgressBar,
    progress: tuple[int, str],
) -> None:
    percent, step = progress
    progress_bar.widgets[4] = step
    progress_bar.update(percent)


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
        updates = checkupdates()
        image = baseImage()
        if [x for x in updates if x.startswith(f"{image} ")]:
            pull()

    if cast(bool, args.noProgress):
        upgrade()
        return

    progress_bar = progressbar.ProgressBar(
        maxval=100,
        widgets=[
            progressbar.Bar(),
            " ",
            progressbar.Percentage(),
            " - ",
            "",
        ],
    )
    _ = progress_bar.start()
    try:
        upgrade(
            onprogress=lambda progress, pb=progress_bar: _on_progress(pb, progress),
            onstdout=lambda _: None,
            onstderr=lambda _: None,
        )

    finally:
        progress_bar.finish()


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
