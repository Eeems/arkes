from argparse import ArgumentParser
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor

from ..system import baseImage
from ..ostree import deployments
from ..ostree import Deployment


def register(_: ArgumentParser):
    pass


def get_status(deployment: Deployment) -> str:
    osInfo = deployment.os_info
    ref = baseImage(f"{deployment.path}/etc/system/Systemfile")
    version = osInfo.get("VERSION", "0")
    version_id = osInfo.get("VERSION_ID", "0")
    build_id = osInfo.get("BUILD_ID", "0")
    status = f"{deployment.index}: {ref}"
    if type:
        status += f" ({deployment.type})"

    if deployment.pinned:
        status += " (pinned)"

    status += f"\n  Version:   {version}.{version_id}"
    status += f"\n  Build:     {build_id}"
    status += f"\n  Stateroot: {deployment.stateroot}"
    if deployment.unlocked and deployment.unlocked != "none":
        status += f"\n  Unlocked:  {deployment.unlocked}"

    return status


def command(_: Namespace):
    with ThreadPoolExecutor(max_workers=50) as exc:
        for status in exc.map(get_status, deployments()):
            print(status)


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
