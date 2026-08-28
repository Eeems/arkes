import atexit
import contextlib
import json
import os
import pty
import shlex
import shutil
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
    IMAGE,
    OS_NAME,
    REGISTRY,
    REPO,
    _execute,  # pyright: ignore[reportPrivateUsage]
    _osDir,  # pyright: ignore[reportPrivateUsage]
    bytes_to_stderr,
    bytes_to_stdout,
    chronic,
    execute_pipe,
    image_qualified_name,
)
from .boot import (
    expect_prompt,
    run,
)

kwds: dict[str, str] = {
    "help": "Check the codebase and ensure it follows standards",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply any automatic fixes that can be applied",
    )
    _ = parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show output when a check fails",
    )


def command(args: Namespace) -> None:
    failed = False
    fix = cast(bool, args.fix)
    quiet = cast(bool, args.quiet)

    if quiet:
        current_stdout = sys.stdout
        current_stderr = sys.stderr
        saved_out_fd = os.dup(1)
        saved_err_fd = os.dup(2)
        cap = tempfile.TemporaryFile()  # noqa: SIM115  (closed in atexit)
        _ = os.dup2(cap.fileno(), 1)
        _ = os.dup2(cap.fileno(), 2)
        sys.stdout = os.fdopen(os.dup(cap.fileno()), "w")
        sys.stderr = os.fdopen(os.dup(cap.fileno()), "w")

        def _restore() -> None:
            _ = sys.stdout.flush()
            _ = sys.stderr.flush()
            _ = os.dup2(saved_out_fd, 1)
            _ = os.dup2(saved_err_fd, 2)
            os.close(saved_out_fd)
            os.close(saved_err_fd)
            sys.stdout = current_stdout
            sys.stderr = current_stderr
            if failed:
                _ = cap.seek(0)
                data = cap.read()
                if data:
                    _ = os.write(2, data)

            cap.close()

        _ = atexit.register(_restore)

    def _assert_name(name: str, expected: str) -> bool:
        image = image_qualified_name(name)
        if image == expected:
            return True

        print(f" Failed: image_qualified_name({json.dumps(name)})")
        print(f"  Expected: {json.dumps(expected)}")
        print(f"  Actual: {json.dumps(image)}")
        return False

    def _assert_run(cmd: str, expected: bytes) -> bool:
        env = os.environ.copy()
        env["PS1"] = "[test@host ~]# "
        env["TERM"] = "dumb"
        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            ["bash", "--norc", "--noprofile", "-i"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            preexec_fn=os.setsid,  # noqa: PLW1509
            env=env,
        )
        os.close(slave_fd)
        proc.stdout = os.fdopen(master_fd, "rb", 0)
        proc.stdin = os.fdopen(os.dup(master_fd), "wb", 0)
        try:
            with contextlib.redirect_stdout(open(os.devnull, "w")):
                if expect_prompt(proc, timeout=2) is None:
                    return False

                result = run(proc, cmd, timeout=2)
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.kill()
            _ = proc.wait()

        if result == expected:
            return True

        print(f" Failed: run({json.dumps(cmd)})")
        print(f"  Expected: {expected!r}")
        print(f"  Actual:   {result!r}")
        return False

    print("[check] Running tests")
    failed = failed or not _assert_name(
        "hello-world:latest@sha256:123",
        "docker.io/hello-world@sha256:123",
    )
    failed = failed or not _assert_name(
        "hello-world@sha256:123",
        "docker.io/hello-world@sha256:123",
    )
    failed = failed or not _assert_name(
        "hello-world:latest",
        "docker.io/hello-world:latest",
    )
    failed = failed or not _assert_name("hello-world", "docker.io/hello-world")
    failed = failed or not _assert_name("system:latest", "localhost/system:latest")
    failed = failed or not _assert_name(
        f"{REPO}:latest@sha256:123",
        f"{REPO}@sha256:123",
    )
    failed = failed or not _assert_name(f"{REPO}:latest", f"{REPO}:latest")
    failed = failed or not _assert_name(f"{REPO}@sha256:123", f"{REPO}@sha256:123")
    failed = failed or not _assert_name(REPO, REPO)
    failed = failed or not _assert_name(
        f"{IMAGE}:latest@sha256:123",
        f"{REPO}@sha256:123",
    )
    failed = failed or not _assert_name(f"{IMAGE}:latest", f"{REPO}:latest")
    failed = failed or not _assert_name(IMAGE, REPO)
    failed = failed or not _assert_name(OS_NAME, REPO)
    failed = failed or not _assert_name(f"{REGISTRY}/{IMAGE}", REPO)
    failed = failed or not _assert_name(
        f"other.example/{OS_NAME}",
        f"other.example/{OS_NAME}",
    )
    failed = failed or not _assert_run("echo hello", b"hello\r\n")
    failed = failed or not _assert_run("printf 'a\\nb'", b"a\r\nb")
    failed = failed or not _assert_run("printf '\\033[32mhello\\033[0m'", b"hello")
    failed = failed or not _assert_run(
        "printf '\\033[?2004larkes\\033[?2004h'", b"arkes"
    )
    failed = failed or not _assert_run("echo -n hello", b"hello")
    failed = failed or not _assert_run("printf 'hello\\rX'", b"hello\rX")
    if failed:
        sys.exit(1)

    if shutil.which("niri") is not None:
        print("[check] Checking niri config", file=sys.stderr)
        cmd = shlex.join(
            [
                "niri",
                "validate",
                "--config=overlay/atomic/usr/share/niri/config.kdl",
            ]
        )
        res = _execute(cmd)
        if res:
            print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
            failed = True

    if shutil.which("gofmt") is not None:
        print("[check] Checking go formatting", file=sys.stderr)
        cmd = [
            "gofmt",
            "-e",
            *(["-w"] if fix else ["-d"]),
            "tools/dockerfile2llbjson",
        ]
        gofmt_failed = False

        def _onstderr(data: bytes) -> None:
            nonlocal gofmt_failed
            gofmt_failed = True
            bytes_to_stderr(data)

        def _onstdout(data: bytes) -> None:
            nonlocal gofmt_failed
            gofmt_failed = True
            bytes_to_stdout(data)

        res = execute_pipe(*cmd, onstderr=_onstderr, onstdout=_onstdout)
        if res or gofmt_failed:
            print(
                f"[check] Failed: {shlex.join(cmd)}\nStatus code: {res}",
                file=sys.stderr,
            )
            failed = True

    if shutil.which("go") is not None:
        cwd = os.getcwd()
        print("[check] Analyzing go code", file=sys.stderr)
        cmds: list[list[str]] = [["go", "vet"]]
        if fix:
            cmds.insert(0, ["go", "mod", "tidy"])

        for cmd in cmds:
            command = shlex.join(cmd)
            os.chdir("tools/dockerfile2llbjson")
            res = _execute(command)
            os.chdir(cwd)
            if res:
                print(
                    f"[check] Failed: {command}\nStatus code: {res}",
                    file=sys.stderr,
                )
                failed = True

    if shutil.which("actionlint") is not None:
        print("[check] Checking github actions", file=sys.stderr)
        cmd = shlex.join(["actionlint"])
        res = _execute(cmd)
        if res:
            print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
            failed = True

    if shutil.which("shfmt") is not None:
        print("[check] Checking bash formatting", file=sys.stderr)
        bash_files: list[str] = []
        for root, _, files in os.walk("overlay"):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue

                with open(path, "rb") as file:
                    shebang = file.readline().strip()

                if not shebang.startswith(b"#!"):
                    continue

                interpreter_args: list[bytes] = shebang[2:].split()
                if not interpreter_args:
                    continue

                interpreter = os.path.basename(interpreter_args[0])
                if interpreter == b"env":
                    for arg in interpreter_args[1:]:
                        if arg.startswith(b"-"):
                            continue

                        interpreter = os.path.basename(arg)
                        break

                if interpreter not in (b"bash", b"sh", b"mksh", b"bats"):
                    continue

                bash_files.append(path)

        if bash_files:
            cmd = ["shfmt", "-i=2"] + (["-w"] if fix else ["-d"]) + bash_files
            shfmt_failed = False

            def _onstderr(data: bytes) -> None:
                nonlocal shfmt_failed
                shfmt_failed = True
                bytes_to_stderr(data)

            def _onstdout(data: bytes) -> None:
                nonlocal shfmt_failed
                shfmt_failed = True
                bytes_to_stdout(data)

            res = execute_pipe(*cmd, onstderr=_onstderr, onstdout=_onstdout)
            if res or shfmt_failed:
                print(
                    f"[check] Failed: {shlex.join(cmd)}\nStatus code: {res}",
                    file=sys.stderr,
                )
                failed = True

    print("[check] Setting up venv", file=sys.stderr)
    if not os.path.exists(".venv/bin/activate"):
        chronic("python", "-m", "venv", "--system-site-packages", ".venv")

    chronic(
        "bash",
        "-ec",
        ";".join(
            [
                "source .venv/bin/activate",
                "python -m ensurepip",
                "pip install "
                + " ".join(
                    [
                        "ruff",
                        "basedpyright",
                        "requests",
                        "dbus-python",
                        "PyGObject",
                        "xattr",
                        "podman",
                        "progressbar2",
                    ]
                ),
            ]
        ),
    )
    cmd = shlex.join(
        [
            "bash",
            "-ec",
            ";".join(
                [
                    "source .venv/bin/activate",
                    f"ruff check {'--fix' if fix else ''} .",
                ]
            ),
        ]
    )
    print("[check] Checking python formatting", file=sys.stderr)
    res = _execute(cmd)
    if res:
        print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
        failed = True

    cmd = shlex.join(
        [
            "bash",
            "-ec",
            ";".join(
                [
                    "source .venv/bin/activate",
                    shlex.join(
                        [
                            "basedpyright",
                            "--pythonversion=3.14",
                            "--pythonplatform=Linux",
                            "--venvpath=.venv",
                            "make.py",
                            f"{_osDir}",
                        ]
                    ),
                ]
            ),
        ]
    )
    print("[check] Checking python types", file=sys.stderr)
    res = _execute(cmd)
    if res:
        print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
        failed = True

    print("[check] Checking variants diagram", file=sys.stderr)
    cmd = shlex.join(["python", "make.py", "variants-diagram", "--check"])
    res = _execute(cmd)
    if res == 2:
        print("Variants diagram is out of date", file=sys.stderr)
        if fix:
            print("Updating variants diagram...", file=sys.stderr)
            cmd = shlex.join(["python", "make.py", "variants-diagram", "--update"])
            res = _execute(cmd)
            if res:
                print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
                failed = True
        else:
            failed = True
    elif res:
        print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
        failed = True

    print("[check] Checking workflow", file=sys.stderr)
    cmd = shlex.join(["python", "make.py", "workflow", "--check"])
    res = _execute(cmd)
    if res == 2:
        print("Workflow is out of date", file=sys.stderr)
        if fix:
            print("Updating workflow...", file=sys.stderr)
            cmd = shlex.join(["python", "make.py", "workflow"])
            res = _execute(cmd)
            if res:
                print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
                failed = True
        else:
            failed = True
    elif res:
        print(f"[check] Failed: {cmd}\nStatus code: {res}", file=sys.stderr)
        failed = True

    if failed:
        print("[check] One or more checks failed", file=sys.stderr)
        sys.exit(1)

    print("[check] All checks passed", file=sys.stderr)


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
