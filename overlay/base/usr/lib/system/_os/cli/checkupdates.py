import sys
import traceback
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..dbus import (
    checkupdates,
    pull,
    pull_available,
)
from ..system import (
    _execute,  # pyright:ignore [reportPrivateUsage]
    baseImage,
)

kwds = {"help": "Checks for updates to the system"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--force",
        action="store_true",
        help="Force check updates, even if there are already known updates",
    )
    _ = parser.add_argument(
        "--download",
        action="store_true",
        help="Download the updated image if found",
    )


def command(args: Namespace) -> None:
    ret = _execute("nm-online --quiet")
    if ret:
        print("Not currently online", file=sys.stderr)
        sys.exit(1)

    force = cast(bool, args.force)
    updates: list[str] = []
    try:
        updates = checkupdates(force)

    except BaseException:
        traceback.print_exc()
        sys.exit(1)

    if not updates:
        return

    print("\n".join(updates))
    if cast(bool, args.download):
        if (
            [x for x in updates if x.startswith(f"{baseImage()} ")]
            and force
            or pull_available()
        ):
            try:
                pull()

            except BaseException:
                traceback.print_exc()
                sys.exit(1)

    sys.exit(2)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
