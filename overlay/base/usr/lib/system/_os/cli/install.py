import os
import shlex
import shutil
import subprocess
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from getpass import getpass
from glob import iglob
from threading import Thread
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
    image_qualified_name,
    storage_graph_driver,
    storage_graph_root,
    storage_run_root,
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


def copy_images(sysroot: str, result: dict[str, str]) -> None:
    output = bytearray()
    try:
        tmp = os.path.join(sysroot, ".tmp")
        os.mkdir(tmp)
        execute("mount", "-o", "bind", tmp, "/var/tmp")  # noqa: S108
        storage = os.path.join(
            sysroot, "ostree/deploy", OS_NAME, "var/lib/containers/storage"
        )
        for image in ("system:latest", baseImage()):
            image = image_qualified_name(image)  # noqa: PLW2901
            execute(
                "skopeo",
                "--insecure-policy",
                "copy",
                (
                    f"containers-storage:[{storage_graph_driver()}@{storage_graph_root()}"
                    f"+{storage_run_root()}]{image}"
                ),
                f"containers-storage:[overlay@{storage}]{image}",
                onstdout=output.extend,
                onstderr=output.extend,
            )

        os.sync()
        execute("umount", "/var/tmp")  # noqa: S108
        os.rmdir(tmp)

    except BaseException as e:
        result["error"] = f"{e}\n{output.decode('utf-8', errors='replace')}"
        raise


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

    if subprocess.check_output(["lsblk", "-no", "pttype", dev_boot]).strip() != b"gpt":
        print(f"Boot partition {dev_boot} is not on a GPT disk", file=sys.stderr)
        sys.exit(1)

    uefi: bool = os.path.ismount("/sys/firmware/efi/efivars") and any(
        iglob("/sys/firmware/efi/efivars/SetupMode-*")
    )

    if secureBoot and not uefi:
        if not os.path.ismount("/sys/firmware/efi/efivars"):
            print(
                "Secure boot requires UEFI firmware with accessible EFI variables, but /sys/firmware/efi/efivars is not available",
                file=sys.stderr,
            )
            sys.exit(1)

        print(
            "Secure boot cannot be enabled. The SetupMode EFI variable is missing.",
            file=sys.stderr,
        )
        sys.exit(1)

    setattr(ostree, "repo", os.path.normpath(f"{sysroot}/{getattr(ostree, 'repo')}"))
    if os.path.ismount(sysroot):
        execute("umount", "--recursive", sysroot)

    if formatPartitions:
        execute("mkfs.vfat", "-n", "SYS_BOOT", "-F", "32", dev_boot)
        execute("mkfs.ext4", "-L", "SYS_ROOT", "-F", dev_sys)

    if not uefi:
        execute("dosfslabel", dev_boot, "SYS_BOOT")

    execute("mount", "--mkdir", dev_sys, sysroot)
    execute("mount", "--mkdir", dev_boot, os.path.join(sysroot, "boot/efi"))
    execute("ostree", "admin", "init-fs", f"--sysroot={sysroot}", "--modern", sysroot)
    execute("ostree", "admin", "stateroot-init", f"--sysroot={sysroot}", OS_NAME)
    ostree("init", "--mode=bare")
    ostree("config", "set", "sysroot.bootprefix", "1")
    ostree("config", "set", "sysroot.bootloader", "none")
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

    copy_result: dict[str, str] = {}
    copy_thread: Thread | None = None
    if not fastInstall:
        print("[system] Copying images in background", file=sys.stderr)
        copy_thread = Thread(target=copy_images, args=(sysroot, copy_result))
        copy_thread.start()

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
            export ESP_PATH=/sysroot/boot/efi
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
        assert copy_thread is not None
        print("[system] Waiting for image copy to finish", file=sys.stderr)
        copy_thread.join()
        if "error" in copy_result:
            print(copy_result["error"], file=sys.stderr)
            sys.exit(1)

    os.sync()
    execute("umount", "--lazy", "--recursive", sysroot)


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
