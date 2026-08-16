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
from .ref import ref
from .shell import shell

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
    _ = parser.add_argument(
        "--install",
        action="store_true",
        help="Install the iso to a disk first, then drop into the installed system console",
    )
    _ = parser.add_argument(
        "--branch",
        default="iso-runner",
        help="iso-runner image ref to use, defaults to iso-runner.",
    )


def qemu_args(iso: str, workspace: str, graphical: bool) -> list[str]:
    args: list[str] = [
        f"--volume={iso}:/iso:ro",
        f"--volume={workspace}:/workspace",
        "--security-opt=label=disable",
    ]
    if os.path.exists("/dev/kvm"):
        args.append("--device=/dev/kvm")

    if not graphical:
        return args

    args.extend(graphical_args())
    return args


def graphical_args() -> list[str]:
    args: list[str] = []
    runtime_dir: str | None = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and os.path.isdir(runtime_dir):
        args.extend([f"--volume={runtime_dir}:{runtime_dir}"])

    args.extend(
        [
            "--volume=/tmp/.X11-unix:/tmp/.X11-unix",
            "--env=DISPLAY",
            "--env=XDG_RUNTIME_DIR",
            "--env=WAYLAND_DISPLAY",
        ]
    )
    return args


def extract_boot(iso: str, workspace: str, branch: str) -> tuple[str, str, str]:
    data: bytes = subprocess.check_output(
        podman_cmd(
            "run",
            "--rm",
            f"--volume={iso}:/iso:ro",
            f"{BUILDER}:{branch}",
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
                value: str = arg.split("=", 1)[1]
                assert value
                return (
                    extract(iso, workspace, "/arkes/x86_64/vmlinuz", branch),
                    extract(iso, workspace, "/arkes/x86_64/initramfs.img", branch),
                    value,
                )

    raise RuntimeError("Unable to find archisosearchuuid in the iso boot entry")


def extract(iso: str, workspace: str, path: str, branch: str) -> str:
    dest: str = os.path.join(workspace, os.path.basename(path))
    with open(dest, "wb") as f:
        _ = subprocess.run(
            podman_cmd(
                "run",
                "--rm",
                f"--volume={iso}:/iso:ro",
                f"{BUILDER}:{branch}",
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
    kernel: str | None,
    initrd: str | None,
    uuid: str | None,
    graphical: bool,
    monitor: bool,
    *,
    disk: str | None = None,
    uefi: bool = False,
) -> list[str]:
    kvm: bool = os.path.exists("/dev/kvm")
    args: list[str] = [
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
    ]
    if uefi:
        args.extend(
            [
                "-drive",
                "if=pflash,index=0,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd",
                "-drive",
                "if=pflash,index=1,format=raw,file=/workspace/OVMF_VARS_4M.fd",
            ]
        )

    if disk is not None:
        args.extend(["-drive", f"file={disk},if=virtio,format=qcow2"])

    if kernel is not None and initrd is not None and uuid is not None:
        args.extend(
            [
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
        )

    if graphical:
        args.extend(["-display", "sdl", "-vga", "std", "-serial", "none"])

    else:
        args.extend(["-nographic"])
        if not monitor:
            args.extend(["-monitor", "none"])

    return args


def workspace_path() -> str:
    data_dir = os.path.join(
        os.environ.get("XDG_DATA_HOME")
        or os.path.join(os.path.expanduser("~"), ".local", "share"),
        "iso-runner-tmp",
    )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def command(args: Namespace) -> None:
    iso: str = os.path.abspath(cast(str, args.iso))
    if not os.path.exists(iso):
        print(f"iso not found: {iso}", file=sys.stderr)
        sys.exit(1)

    graphical: bool = cast(bool, args.graphical)
    branch: str = ref(cast(str, args.branch))
    with tempfile.TemporaryDirectory(
        prefix="iso-runner-", dir=workspace_path()
    ) as workspace:
        image: str = f"{BUILDER}:{branch}"
        kernel, initrd, uuid = extract_boot(iso, workspace, branch)
        if not cast(bool, args.install):
            res = shell(
                *podman_cmd(
                    "run",
                    "--rm",
                    "-it",
                    *qemu_args(iso, workspace, graphical),
                    image,
                    "qemu-system-x86_64",
                    *qemu_cmd(kernel, initrd, uuid, graphical, True),
                )
            )
            if res:
                sys.exit(res)

            return

        _ = atexit.register(clear_stdin)
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
        disk: str = "/workspace/disk.qcow2"

        # Phase 1: boot the iso and install to the target disk.
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
                print("boot: live iso never reached a shell", file=sys.stderr)
                error_exit(proc, cidfile)

            if not partition_disk(proc):
                print("boot: failed to partition /dev/vda", file=sys.stderr)
                error_exit(proc, cidfile)

            if not install(proc):
                print("boot: os install failed", file=sys.stderr)
                error_exit(proc, cidfile)

            if not stop(proc):
                print("boot: install shutdown failed", file=sys.stderr)
                error_exit(proc, cidfile)

        except KeyboardInterrupt, Exception:
            traceback.print_exc()
            error_exit(proc, cidfile)

        clear_stdin()
        if graphical:
            pod_args.extend(graphical_args())

        res = shell(
            *podman_cmd(
                "run",
                "--rm",
                "-it",
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
                    qemu_cmd(None, None, None, graphical, True, disk=disk, uefi=True)
                ),
            ),
        )
        if res:
            sys.exit(res)


def partition_disk(proc: subprocess.Popen[bytes]) -> bool:
    return check(
        proc,
        "printf 'g\\nn\\n\\n\\n+512M\\nt\\n\\n1\\nn\\n\\n\\n\\nw\\n' | sudo fdisk /dev/vda",
    )


def install(proc: subprocess.Popen[bytes]) -> bool:
    return check(
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
    )


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
            return False

    match expect_prompt(proc, b"Password:", timeout=60):
        case b"Password:":
            send(proc, password + b"\n")

        case b"~]$" | b"~]#":
            return True

        case _:
            return False

    return expect_prompt(proc, timeout=60) is not None


def send(proc: subprocess.Popen[bytes], data: bytes) -> None:
    stdin: IO[bytes] | None = proc.stdin
    if stdin is None:
        raise RuntimeError("stdin is None")

    _ = stdin.write(data)
    stdin.flush()


def read(proc: subprocess.Popen[bytes]) -> bytes:
    assert proc.stdout is not None
    data = cast(IO[bytes], proc.stdout).read(4096)
    if not data:
        return b""

    bytes_to_stdout(data)
    return data


def stop(proc: subprocess.Popen[bytes]) -> bool:
    assert proc.stdout is not None
    send(proc, b"sudo systemctl poweroff\n")
    while True:
        data = cast(IO[bytes], proc.stdout).read(4096)
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
