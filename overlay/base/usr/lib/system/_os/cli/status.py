import sys

from typing import cast

from argparse import ArgumentParser
from argparse import Namespace

from concurrent.futures import ThreadPoolExecutor

from ..system import baseImage
from ..ostree import deployments
from ..ostree import Deployment


def register(parser: ArgumentParser):
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
    ref = baseImage(f"{deployment.path}/etc/system/Systemfile")
    version = osInfo.get("VERSION", "0")
    version_id = osInfo.get("VERSION_ID", "0")
    build_id = osInfo.get("BUILD_ID", "0")
    status = f"{deployment.index}: {ref}"
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


def command(args: Namespace):
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

    _deployments = list(deployments())
    _idx = idx
    if idx < 0:
        idx = len(_deployments) + idx

    if idx < 0 or idx >= len(_deployments):
        if idx != _idx:
            print(
                f"Error: deployment {_idx} is {idx}, which could not be found",
                file=sys.stderr,
            )

        else:
            print(f"Error: deployment {_idx} could not be found", file=sys.stderr)

        sys.exit(1)

    deployment = _deployments[idx]
    print(get_status(deployment, showPackages, showImagePackages))


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
