# pyright: reportImportCycles=false
import os
import shlex
import subprocess
from collections.abc import (
    Callable,
    Generator,
)
from datetime import datetime
from glob import iglob
from typing import cast

import gi  # pyright: ignore[reportMissingTypeStubs]

from . import OS_NAME, ROOTFS_PATH, SYSTEM_PATH
from .console import bytes_to_stderr, bytes_to_stdout
from .system import (
    _execute,  # pyright:ignore [reportPrivateUsage]
    baseImage,
    execute,
)

gi.require_version("OSTree", "1.0")  # pyright: ignore[reportUnknownMemberType]
from gi.repository import (  # pyright: ignore[reportMissingTypeStubs]
    Gio,  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
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
        deployment = self.sysroot.get_booted_deployment()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if deployment is None:
            return False

        return self.index == deployment.get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def pending(self) -> bool:
        pending, _ = self.sysroot.query_deployments_for(self.stateroot)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if pending is None:
            return False

        return self.index == pending.get_index()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @property
    def rollback(self) -> bool:
        _, rollback = self.sysroot.query_deployments_for(self.stateroot)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if rollback is None:
            return False

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
                    for x in f
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
            packages = [
                cast(tuple[str, str], tuple(x.split(" ", 1)))
                for x in in_nspawn_system_output(
                    "pacman", "-Q", deployment=self, quiet=True
                )
                .strip()
                .decode("utf-8")
                .splitlines()
            ]

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
                packages = [
                    cast(tuple[str, str], tuple(x.split(" ", 1)))
                    for x in f.read().strip().splitlines()
                ]

        except FileNotFoundError:
            pass

        return dict(packages)

    @property
    def image(self) -> str:
        return baseImage(os.path.join(self.path, "etc/system/Systemfile"))


def sysroot(sysroot_path: str | None = None) -> OSTree.Sysroot:  # pyright: ignore[reportUnknownMemberType, reportUnknownParameterType]
    if sysroot_path is None:
        sysroot_path = cast(str, ostree.repo)  # pyright: ignore[reportFunctionMemberAccess]
        parent = os.path.dirname(sysroot_path)
        if (
            os.path.basename(sysroot_path) == "repo"
            and os.path.basename(parent) == "ostree"
        ):
            sysroot_path = os.path.dirname(parent)

    sysroot = OSTree.Sysroot.new(Gio.File.new_for_path(sysroot_path))  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    sysroot.load()  # pyright: ignore[reportUnknownMemberType]
    return sysroot  # pyright: ignore[reportUnknownVariableType]


def deployments(sysroot_path: str | None = None) -> Generator[Deployment]:
    _sysroot: OSTree.Sysroot = sysroot(sysroot_path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    for deployment in _sysroot.get_deployments():  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        yield Deployment(_sysroot, deployment)  # pyright: ignore[reportUnknownArgumentType]


def current_deployment() -> Deployment:
    _sysroot: OSTree.Sysroot = sysroot()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    deployment = _sysroot.get_booted_deployment()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    assert deployment is not None
    return Deployment(_sysroot, deployment)  # pyright: ignore[reportUnknownArgumentType]


def update_grub_config(
    sysroot: str = "/",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    deployments_by_key: dict[tuple[str, int], Deployment] = {
        (deployment.checksum, deployment.serial): deployment
        for deployment in deployments(sysroot)
    }
    entries_dir = os.path.join(sysroot, "boot/loader/entries")
    for path in iglob(os.path.join(entries_dir, "ostree-*.conf")):
        stem = os.path.basename(path)[len("ostree-") : -len(".conf")]
        serial = 0
        if "." in stem:
            serial_str, stem = stem.rsplit(".", 1)
            if not serial_str.isdigit():
                continue

            serial = int(serial_str)

        deployment = deployments_by_key.get((stem.rpartition("-")[2], serial))
        if deployment is None:
            continue

        os_info = deployment.os_info
        version = os_info.get("VERSION", "0")
        version_id = os_info.get("VERSION_ID", "0")
        index = f"{deployment.index}.{serial}" if serial else str(deployment.index)
        title = (
            f"{index}: {deployment.image} {version}.{version_id} "
            f"[{deployment.stateroot}]"
        )
        for char in "'\"$\\\n\r":
            if char in title:
                raise ValueError(
                    f"Unsafe character {char!r} found in boot title: {title!r}"
                )

        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if line.startswith("title="):
                lines[i] = f"title={title}\n"
                with open(f"{path}.new", "w", encoding="utf-8") as f:
                    f.writelines(lines)

                os.replace(f"{path}.new", path)
                break

    grub_cfg = os.path.join(sysroot, "boot/efi/EFI/grub/grub.cfg")
    grub_cfg_new = f"{grub_cfg}.new"
    deployment = next(iter(deployments(sysroot)), None)
    if deployment is None:
        raise RuntimeError(f"No deployments found in sysroot {sysroot}")

    execute(
        "chroot",
        deployment.path,
        "/bin/bash",
        "-c",
        "grub-mkconfig -o /boot/efi/EFI/grub/grub.cfg.new",
        onstdout=onstdout,
        onstderr=onstderr,
    )
    execute(
        "chroot",
        deployment.path,
        "/bin/bash",
        "-c",
        "grub-script-check /boot/efi/EFI/grub/grub.cfg.new",
        onstdout=onstdout,
        onstderr=onstderr,
    )
    os.replace(grub_cfg_new, grub_cfg)
