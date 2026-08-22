import atexit
import os
import shlex
import shutil
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from getpass import getpass
from glob import iglob
from typing import (
    Any,
    cast,
)

from .. import OS_NAME
from ..ostree import (
    commit_export,
    deploy,
    ostree,
    update_bootloader,
    update_loader_entries,
)
from ..podman import (
    build,
    podman_cmd,
)
from ..system import (
    baseImage,
    execute,
    is_root,
)

kwds = {"help": f"Installs {OS_NAME}"}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--branch", default="system", help="System branch to prune")
    _ = parser.add_argument(
        "--sysroot", default="/mnt", help="Location to use for mounting target install"
    )
    _ = parser.add_argument(
        "--kernel-commandline",
        default="",
        help="Kernel command line arguments",
        dest="kernelCommandline",
    )
    _ = parser.add_argument(
        "--system-partition",
        default=None,
        help="Partition to install the system to",
        dest="dev_sys",
    )
    _ = parser.add_argument(
        "--boot-partition",
        default=None,
        help="Partition to install the bootloader to",
        dest="dev_boot",
    )
    _ = parser.add_argument(
        "--format-partitions",
        action="store_true",
        dest="formatPartitions",
        help="Format the partitions before installing",
    )
    _ = parser.add_argument(
        "--fast-install",
        action="store_true",
        dest="fastInstall",
        help="Don't copy the system and base images as part of the install",
    )
    _ = parser.add_argument(
        "--secure-boot",
        action="store_true",
        dest="secureBoot",
        help="Generate secure boot keys, register them, and sign the boot files",
    )
    _ = parser.add_argument("--password", default=None, help="New root password")
    _ = parser.add_argument(
        "--package", action="append", help="Extra package to install", default=[]
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    packages = cast(list[str], args.package)
    if not packages:
        packages += ["man-pages", "man-db", "git"]

    install(
        branch=cast(str, args.branch),
        sysroot=cast(str, args.sysroot),
        dev_sys=cast(str | None, args.dev_sys),
        dev_boot=cast(str | None, args.dev_boot),
        kernelCommandline=cast(str, args.kernelCommandline),
        formatPartitions=cast(bool, args.formatPartitions),
        password=cast(str, args.password),
        extraPackages=packages,
        fastInstall=cast(bool, args.fastInstall),
        secureBoot=cast(bool, args.secureBoot),
    )


def install(
    *,
    branch: str = "system",
    sysroot: str = "/mnt",
    dev_sys: str | None = None,
    dev_boot: str | None = None,
    kernelCommandline: str = "",
    formatPartitions: bool = False,
    password: str | None = None,
    extraPackages: list[str] | None = None,
    fastInstall: bool = False,
    secureBoot: bool = False,
) -> None:
    if os.path.exists("/ostree"):
        print("Cannot install on existing system")
        sys.exit(1)

    if password is None:
        password = os.environ.get("ROOT_PASSWORD", None)
        if password is None and sys.stdout.isatty():
            password = getpass("New root password: ")
            confirm_password = getpass("Confirm password: ")
            if password != confirm_password:
                print("Passwords do not match")
                sys.exit(1)

        if password is None:
            print("A new root password must be provided")
            sys.exit(1)

    if dev_sys is None:
        print("System partition must be specified")
        sys.exit(1)

    if dev_boot is None:
        print("Boot partition must be specified")
        sys.exit(1)

    setattr(ostree, "repo", os.path.normpath(f"{sysroot}/{getattr(ostree, 'repo')}"))
    if os.path.ismount(sysroot):
        execute("umount", "--recursive", sysroot)

    if formatPartitions:
        execute("mkfs.vfat", "-n", "SYS_BOOT", "-F", "32", dev_boot)
        execute("mkfs.ext4", "-L", "SYS_ROOT", "-F", dev_sys)

    execute("mount", "--mkdir", dev_sys, sysroot)
    execute("mount", "--mkdir", dev_boot, os.path.join(sysroot, "boot/efi"))
    execute("ostree", "admin", "init-fs", f"--sysroot={sysroot}", "--modern", sysroot)
    execute("ostree", "admin", "stateroot-init", f"--sysroot={sysroot}", OS_NAME)
    ostree("init", "--mode=bare")
    ostree("config", "set", "sysroot.bootprefix", "1")
    systemfile = "/tmp/Systemfile"  # noqa: S108
    if os.path.exists(systemfile):
        os.unlink(systemfile)

    _ = shutil.copy2("/etc/system/Systemfile", systemfile)
    build(
        systemfile,
        buildArgs={"KARGS": kernelCommandline},
        extraSteps=[
            r"RUN /usr/lib/system/install_packages \ ",
            " \\\n".join([f"  {x}" for x in extraPackages or []]),
        ],
    )
    os.unlink(systemfile)
    commit_export(
        branch,
        setup="""
        rm -f /etc
        rm -rf /var/*
        """,
    )
    deployment = deploy(branch, sysroot)
    execute("bootctl", "install", f"--esp-path={sysroot}/boot/efi")
    sysPath = [
        x.path
        for x in os.scandir(os.path.join(sysroot, f"ostree/deploy/{OS_NAME}/deploy"))
        if x.is_dir()
    ][0]
    for path in iglob(f"{sysPath}/boot/*"):
        if os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)

        else:
            shutil.rmtree(path)

    os.makedirs(
        os.path.join(sysroot, f"ostree/deploy/{OS_NAME}/var/home"), exist_ok=True
    )
    execute(
        "bash", "-c", f"genfstab -U {sysroot} >> {os.path.join(sysPath, 'etc/fstab')}"
    )
    if secureBoot:
        deployment.chroot(
            """
            set -e
            mkdir /var/lib
            export ESP_PATH=/boot/efi
            sbctl create-keys
            sbctl enroll-keys -m
            """,
            sysroot=sysroot,
        )

    update_loader_entries(sysroot)
    update_bootloader(sysroot, deployment=deployment)
    deployment.chroot(
        shlex.join(["echo", f"root:{password}"]) + " | chpasswd",
        sysroot=sysroot,
    )

    if not fastInstall:
        tmp = os.path.join(sysroot, ".tmp")
        os.mkdir(tmp)
        execute("mount", "-o", "bind", tmp, "/var/tmp")  # noqa: S108
        exitFunc1 = atexit.register(execute, "umount", "/var/tmp")  # noqa: S108
        storage = os.path.join(
            sysroot, "ostree/deploy", OS_NAME, "var/lib/containers/storage"
        )
        execute(
            "bash",
            "-c",
            " | ".join(
                [
                    shlex.join(
                        podman_cmd(
                            "save",
                            "--multi-image-archive",
                            "system:latest",
                            baseImage(),
                        )
                    ),
                    shlex.join(
                        [
                            "podman",
                            f"--root={storage}",
                            "--runroot=/tmp/podman-runroot",
                            "--storage-driver=overlay",
                            "--events-backend=file",
                            "load",
                        ]
                    ),
                ]
            ),
        )
        os.unlink(os.path.join(storage, "db.sql"))
        atexit.unregister(exitFunc1)
        os.sync()
        execute("umount", "/var/tmp")  # noqa: S108
        os.rmdir(tmp)

    os.sync()
    execute("umount", "--lazy", "--recursive", sysroot)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
