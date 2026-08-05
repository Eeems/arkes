import os
import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from glob import iglob
from typing import (
    Any,
    cast,
)

kwds = {}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> None:
    failed = False
    for script in sorted(
        path
        for path in iglob("/usr/lib/system/validate.d/*")
        if os.path.isfile(path) and os.access(path, os.X_OK)
    ):
        name = os.path.basename(script)
        result = subprocess.run(
            [script],
            check=False,
            capture_output=True,
        )
        if result.returncode:
            failed = True
            print(f"validate: {name} failed", file=sys.stderr)

        if result.stdout:
            sys.stdout.write(result.stdout.decode("utf-8"))  # pyright: ignore [reportUnusedCallResult]

        if result.stderr:
            sys.stderr.write(result.stderr.decode("utf-8"))  # pyright: ignore [reportUnusedCallResult]

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
