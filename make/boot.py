import os
import subprocess
import sys
import tempfile
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

from . import (
    BUILDER,
    podman_cmd,
)
from .shell import shell

ISO_RUNNER_IMAGE = f"{BUILDER}:iso-runner"

kwds: dict[str, str] = {
    "help": "Boot an iso in qemu",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("iso", help="Path to the iso to boot")
    _ = parser.add_argument(
        "--graphical",
        action="store_true",
        help="Open a graphical window instead of the serial console",
    )


def qemu_args(iso: str, workspace: str, graphical: bool) -> list[str]:
    args = [
        f"--volume={iso}:/iso:ro",
        f"--volume={workspace}:/workspace",
        "--security-opt=label=disable",
    ]
    if os.path.exists("/dev/kvm"):
        args.append("--device=/dev/kvm")

    if graphical:
        display = os.environ.get("DISPLAY")
        if display:
            args.extend(
                [
                    "--volume=/tmp/.X11-unix:/tmp/.X11-unix",
                    f"--env=DISPLAY={display}",
                ]
            )

    return args


def extract_boot(iso: str, workspace: str) -> tuple[str, str, str]:
    data = subprocess.check_output(
        podman_cmd(
            "run",
            "--rm",
            f"--volume={iso}:/iso:ro",
            ISO_RUNNER_IMAGE,
            "isoinfo",
            "-R",
            "-i",
            "/iso",
            "-x",
            "/loader/entries/01-archiso-x86_64-linux.conf",
        )
    )
    for line in data.decode("utf-8").splitlines():
        for arg in line.split():
            if arg.startswith("archisosearchuuid="):
                value = arg.split("=", 1)[1]
                assert value
                return (
                    extract(iso, workspace, "/arkes/x86_64/vmlinuz"),
                    extract(iso, workspace, "/arkes/x86_64/initramfs.img"),
                    value,
                )

    raise RuntimeError("Unable to find archisosearchuuid in the iso boot entry")


def extract(iso: str, workspace: str, path: str) -> str:
    dest = os.path.join(workspace, os.path.basename(path))
    with open(dest, "wb") as f:
        _ = subprocess.run(
            podman_cmd(
                "run",
                "--rm",
                f"--volume={iso}:/iso:ro",
                ISO_RUNNER_IMAGE,
                "isoinfo",
                "-R",
                "-i",
                "/iso",
                "-x",
                path,
            ),
            stdout=f,
            check=True,
        )

    return f"/workspace/{os.path.basename(path)}"


def qemu_cmd(
    kernel: str,
    initrd: str,
    uuid: str,
    graphical: bool,
    monitor: bool,
) -> list[str]:
    kvm = os.path.exists("/dev/kvm")
    args = [
        "-machine",
        "q35",
        "-cpu",
        "host" if kvm else "max",
        "-accel",
        "kvm" if kvm else "tcg",
        "-m",
        "4096",
        "-smp",
        "2",
        "-audiodev",
        "none,id=noaudio",
        "-drive",
        "file=/iso,format=raw,media=cdrom,readonly=on",
        "-kernel",
        kernel,
        "-initrd",
        initrd,
        "-append",
        (
            "console=ttyS0,115200 "
            "archisobasedir=arkes "
            f"archisosearchuuid={uuid} "
            "copytoram=n cow_spacesize=2G"
        ),
    ]
    if graphical:
        args.extend(["-display", "sdl", "-vga", "std", "-serial", "none"])

    else:
        args.extend(["-nographic"])
        if not monitor:
            args.extend(["-monitor", "none"])

    return args


def command(args: Namespace) -> None:
    iso = os.path.abspath(cast(str, args.iso))
    if not os.path.exists(iso):
        print(f"iso not found: {iso}", file=sys.stderr)
        sys.exit(1)

    graphical = cast(bool, args.graphical)
    with tempfile.TemporaryDirectory(prefix="iso-runner-") as workspace:
        ret = shell(
            *podman_cmd(
                "run",
                "--rm",
                "-it",
                *qemu_args(iso, workspace, graphical),
                ISO_RUNNER_IMAGE,
                "qemu-system-x86_64",
                *qemu_cmd(*extract_boot(iso, workspace), graphical, True),
            )
        )

    if ret:
        sys.exit(ret)


if __name__ == "__main__":
    kwds["description"] = kwds["help"]
    del kwds["help"]
    parser = ArgumentParser(
        **cast(  # pyright: ignore[reportAny]
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            kwds,
        ),
    )
    register(parser)
    args = parser.parse_args()
    command(args)
