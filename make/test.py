import os
import select
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
    bytes_to_stderr,
    bytes_to_stdout,
    podman_cmd,
)
from .boot import (
    extract_boot,
    qemu_args,
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
    iso: str = cast(str, args.iso)
    if not os.path.exists(iso):
        print(f"iso not found: {iso}", file=sys.stderr)
        sys.exit(1)

    branch: str = ref(cast(str, args.branch))
    with tempfile.TemporaryDirectory(prefix="iso-runner-") as workspace:
        cmd: list[str] = podman_cmd(
            "run",
            "--rm",
            "-i",
            *qemu_args(iso, workspace, False),
            f"{BUILDER}:{branch}",
            "qemu-system-x86_64",
            *qemu_cmd(*extract_boot(iso, workspace, branch), False, False),
        )
        proc: subprocess.Popen[bytes] = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not login(proc):
            print("boot-test: validation failed", file=sys.stderr)
            stop(proc)
            sys.exit(1)

        if not check(proc, "os validate"):
            print("boot-test: validation failed", file=sys.stderr)
            stop(proc)
            sys.exit(1)

        stop(proc)

    print("boot-test: validation passed", file=sys.stderr)


def login(proc: subprocess.Popen[bytes]) -> bool:
    match expect(proc, [b"login:", b"~]$"]):
        case b"~]$":
            return True

        case b"login:":
            send(proc, b"live\n")

        case _:
            print("boot-test: never reached a login prompt", file=sys.stderr)
            return False

    match expect(proc, [b"Password:", b"~]$"]):
        case b"Password:":
            send(proc, b"\n")

        case b"~]$":
            return True

        case _:
            print("boot-test: never reached the shell prompt", file=sys.stderr)
            return False

    if expect(proc, [b"~]$"]) is None:
        print("boot-test: never reached the shell prompt", file=sys.stderr)
        return False

    return True


def send(proc: subprocess.Popen[bytes], data: bytes) -> None:
    stdin: IO[bytes] | None = proc.stdin
    if stdin is None:
        raise RuntimeError("stdin is None")

    _ = stdin.write(data)
    stdin.flush()


def stop(proc: subprocess.Popen[bytes]) -> None:
    assert proc.stdout is not None
    assert proc.stderr is not None
    send(proc, b"sudo systemctl poweroff\n")
    while proc.poll() is None:
        r, _, _ = select.select([proc.stdout, proc.stderr], [], [])
        if proc.stdout in r:
            data: bytes = os.read(proc.stdout.fileno(), 4096)
            if data:
                bytes_to_stdout(data)

        if proc.stderr in r:
            data = os.read(proc.stderr.fileno(), 4096)
            if data:
                bytes_to_stderr(data)


def check(proc: subprocess.Popen[bytes], cmd: str) -> bool:
    assert proc.stdout is not None
    assert proc.stderr is not None
    send(proc, f"{cmd} 2>&1; echo __RC__=$?\n".encode())
    res: int = -1
    buffer: bytes = b""
    while res == -1:
        r, _, _ = select.select([proc.stdout, proc.stderr], [], [])
        if proc.stdout in r:
            data = os.read(proc.stdout.fileno(), 4096)
            if not data:
                if proc.poll() is not None:
                    break

                continue

            buffer += data
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

        if proc.stderr in r:
            data = os.read(proc.stderr.fileno(), 4096)
            if data:
                bytes_to_stderr(data)

    if res == -1:
        print(f"boot-test: command did not return: {cmd}", file=sys.stderr)
        return False

    return res == 0


def expect(proc: subprocess.Popen[bytes], patterns: list[bytes]) -> bytes | None:
    buffer: bytes = b""
    assert proc.stdout is not None
    assert proc.stderr is not None
    while proc.poll() is None:
        r, _, _ = select.select([proc.stdout, proc.stderr], [], [])
        if proc.stdout in r:
            data = os.read(proc.stdout.fileno(), 4096)
            if not data:
                continue

            buffer += data
            bytes_to_stdout(data)
            for pattern in patterns:
                if pattern in buffer:
                    return pattern

        if proc.stderr in r:
            data = os.read(proc.stderr.fileno(), 4096)
            if not data:
                continue

            bytes_to_stderr(data)

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
