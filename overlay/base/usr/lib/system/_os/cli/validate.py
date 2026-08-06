import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from ..system import execute

kwds: dict[str, str] = {}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    try:
        execute("run-parts", "--report", "/usr/lib/system/validate.d")

    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

    sys.exit(0)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
