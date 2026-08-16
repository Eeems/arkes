import atexit
import os
import shlex
import subprocess
import sys
import tempfile
import traceback
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
    podman,
    podman_cmd,
)
from .boot import (
    check,
    clear_stdin,
    error_exit,
    expect,
    extract_boot,
    install,
    login,
    partition_disk,
    qemu_cmd,
    send,
    stop,
    workspace_path,
)
from .ref import ref

kwds: dict[str, str] = {
    "help": "Boot an iso in qemu and run validation against it",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("iso", help="Path to the iso to boot")
    _ = parser.add_argument(
        "--branch",
        default="iso-runner",
        help="iso-runner image ref to use, defaults to iso-runner.",
    )


def command(args: Namespace) -> None:
    iso: str = os.path.abspath(cast(str, args.iso))
    if not os.path.exists(iso):
        print(f"iso not found: {iso}", file=sys.stderr)
        sys.exit(1)

    branch: str = ref(cast(str, args.branch))
    image: str = f"{BUILDER}:{branch}"
    _ = atexit.register(clear_stdin)
    with tempfile.TemporaryDirectory(
        prefix="iso-runner-", dir=workspace_path()
    ) as workspace:
        pod_args: list[str] = [
            f"--volume={workspace}:/workspace",
            "--security-opt=label=disable",
        ]
        if os.path.exists("/dev/kvm"):
            pod_args.append("--device=/dev/kvm")

        podman(
            "run",
            "--rm",
            *pod_args,
            image,
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            "/workspace/disk.qcow2",
            "32G",
        )
        kernel, initrd, uuid = extract_boot(iso, workspace, branch)
        disk: str = "/workspace/disk.qcow2"

        # Phase 1: boot the iso, validate, install to the target disk.
        cidfile: str = os.path.join(workspace, "phase1.cid")
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            podman_cmd(
                "run",
                "--rm",
                "-i",
                "--cidfile",
                cidfile,
                *pod_args,
                f"--volume={iso}:/iso:ro",
                image,
                "qemu-system-x86_64",
                *qemu_cmd(kernel, initrd, uuid, False, False, disk=disk, uefi=False),
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        try:
            if not login(proc):
                print("boot-test: live iso never reached a shell", file=sys.stderr)
                error_exit(proc, cidfile)

            if not check(proc, "os validate --verbose"):
                print("boot-test: live iso failed os validate", file=sys.stderr)
                error_exit(proc, cidfile)

            if not partition_disk(proc):
                print("boot-test: failed to partition /dev/vda", file=sys.stderr)
                error_exit(proc, cidfile)

            if not install(proc, False):
                print("boot-test: os install failed", file=sys.stderr)
                error_exit(proc, cidfile)

            if not stop(proc):
                print("boot-test: phase 1 shutdown failed", file=sys.stderr)
                error_exit(proc, cidfile)

        except KeyboardInterrupt, Exception:
            traceback.print_exc()
            error_exit(proc, cidfile)

        # Phase 2: boot the installed disk (uefi, no iso) and validate.
        cidfile = os.path.join(workspace, "phase2.cid")
        proc = subprocess.Popen(
            podman_cmd(
                "run",
                "--rm",
                "-i",
                "--cidfile",
                cidfile,
                *pod_args,
                image,
                "bash",
                "-c",
                shlex.join(
                    [
                        "cp",
                        "/usr/share/OVMF/OVMF_VARS_4M.fd",
                        "/workspace/OVMF_VARS_4M.fd",
                    ]
                )
                + " && exec qemu-system-x86_64 "
                + shlex.join(
                    qemu_cmd(None, None, None, False, False, disk=disk, uefi=True)
                ),
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        try:
            if not login(proc, b"root", b"live"):
                print(
                    "boot-test: installed system never reached a shell",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            if not check(proc, "os validate --verbose"):
                print(
                    "boot-test: installed system failed os validate",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            # Run the upgrade in the background while verifying that the
            # os-daemon holds a logind inhibitor lock for its duration.
            if not check(
                proc,
                """(
                  os upgrade --no-pull &
                  pid=$!
                  found=0
                  while kill -0 $pid 2>/dev/null; do
                    if systemd-inhibit --list --no-legend --no-pager |
                      awk '/^os-daemon[[:space:]]/ {found=1} END {exit !found}'; then
                      found=1
                      break
                    fi
                    sleep 1
                  done
                  if [ $found -eq 0 ]; then
                    echo "No inhibitor was created" >&2
                    exit 1
                  fi
                  wait $pid
                  rc=$?
                  if [ $rc -eq 0 ] && ! systemd-inhibit --list --no-legend --no-pager |
                    awk '/^os-daemon[[:space:]]/ {found=1} END {exit found}'; then
                    echo "Inhibitor was not released" >&2
                    exit 1
                  fi
                  exit $rc
                )""",
            ):
                print(
                    "boot-test: os upgrade failed or inhibitor not held/released",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            send(proc, b"sudo systemctl reboot\n")
            match = expect(
                proc,
                [
                    b"reboot: Restarting system",
                    b"Operation inhibited",
                ],
            )
            if match != b"reboot: Restarting system":
                print("boot-test: reboot never started", file=sys.stderr)
                error_exit(proc, cidfile)

            if not login(proc, b"root", b"live"):
                print(
                    "boot-test: upgraded system never reached a shell",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            if not check(proc, "os validate --verbose"):
                print(
                    "boot-test: upgraded system failed os validate",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            if not check(
                proc,
                """os status --json | python -c '
                import json
                import sys
                if len(json.load(sys.stdin)) != 2:
                    sys.exit(1)
                '""",
            ):
                print(
                    "boot-test: upgrade did not create two deployments",
                    file=sys.stderr,
                )
                _ = check(proc, "os status")
                error_exit(proc, cidfile)

            if not stop(proc):
                print("boot-test: phase 2 shutdown failed", file=sys.stderr)
                error_exit(proc, cidfile)

        except KeyboardInterrupt, Exception:
            traceback.print_exc()
            error_exit(proc, cidfile)

    print("boot-test: validation passed", file=sys.stderr)


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
