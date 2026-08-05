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

kwds = {}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    sys.exit(
        subprocess.run(
            ["run-parts", "--report", "/usr/lib/system/validate.d"],
            check=False,
        ).returncode
    )


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)