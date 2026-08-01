import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from concurrent.futures import ThreadPoolExecutor
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


def get_status(
    deployment: Deployment, showPackages: bool = False, showImagePackages: bool = False
) -> str:
    if showPackages:
        return "\n".join([f"{k}: {v}" for k, v in deployment.packages.items()])

    if showImagePackages:
        return "\n".join([f"{k}: {v}" for k, v in deployment.imagePackages.items()])

    osInfo = deployment.os_info
    version = osInfo.get("VERSION", "0")
    version_id = osInfo.get("VERSION_ID", "0")
    build_id = osInfo.get("BUILD_ID", "0")
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
    showPackages = cast(bool, args.packages)
    showImagePackages = cast(bool, args.imagePackages)
    if idx is None:
        if showPackages or showImagePackages:
            print(
                "Error: --packages and --image-packages are only valid when a deployment has been selected"
            )
            sys.exit(1)

        with ThreadPoolExecutor(max_workers=50) as exc:
            for status in exc.map(get_status, deployments()):
                print(status)

        return

    if showPackages and not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    _deployments = list(deployments())
    try:
        deployment = _deployments[get_index(idx)]

    except InvalidIndex as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(get_status(deployment, showPackages, showImagePackages))


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
