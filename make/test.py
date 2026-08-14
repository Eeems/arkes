import atexit
import os
import select
import shlex
import subprocess
import sys
import tempfile
import termios
import time
import traceback
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    IO,
    Any,
    NoReturn,
    cast,
)

from . import (
    BUILDER,
    bytes_to_stdout,
    podman,
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
    atexit.register(clear_stdin)
    with tempfile.TemporaryDirectory(prefix="iso-runner-", dir=data_dir) as workspace:
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

            if not check(
                proc,
                "printf 'g\\nn\\n\\n\\n+512M\\nt\\n\\n1\\nn\\n\\n\\n\\nw\\n' | sudo fdisk /dev/vda",
            ):
                print("boot-test: failed to partition /dev/vda", file=sys.stderr)
                error_exit(proc, cidfile)

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
                    UP_PID=$!
                    RC=1
                    while kill -0 $UP_PID 2>/dev/null; do
                        if systemd-inhibit --list --no-legend --no-pager | awk '/^os-daemon[[:space:]]/ {found=1} END {exit !found}';then
                            RC=0
                            break
                        fi
                        sleep 1
                    done
                    wait $UP_PID
                    exit $((RC + $?))
                )""",
            ):
                print(
                    "boot-test: os upgrade failed or did not hold inhibitor",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            send(proc, b"sudo systemctl reboot\n")
            if expect(proc, [b"reboot: Restarting system"]) is None:
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


def expect_prompt(
    proc: subprocess.Popen[bytes],
    *extras: bytes,
    timeout: float | None = None,
) -> bytes | None:
    return expect(proc, [*extras, b"~]$", b"~]#"], timeout)


def login(
    proc: subprocess.Popen[bytes],
    user: bytes = b"live",
    password: bytes = b"",
) -> bool:
    match expect_prompt(proc, b"login:", timeout=60):
        case b"~]$" | b"~]#":
            return True

        case b"login:":
            send(proc, user + b"\n")

        case _:
            print("boot-test: never reached a login prompt", file=sys.stderr)
            return False

    match expect_prompt(proc, b"Password:", timeout=60):
        case b"Password:":
            send(proc, password + b"\n")

        case b"~]$" | b"~]#":
            return True

        case _:
            print("boot-test: never reached the shell prompt", file=sys.stderr)
            return False

    if expect_prompt(proc, timeout=60) is None:
        print("boot-test: never reached the shell prompt", file=sys.stderr)
        return False

    return True


def send(proc: subprocess.Popen[bytes], data: bytes) -> None:
    stdin: IO[bytes] | None = proc.stdin
    if stdin is None:
        raise RuntimeError("stdin is None")

    _ = stdin.write(data)
    stdin.flush()


def read(proc: subprocess.Popen[bytes]) -> bytes:
    assert proc.stdout is not None
    data: bytes = proc.stdout.read(4096)
    if not data:
        return b""

    bytes_to_stdout(data)
    return data


def stop(proc: subprocess.Popen[bytes]) -> bool:
    assert proc.stdout is not None
    send(proc, b"sudo systemctl poweroff\n")
    while True:
        data: bytes = proc.stdout.read(4096)
        if not data:
            break

        bytes_to_stdout(data)

    return proc.wait() == 0


def clear_stdin() -> None:
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        return

    termios.tcflush(fd, termios.TCIFLUSH)


def error_exit(proc: subprocess.Popen[bytes], cidfile: str) -> NoReturn:
    try:
        with open(cidfile) as f:
            cid: str = f.read().strip()

    except OSError:
        cid = ""

    if cid:
        try:
            podman("kill", cid)
        except subprocess.CalledProcessError:
            pass

    proc.kill()
    _ = proc.wait()
    sys.exit(1)


def check(proc: subprocess.Popen[bytes], cmd: str) -> bool:
    send(proc, f"{cmd} 2>&1; echo __RC__=$?\n".encode())
    res = -1
    buffer = b""
    prompt = -1
    while res == -1:
        data: bytes = read(proc)
        if not data:
            if proc.poll() is not None:
                break

            continue

        buffer += data
        pos: int = buffer.find(b"__RC__=")
        while pos != -1:
            newline: int = buffer.find(b"\n", pos)
            if newline == -1:
                break

            value: bytes = buffer[pos + len(b"__RC__=") : newline].strip()
            if value.isdigit():
                res = int(value)
                prompt = newline + 1
                break

            pos = buffer.find(b"__RC__=", pos + len(b"__RC__="))

    if res == -1:
        print(f"boot-test: command did not return: {cmd}", file=sys.stderr)
        return False

    while True:
        for pattern in [b"~]$", b"~]#"]:
            if buffer.find(pattern, prompt) != -1:
                return res == 0

        data = read(proc)
        if not data:
            if proc.poll() is not None:
                break

            continue

        buffer += data

    print(f"boot-test: shell did not return after: {cmd}", file=sys.stderr)
    return False


def expect(
    proc: subprocess.Popen[bytes],
    patterns: list[bytes],
    timeout: float | None = None,
) -> bytes | None:
    assert proc.stdout is not None
    buffer = b""
    max_len: int = max(len(pattern) for pattern in patterns)
    deadline: float | None = None
    if timeout is not None:
        deadline = time.monotonic() + timeout

    while proc.poll() is None:
        if deadline is not None:
            remaining: float = deadline - time.monotonic()
            if remaining <= 0:
                return None

            readable, _, _ = select.select([proc.stdout.fileno()], [], [], remaining)
            if not readable:
                return None

        data: bytes = read(proc)
        if not data:
            continue

        buffer = (buffer + data)[-(max_len + len(data)) :]
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
