# pyright: reportImportCycles=false
import json
import os
import shlex
import subprocess
from collections.abc import (
    Callable,
    Generator,
)
from datetime import datetime
from typing import cast

import gi

from . import OS_NAME, ROOTFS_PATH, SYSTEM_PATH
from .console import bytes_to_stderr, bytes_to_stdout
from .system import (
    _execute,  # pyright:ignore [reportPrivateUsage]
    execute,
)

gi.require_version("OSTree", "1.0")
from gi.repository import (  # pyright: ignore[reportMissingTypeStubs]
    OSTree,  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
)

RETAIN = 5


def ostree_cmd(*args: str) -> list[str]:
    return ["ostree", f"--repo={getattr(ostree, 'repo')}", *args]


def ostree(
    *args: str,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    execute(*ostree_cmd(*args), onstdout=onstdout, onstderr=onstderr)


setattr(ostree, "repo", "/ostree/repo")


def commit(
    branch: str = "system",
    rootfs: str | None = None,
    skipList: list[str] | None = None,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    if rootfs is None:
        rootfs = ROOTFS_PATH

    if skipList is None:
        skipList = []

    skipList.append("/etc")
    for name in os.listdir(os.path.join(rootfs, "var")):
        skipList.append(f"/var/{name}")

    _skipList = os.path.join(SYSTEM_PATH, "skiplist")
    with open(_skipList, "w") as f:
        _ = f.write("\n".join(skipList))

    ostree(
        "commit",
        "--generate-composefs-metadata",
        "--generate-sizes",
        f"--branch={OS_NAME}/{branch}",
        f"--subject={datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}",
        f"--tree=dir={rootfs}",
        f"--skip-list={_skipList}",
        onstdout=onstdout,
        onstderr=onstderr,
    )
    os.unlink(_skipList)


def commit_export(
    branch: str = "system",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    from .ostree import ostree_cmd  # noqa: PLC0415
    from .podman import export_stream  # noqa: PLC0415

    with export_stream(
        setup="""
        rm -f /etc
        rm -rf /var/*
        find / -xdev \\
          \\( \\
            -path /dev \\
            -o -path /proc \\
            -o -path /sys \\
            -o -path /run \\
            -o -path /tmp \\
          \\) -prune -o -print0 \\
        | xargs -0 -r -P$(nproc) -n500 touch -h -d "@1735689640"
        """,
        workingDir=SYSTEM_PATH,
        onstdout=onstdout,
        onstderr=onstderr,
    ) as stdout:
        cmd = ostree_cmd(
            "commit",
            "--generate-composefs-metadata",
            "--generate-sizes",
            f"--branch={OS_NAME}/{branch}",
            f"--subject={datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}",
            "--tree=tar=-",
            "--tar-pathname-filter=^,./",
            "--tar-autocreate-parents",
        )
        env = os.environ.copy()
        env["SOURCE_DATE_EPOCH"] = "0"
        ostree_proc = subprocess.Popen(cmd, stdin=stdout, env=env)
        ostree_out, ostree_err = ostree_proc.communicate()
        if ostree_out is not None:  # pyright: ignore[reportUnnecessaryComparison]
            onstdout(ostree_out)

        if ostree_err is not None:  # pyright: ignore[reportUnnecessaryComparison]
            onstderr(ostree_err)

        if ostree_proc.returncode:
            raise subprocess.CalledProcessError(
                ostree_proc.returncode, cmd, ostree_out, ostree_err
            )


def deploy(
    branch: str = "system",
    sysroot: str = "/",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,  # pyright:ignore [reportUnusedParameter]
    onstderr: Callable[[bytes], None] = bytes_to_stderr,  # pyright:ignore [reportUnusedParameter]
) -> None:
    kargs = ["--karg=root=LABEL=SYS_ROOT", "--karg=rw"]
    revision = f"{OS_NAME}/{branch}"
    if b"/usr/etc/system/commandline" in subprocess.check_output(
        ostree_cmd("ls", revision, "/usr/etc/system")
    ):
        kernelCommandline = (
            subprocess.check_output(
                ostree_cmd("cat", revision, "/usr/etc/system/commandline")
            )
            .strip()
            .decode("UTF-8")
        )
        for karg in kernelCommandline.split():
            kargs.append(f"--karg={karg.strip()}")

    stateroot = OS_NAME
    if not os.path.exists(os.path.join(sysroot, "ostree/deploy", OS_NAME)):
        stateroot = current_deployment().stateroot

    cmd = shlex.join(
        [
            "ostree",
            "admin",
            "deploy",
            f"--sysroot={sysroot}",
            *kargs,
            f"--os={OS_NAME}",
            f"--stateroot={stateroot}",
            "--retain",
            revision,
        ]
    )
    ret = _execute(cmd)
    if ret:
        raise subprocess.CalledProcessError(ret, cmd, None, None)


def prune(
    branch: str = "system",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    from .podman import podman  # noqa: PLC0415

    ostree(
        "prune",
        "--commit-only",
        f"--retain-branch-depth={OS_NAME}/{branch}={RETAIN}",
        f"--only-branch={OS_NAME}/{branch}",
        "--keep-younger-than=1 second",
        onstdout=onstdout,
        onstderr=onstderr,
    )
    execute("ostree", "admin", "cleanup", onstdout=onstdout, onstderr=onstderr)
    podman("system", "prune", "-f", "--build")


def undeploy(
    index: int,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    execute(
        "ostree",
        "admin",
        "undeploy",
        "--sysroot=/",
        str(index),
        onstdout=onstdout,
        onstderr=onstderr,
    )


class Deployment:
    def __init__(self, sysroot: OSTree.Sysroot, deployment: OSTree.Deployment) -> None:  # pyright: ignore[reportUnknownMemberType, reportUnknownParameterType]
        self.sysroot: OSTree.Sysroot = sysroot
        self.deployment: OSTree.Deployment = deployment

    @property
    def checksum(self) -> str:
        return self.deployment.get_csum()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def stateroot(self) -> str:
        return self.deployment.get_osname()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def unlocked(self) -> str:
        state = self.deployment.unlocked_state_to_string(self.deployment.get_unlocked())  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        assert isinstance(state, str)
        return state

    @property
    def booted(self) -> bool:
        return self.index == self.sysroot.get_booted_deployment().get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def pending(self) -> bool:
        staged = self.sysroot.get_staged_deployment()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if staged is None:
            return False

        return self.index == staged.get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def rollback(self) -> bool:
        _, rollback = self.sysroot.query_deployments_for(None)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return self.index == rollback.get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def finalization_locked(self) -> bool:
        return self.deployment.is_finalization_locked()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def soft_reboot_target(self) -> bool:
        return self.deployment.is_soft_reboot_target()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def staged(self) -> bool:
        return self.deployment.is_staged()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def pinned(self) -> bool:
        return self.deployment.is_pinned()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def serial(self) -> int:
        return self.deployment.get_deployserial()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def index(self) -> int:
        return self.deployment.get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def path(self) -> str:
        path = self.sysroot.get_deployment_directory(self.deployment).get_path()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        assert isinstance(path, str)
        assert os.path.exists(path)
        assert os.path.isdir(path)
        return path

    @property
    def os_info(self) -> dict[str, str]:
        with open(os.path.join(self.path, "usr/lib/os-release")) as f:
            return {
                x[0]: x[1]
                for x in [
                    x.strip().split("=", 1)
                    for x in f.readlines()
                    if "=" in x
                    if not x.startswith("#")
                ]
            }

    @property
    def type(self) -> str:
        if self.booted:
            return "current"

        if self.pending:
            return "pending"

        if self.rollback:
            return "rollback"

        return ""

    @property
    def packages(self) -> dict[str, str]:
        from .system import in_nspawn_system_output  # noqa: PLC0415

        packages: list[tuple[str, str]] = []
        try:
            packages = list(
                cast(tuple[str, str], tuple(x.split(" ", 1)))
                for x in in_nspawn_system_output("pacman", "-Q", deployment=self)
                .strip()
                .decode("utf-8")
                .splitlines()
            )

        except subprocess.CalledProcessError as e:
            if e.returncode != 2:
                raise

        return dict(packages)

    @property
    def imagePackages(self) -> dict[str, str]:
        packages: list[tuple[str, str]] = []
        try:
            with open(
                os.path.join(self.path, "usr/lib/system/packages.txt"),
                encoding="utf-8",
            ) as f:
                packages = list(
                    cast(tuple[str, str], tuple(x.split(" ", 1)))
                    for x in f.read().strip().splitlines()
                )

        except FileNotFoundError:
            pass

        return dict(packages)


def deployments() -> Generator[Deployment]:
    sysroot = OSTree.Sysroot.new_default()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    sysroot.load()  # pyright: ignore[reportUnknownMemberType]
    for deployment in sysroot.get_deployments():  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        yield Deployment(sysroot, deployment)  # pyright: ignore[reportUnknownArgumentType]


def current_deployment() -> Deployment:
    candidates = [x for x in deployments() if x.booted]
    assert len(candidates) == 1, (
        f"There should be one current deployment, not {len(candidates)}"
    )
    return candidates[0]
