# pyright: reportImportCycles=false
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import (
    Callable,
    Generator,
)
from contextlib import ExitStack
from datetime import datetime
from functools import partial
from glob import iglob
from typing import cast

import gi  # pyright: ignore[reportMissingTypeStubs]

from . import OS_NAME, ROOTFS_PATH, SYSTEM_PATH
from .console import (
    bytes_to_stderr,
    bytes_to_stdout,
)
from .system import (
    _execute,  # pyright:ignore [reportPrivateUsage]
    baseImage,
    execute,
    is_root,
    mount,
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
    setup: str = """
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
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    from .ostree import ostree_cmd  # noqa: PLC0415
    from .podman import export_stream  # noqa: PLC0415

    with export_stream(
        setup=setup,
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
    def index_str(self) -> str:
        return (
            f"{self.index}.{self.serial}" if self.serial else str(self.index)
        )

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
        packages: list[tuple[str, str]] = []
        try:
            packages = [
                cast(tuple[str, str], tuple(x.split(" ", 1)))
                for x in self.nspawn_output("pacman", "-Q", quiet=True)
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

    def chroot(
        self,
        cmd: str,
        sysroot: str = "/",
        onstdout: Callable[[bytes], None] = bytes_to_stdout,
        onstderr: Callable[[bytes], None] = bytes_to_stderr,
    ) -> None:
        _mount = partial(
            mount,
            onstdout=onstdout,
            onstderr=onstderr,
        )
        with ExitStack() as stack:
            sysroot_partition = (
                subprocess.check_output(
                    [
                        "findmnt",
                        "--noheadings",
                        "--output",
                        "SOURCE",
                        "--target",
                        sysroot,
                    ]
                )
                .decode()
                .strip()
                .split("[", 1)[0]
            )
            stack.enter_context(
                _mount(sysroot_partition, os.path.join(self.path, "sysroot"))
            )
            boot_partition = (
                subprocess.check_output(
                    [
                        "findmnt",
                        "--noheadings",
                        "--output",
                        "SOURCE",
                        "--target",
                        os.path.join(sysroot, "boot/efi"),
                    ]
                )
                .decode()
                .strip()
                .split("[", 1)[0]
            )
            stack.enter_context(
                _mount(boot_partition, os.path.join(self.path, "sysroot/boot/efi"))
            )
            stack.enter_context(
                _mount(
                    os.path.join(sysroot, "ostree/deploy", self.stateroot, "var"),
                    os.path.join(self.path, "var"),
                    rbind=True,
                )
            )
            for i in ["dev", "proc", "sys", "tmp"]:
                stack.enter_context(
                    _mount(f"/{i}", os.path.join(self.path, i), bind=True)
                )

            if os.path.exists("/sys/firmware/efi/efivars"):
                stack.enter_context(
                    _mount(
                        "/sys/firmware/efi/efivars",
                        os.path.join(self.path, "sys/firmware/efi/efivars"),
                        rbind=True,
                    )
                )

            execute(
                "chroot",
                self.path,
                "/bin/bash",
                "-c",
                cmd,
                onstdout=onstdout,
                onstderr=onstderr,
            )
            os.sync()

    def nspawn(
        self,
        *args: str,
        check: bool = False,
        quiet: bool = False,
        binds: list[str] | None = None,
        overlays: list[str] | None = None,
        etc: str = "ro",
        home: str = "ro",
        var: str = "ro",
    ) -> int:
        if not is_root():
            raise RuntimeError("nspawn can only be called as root")

        cmd = in_nspawn_system_cmd(
            *args,
            quiet=quiet,
            deployment=self,
            binds=binds,
            overlays=overlays,
            etc=etc,
            home=home,
            var=var,
        )
        ret = _execute(shlex.join(cmd))
        if ret and check:
            raise subprocess.CalledProcessError(ret, cmd, None, None)

        return ret

    def nspawn_output(
        self,
        *args: str,
        quiet: bool = False,
        binds: list[str] | None = None,
        overlays: list[str] | None = None,
        etc: str = "ro",
        home: str = "ro",
        var: str = "ro",
    ) -> bytes:
        if not is_root():
            raise RuntimeError("nspawn_output can only be called as root")

        return subprocess.check_output(
            in_nspawn_system_cmd(
                *args,
                quiet=quiet,
                deployment=self,
                binds=binds,
                overlays=overlays,
                etc=etc,
                home=home,
                var=var,
            ),
            stderr=subprocess.DEVNULL if quiet else None,
        )


def deploy(
    branch: str = "system",
    sysroot: str = "/",
    onstdout: Callable[[bytes], None] = bytes_to_stdout,  # pyright:ignore [reportUnusedParameter]
    onstderr: Callable[[bytes], None] = bytes_to_stderr,  # pyright:ignore [reportUnusedParameter]
) -> Deployment:
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

    return list(deployments(sysroot))[0]


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


def in_nspawn_system_cmd(
    *args: str,
    quiet: bool = False,
    deployment: Deployment | None = None,
    binds: list[str] | None = None,
    overlays: list[str] | None = None,
    etc: str = "ro",
    home: str = "ro",
    var: str = "ro",
) -> list[str]:
    _ostree_root = ""
    if os.path.exists("/ostree") and os.path.isdir("/ostree"):
        _ostree = "/ostree"
        if not os.path.exists(SYSTEM_PATH):
            os.makedirs(SYSTEM_PATH, exist_ok=True)

        if not os.path.exists(f"{SYSTEM_PATH}/ostree"):
            os.symlink("/ostree", f"{SYSTEM_PATH}/ostree")

    else:
        _ostree = f"{SYSTEM_PATH}/ostree"
        os.makedirs(_ostree, exist_ok=True)
        repo = os.path.join(_ostree, "repo")
        _ostree_root = f"{SYSTEM_PATH}/"
        setattr(ostree, "repo", repo)
        if not os.path.exists(repo):
            ostree("init")

    cache = "/var/cache/pacman"
    if not os.path.exists(cache):
        os.makedirs(cache, exist_ok=True)

    if deployment is None:
        deployment = current_deployment()

    if binds is None:
        binds = []

    if overlays is None:
        overlays = []

    if etc == "rw":
        etc = "bind"

    match etc:
        case "overlay":
            overlays.append("+/etc::/etc")

        case "bind":
            binds.append("/etc")

        case "ro":
            pass

        case _:
            raise NotImplementedError(f"Unknown etc setting: {etc}")

    if home == "rw":
        home = "bind"

    match home:
        case "overlay":
            overlays.append("+/var/home::/var/home")

        case "bind":
            binds.append("/var/home")

        case "ro":
            pass

        case _:
            raise NotImplementedError(f"Unknown home setting: {home}")

    if var == "rw":
        var = "bind"

    match var:
        case "overlay":
            overlays.append(f"+/sysroot/ostree/deploy/{deployment.stateroot}/var::/var")

        case "bind":
            binds.append("/var")

        case "ro":
            binds.append(f"+/sysroot/ostree/deploy/{deployment.stateroot}/var:/var")

        case _:
            raise NotImplementedError(f"Unknown var setting: {var}")

    os.environ["SYSTEMD_NSPAWN_LOCK"] = "0"
    # TODO overlay /usr/lib/pacman somehow
    return [
        "systemd-nspawn",
        "--as-pid2",
        "--pipe",
        "--volatile=state",
        "--link-journal=no",
        "--directory=/sysroot",
        "--resolv-conf=off",
        *(["--quiet"] if quiet else []),
        f"--bind={SYSTEM_PATH}:{SYSTEM_PATH}",
        "--bind=/boot:/boot",
        "--bind=/run/podman/podman.sock:/run/podman/podman.sock",
        f"--bind={cache}",
        *[f"--bind={x}" for x in binds],
        *[f"--overlay={x}" for x in overlays],
        f"--pivot-root={_ostree_root}{deployment.path}:/sysroot",
        *args,
    ]


def loader_entries(sysroot: str) -> Generator[tuple[str, dict[str, str], Deployment]]:
    sysroot = os.path.normpath(sysroot)
    deployments_by_key: dict[tuple[str, str, int], Deployment] = {
        (deployment.stateroot, deployment.checksum, deployment.serial): deployment
        for deployment in deployments(sysroot)
    }
    for path in iglob(os.path.join(sysroot, "boot/loader/entries", "ostree-*.conf")):
        props: dict[str, str] = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.strip().partition(" ")
                if sep:
                    props[key] = value.strip()

        kernel = props.get("linux")
        if kernel is None:
            print(
                f"Skipping loader entry {path}: missing linux property",
                file=sys.stderr,
            )
            continue

        initrd = props.get("initrd")
        if initrd is None:
            print(
                f"Skipping loader entry {path}: missing initrd property",
                file=sys.stderr,
            )
            continue

        options = props.get("options")
        if options is None:
            print(
                f"Skipping loader entry {path}: missing options property",
                file=sys.stderr,
            )
            continue

        bootlink = next(
            (
                arg[len("ostree=") :]
                for arg in options.split()
                if arg.startswith("ostree=")
            ),
            None,
        )
        if bootlink is None:
            print(
                f"Skipping loader entry {path}: missing ostree= argument",
                file=sys.stderr,
            )
            continue

        deployment_name = os.path.basename(
            os.path.realpath(os.path.join(sysroot, bootlink.lstrip("/")))
        )
        checksum, serial_str = deployment_name.rsplit(".", 1)
        serial = int(serial_str)
        deployment = deployments_by_key.get((bootlink.split("/")[3], checksum, serial))
        if deployment is None:
            print(
                f"Skipping loader entry {path}: could not find deployment",
                file=sys.stderr,
            )
            continue

        yield path, props, deployment


def update_loader_entries(sysroot: str = "/") -> None:
    sysroot = os.path.normpath(sysroot)
    staged: list[tuple[str, list[str]]] = []
    for path, props, deployment in loader_entries(sysroot):
        os_info = deployment.os_info
        version = os_info.get("VERSION", "0")
        version_id = os_info.get("VERSION_ID", "0")
        title = (
            f"{deployment.index_str}: {deployment.image} {version}.{version_id} "
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
            if line.startswith("title "):
                lines[i] = f"title {title}\n"
                break

        else:
            lines.append(f"title {title}\n")

        staged.append((path, lines))

    for path, lines in staged:
        with open(f"{path}.new", "w", encoding="utf-8") as f:
            f.writelines(lines)

    for path, _ in staged:
        os.replace(f"{path}.new", path)

    names: set[str] = set()
    for path, props, deployment in loader_entries(sysroot):
        index = (
            f"{deployment.index}.{deployment.serial}"
            if deployment.serial
            else deployment.index
        )
        name = f"arkes-{deployment.os_info.get('VERSION_ID', '0')}-{index}.efi"
        output = f"/sysroot/boot/efi/EFI/Linux/{name}"
        names.add(name)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", prefix="arkes-cmdline-", dir="/tmp"
        ) as cmdlineFile:
            _ = cmdlineFile.write(f"{props['options']}\n")
            cmdlineFile.flush()
            commands = [
                "set -e",
                "export ESP_PATH=/sysroot/boot/efi",
                shlex.join(
                    [
                        "sbctl",
                        "bundle",
                        "--cmdline",
                        cmdlineFile.name,
                        "--kernel-img",
                        f"/sysroot{props['linux']}",
                        "--initramfs",
                        f"/sysroot{props['initrd']}",
                        output,
                    ]
                ),
            ]
            if os.path.isfile(
                os.path.join(
                    sysroot,
                    "ostree/deploy",
                    deployment.stateroot,
                    "var/lib/sbctl/keys/db/db.key",
                )
            ):
                commands.append(shlex.join(["sbctl", "sign", "-s", output]))

            deployment.chroot("\n".join(commands), sysroot=sysroot)

    efi_linux_dir = os.path.join(sysroot, "sysroot/boot/efi/EFI/Linux")
    os.makedirs(efi_linux_dir, exist_ok=True)
    for ukiPath in iglob(os.path.join(efi_linux_dir, "arkes-*.efi")):
        if os.path.basename(ukiPath) in names:
            continue

        os.unlink(ukiPath)


def update_bootloader(
    sysroot: str = "/",
    deployment: Deployment | None = None,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    if deployment is None:
        deployment = next(iter(deployments(sysroot)), None)

    if deployment is None:
        raise RuntimeError(f"No deployments found in sysroot {sysroot}")

    chroot = partial(
        deployment.chroot,
        sysroot=sysroot,
        onstdout=onstdout,
        onstderr=onstderr,
    )
    chroot("bootctl update --esp-path=/sysroot/boot/efi")
    if not os.path.isfile(
        os.path.join(
            sysroot,
            "ostree/deploy",
            deployment.stateroot,
            "var/lib/sbctl/keys/db/db.key",
        )
    ):
        return

    chroot(
        """
        set -e
        export ESP_PATH=/sysroot/boot/efi
        sbctl verify | sed -E 's|^.* (/.+) is not signed$|sbctl sign -s "\\1"|e'
        """
    )
