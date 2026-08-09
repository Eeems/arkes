import json
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from concurrent.futures import ThreadPoolExecutor
from enum import IntEnum, auto
from functools import partial
from typing import cast

from ..ostree import (
    Deployment,
    deployments,
)
from ..system import (
    is_root,
)


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "deployment",
        type=int,
        help="Deployment to display status for",
        default=None,
        nargs="?",
    )
    _ = parser.add_argument(
        "--packages",
        action="store_true",
        help="Display the packages insalled in this deployment",
    )
    _ = parser.add_argument(
        "--image-packages",
        action="store_true",
        dest="imagePackages",
        help="Display the packages insalled in the image used in this deployment",
    )
    _ = parser.add_argument(
        "--json",
        action="store_true",
        help="Output status as json",
    )


class OutputType(IntEnum):
    Deployment = auto()
    Packages = auto()
    ImagePackages = auto()


class OutputFormat(IntEnum):
    PlainText = auto()
    Json = auto()


def get_status(
    deployment: Deployment,
    outputType: OutputType,
    outputFormat: OutputFormat,
) -> str | dict[str, int | str]:
    match outputType:
        case OutputType.Deployment:
            osInfo = deployment.os_info
            version = osInfo.get("VERSION", "0")
            version_id = osInfo.get("VERSION_ID", "0")
            build_id = osInfo.get("BUILD_ID", "0")
            match outputFormat:
                case OutputFormat.Json:
                    return {
                        "index": deployment.index,
                        "image": deployment.image,
                        "version": f"{version}.{version_id}",
                        "build": build_id,
                        "stateroot": deployment.stateroot,
                        "type": deployment.type,
                        "pinned": deployment.pinned,
                        "unlocked": deployment.unlocked,
                    }

                case OutputFormat.PlainText:
                    status = f"{deployment.index}: {deployment.image}"
                    if deployment.type:
                        status += f" ({deployment.type})"

                    if deployment.pinned:
                        status += " (pinned)"

                    status += f"\n  Version:   {version}.{version_id}"
                    status += f"\n  Build:     {build_id}"
                    status += f"\n  Stateroot: {deployment.stateroot}"
                    if deployment.unlocked and deployment.unlocked != "none":
                        status += f"\n  Unlocked:  {deployment.unlocked}"

                    return status

        case OutputType.Packages:
            match outputFormat:
                case OutputFormat.Json:
                    return json.dumps({"packages": deployment.packages})

                case OutputFormat.PlainText:
                    return "\n".join(
                        [f"{k}: {v}" for k, v in deployment.packages.items()]
                    )

        case OutputType.ImagePackages:
            match outputFormat:
                case OutputFormat.Json:
                    return json.dumps({"imagePackages": deployment.imagePackages})

                case OutputFormat.PlainText:
                    return "\n".join(
                        [f"{k}: {v}" for k, v in deployment.imagePackages.items()]
                    )


class InvalidIndex(Exception):
    pass


def get_index(index: int) -> int:
    requested = index
    maximum = sum(1 for _ in deployments()) - 1
    if index < 0:
        index += maximum + 1

    if 0 <= index <= maximum:
        return index

    if index != requested:
        raise InvalidIndex(
            f"deployment {requested} is {index}, which could not be found"
        )

    raise InvalidIndex(f"deployment {requested} could not be found")


def command(args: Namespace) -> None:
    idx = cast(int | None, args.deployment)
    asJson = cast(bool, args.json)
    outputType = OutputType.Deployment
    if cast(bool, args.packages):
        outputType = OutputType.Packages

    if cast(bool, args.imagePackages):
        if outputType != OutputType.Deployment:
            print(
                "--packages and --image-packages cannot be specified at the same time",
                file=sys.stderr,
            )
            sys.exit(1)

        outputType = OutputType.ImagePackages

    outputFormat = OutputFormat.Json if asJson else OutputFormat.PlainText
    if idx is None:
        if outputType != OutputType.Deployment:
            print(
                "--packages and --image-packages are only valid when a deployment has been selected",
                file=sys.stderr,
            )
            sys.exit(1)

        with ThreadPoolExecutor(max_workers=50) as exc:
            statuses = exc.map(
                partial(get_status, outputType=outputType, outputFormat=outputFormat),
                deployments(),
            )
            match outputFormat:
                case OutputFormat.Json:
                    print(json.dumps(list(statuses)))

                case OutputFormat.PlainText:
                    for status in statuses:
                        print(status)

        return

    if outputType == OutputType.Packages and not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    _deployments = list(deployments())
    try:
        deployment = _deployments[get_index(idx)]

    except InvalidIndex as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(get_status(deployment, outputType, outputFormat))


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
