# pyright: reportImportCycles=false
import os
import shlex
import subprocess
import json

from datetime import datetime
from typing import Callable
from typing import cast
from collections.abc import Generator

from . import SYSTEM_PATH
from . import ROOTFS_PATH
from . import OS_NAME

from .system import execute
from .system import _execute  # pyright:ignore [reportPrivateUsage]
from .console import bytes_to_stdout
from .console import bytes_to_stderr

RETAIN = 5


def ostree_cmd(*args: str) -> list[str]:
    return ["ostree", f"--repo={getattr(ostree, 'repo')}", *args]


def ostree(
    *args: str,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
):
    execute(*ostree_cmd(*args), onstdout=onstdout, onstderr=onstderr)


setattr(ostree, "repo", "/ostree/repo")


def commit(
    branch: str = "system",
    rootfs: str | None = None,
    skipList: list[str] | None = None,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
):
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


def deploy(
    branch: str = "system",
    sysroot: str = "/",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,  # pyright:ignore [reportUnusedParameter]
    onstderr: Callable[[bytes], None] = bytes_to_stderr,  # pyright:ignore [reportUnusedParameter]
):
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
):
    from .podman import podman

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
):
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
    def __init__(self, data: dict[str, str | int | bool]):
        self.data: dict[str, str | int | bool] = data

    @property
    def checksum(self) -> str:
        checksum = self.data.get("checksum", "")
        assert isinstance(checksum, str)
        return checksum

    @property
    def stateroot(self) -> str:
        stateroot = self.data.get("stateroot", "")
        assert isinstance(stateroot, str)
        return stateroot

    @property
    def unlocked(self) -> str:
        unlocked = self.data.get("unlocked", "")
        assert isinstance(unlocked, str)
        return unlocked

    @property
    def booted(self) -> bool:
        booted = self.data.get("booted", False)
        assert isinstance(booted, bool)
        return booted

    @property
    def pending(self) -> bool:
        pending = self.data.get("pending", False)
        assert isinstance(pending, bool)
        return pending

    @property
    def rollback(self) -> bool:
        rollback = self.data.get("rollback", False)
        assert isinstance(rollback, bool)
        return rollback

    @property
    def finalization_locked(self) -> bool:
        finalization_locked = self.data.get("finalization-locked", False)
        assert isinstance(finalization_locked, bool)
        return finalization_locked

    @property
    def soft_reboot_target(self) -> bool:
        soft_reboot_target = self.data.get("soft-reboot-target", False)
        assert isinstance(soft_reboot_target, bool)
        return soft_reboot_target

    @property
    def staged(self) -> bool:
        staged = self.data.get("staged", False)
        assert isinstance(staged, bool)
        return staged

    @property
    def pinned(self) -> bool:
        pinned = self.data.get("pinned", False)
        assert isinstance(pinned, bool)
        return pinned

    @property
    def serial(self) -> int:
        serial = self.data.get("serial", -1)
        assert isinstance(serial, int)
        return serial

    @property
    def index(self) -> int:
        index = self.data.get("index", -1)
        assert isinstance(index, int)
        return index

    @property
    def path(self) -> str:
        path = f"/ostree/deploy/{self.stateroot}/deploy/{self.checksum}.{self.serial}"
        assert os.path.exists(path)
        assert os.path.isdir(path)
        return path

    @property
    def os_info(self) -> dict[str, str]:
        with open(os.path.join(self.path, "usr/lib/os-release"), "r") as f:
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


def deployments() -> Generator[Deployment, None, None]:
    status = json.loads(  # pyright: ignore[reportAny]
        subprocess.check_output(["ostree", "admin", "status", "--json"])
    )
    assert isinstance(status, dict)
    deployments = cast(
        list[dict[str, str | int | bool]],
        status.get("deployments", []),  # pyright: ignore[reportUnknownMemberType]
    )
    for deployment in deployments:
        yield Deployment(deployment)


def current_deployment() -> Deployment:
    candidates = [x for x in deployments() if x.booted]
    assert len(candidates) == 1, (
        f"There should be one current deployment, not {len(candidates)}"
    )
    return candidates[0]
