import io
import os
import shlex
import subprocess
import sys
import tempfile
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    IO,
    Any,
    cast,
)

from . import (
    BUILDER,
    bytes_to_stdout,
    execute,
    podman_cmd,
)
from .boot import (
    extract_boot,
    qemu_cmd,
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
    data_dir = os.path.join(
        os.environ.get("XDG_DATA_HOME")
        or os.path.join(os.path.expanduser("~"), ".local", "share"),
        "iso-runner-tmp",
    )
    os.makedirs(data_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="iso-runner-", dir=data_dir) as workspace:
        pod_args: list[str] = [
            f"--volume={workspace}:/workspace",
            "--security-opt=label=disable",
        ]
        if os.path.exists("/dev/kvm"):
            pod_args.append("--device=/dev/kvm")

        execute(
            podman_cmd(
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
            ),
        )
        kernel, initrd, uuid = extract_boot(iso, workspace, branch)
        disk: str = "/workspace/disk.qcow2"

        # Phase 1: boot the iso, validate, install to the target disk.
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            podman_cmd(
                "run",
                "--rm",
                "-i",
                *pod_args,
                f"--volume={iso}:/iso:ro",
                image,
                "qemu-system-x86_64",
                *qemu_cmd(kernel, initrd, uuid, False, False, disk=disk, uefi=False),
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if not login(proc):
            print("boot-test: live iso never reached a shell", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not check(proc, "os validate --verbose"):
            print("boot-test: live iso failed os validate", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not check(
            proc,
            "printf 'g\\nn\\n\\n\\n+512M\\nt\\n\\n1\\nn\\n\\n\\n\\nw\\n' | sudo fdisk /dev/vda",
        ):
            print("boot-test: failed to partition /dev/vda", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not check(
            proc,
            shlex.join(
                [
                    "sudo",
                    "os",
                    "install",
                    "--system-partition=/dev/vda2",
                    "--boot-partition=/dev/vda1",
                    "--format-partitions",
                    "--password=live",
                    "--kernel-commandline=console=ttyS0,115200",
                ]
            ),
        ):
            print("boot-test: os install failed", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not stop(proc):
            print("boot-test: phase 1 shutdown failed", file=sys.stderr)
            sys.exit(1)

        # Phase 2: boot the installed disk (uefi, no iso) and validate.
        proc = subprocess.Popen(
            podman_cmd(
                "run",
                "--rm",
                "-i",
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
        )
        if not login(proc, b"root", b"live"):
            print("boot-test: installed system never reached a shell", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not check(proc, "os validate --verbose"):
            print("boot-test: installed system failed os validate", file=sys.stderr)
            _ = stop(proc)
            sys.exit(1)

        if not stop(proc):
            print("boot-test: phase 2 shutdown failed", file=sys.stderr)
            sys.exit(1)

    print("boot-test: validation passed", file=sys.stderr)


def login(
    proc: subprocess.Popen[bytes],
    user: bytes = b"live",
    password: bytes = b"",
) -> bool:
    match expect(proc, [b"login:", b"~]$", b"~]#"]):
        case b"~]$" | b"~]#":
            return True

        case b"login:":
            send(proc, user + b"\n")

        case _:
            print("boot-test: never reached a login prompt", file=sys.stderr)
            return False

    match expect(proc, [b"Password:", b"~]$", b"~]#"]):
        case b"Password:":
            send(proc, password + b"\n")

        case b"~]$" | b"~]#":
            return True

        case _:
            print("boot-test: never reached the shell prompt", file=sys.stderr)
            return False

    if expect(proc, [b"~]$", b"~]#"]) is None:
        print("boot-test: never reached the shell prompt", file=sys.stderr)
        return False

    return True


def send(proc: subprocess.Popen[bytes], data: bytes) -> None:
    stdin: IO[bytes] | None = proc.stdin
    if stdin is None:
        raise RuntimeError("stdin is None")

    _ = stdin.write(data)
    stdin.flush()


def stop(proc: subprocess.Popen[bytes]) -> bool:
    assert proc.stdout is not None
    stdout = cast(io.BufferedReader, proc.stdout)
    send(proc, b"sudo systemctl poweroff\n")
    while True:
        data: bytes = stdout.read1(4096)
        if not data:
            break

        bytes_to_stdout(data)

    return proc.wait() == 0


def check(proc: subprocess.Popen[bytes], cmd: str) -> bool:
    assert proc.stdout is not None
    stdout = cast(io.BufferedReader, proc.stdout)
    send(proc, f"{cmd} 2>&1; echo __RC__=$?\n".encode())
    res: int = -1
    buffer: bytes = b""
    while res == -1:
        data: bytes = stdout.read1(4096)
        if not data:
            if proc.poll() is not None:
                break

            continue

        buffer = (buffer + data)[-(len(b"__RC__=") + 32) :]
        bytes_to_stdout(data)
        pos: int = buffer.find(b"__RC__=")
        while pos != -1:
            newline: int = buffer.find(b"\n", pos)
            if newline == -1:
                break

            value: bytes = buffer[pos + len(b"__RC__=") : newline].strip()
            if value.isdigit():
                res = int(value)
                break

            pos = buffer.find(b"__RC__=", pos + len(b"__RC__="))

    if res == -1:
        print(f"boot-test: command did not return: {cmd}", file=sys.stderr)
        return False

    return res == 0


def expect(proc: subprocess.Popen[bytes], patterns: list[bytes]) -> bytes | None:
    buffer: bytes = b""
    max_len: int = max(len(pattern) for pattern in patterns)
    assert proc.stdout is not None
    stdout = cast(io.BufferedReader, proc.stdout)
    while proc.poll() is None:
        data: bytes = stdout.read1(4096)
        if not data:
            continue

        buffer = (buffer + data)[-(max_len + len(data)) :]
        bytes_to_stdout(data)
        for pattern in patterns:
            if pattern in buffer:
                return pattern

    return None


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
