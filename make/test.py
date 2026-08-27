import atexit
import os
import subprocess
import sys
import tempfile
import traceback
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    Any,
    cast,
)

import requests

from . import (
    BUILDER,
    execute,
    image_qualified_name,
    podman,
    podman_cmd,
)
from .boot import (
    check,
    clear_stdin,
    error_exit,
    expect,
    extract_boot,
    install,
    login,
    partition_disk,
    qemu_cmd,
    run,
    send,
    stop,
    workspace_path,
)
from .ref import ref


def reboot(proc: subprocess.Popen[bytes], cidfile: str) -> None:
    send(proc, b"sudo systemctl reboot\n")
    if expect(proc, [b"reboot: Restarting system"]) != b"reboot: Restarting system":
        print("boot-test: reboot failed", file=sys.stderr)
        error_exit(proc, cidfile)

    if not login(proc, b"root", b"live"):
        print("boot-test: login failed after reboot", file=sys.stderr)
        error_exit(proc, cidfile)


def validate(proc: subprocess.Popen[bytes], cidfile: str) -> None:
    if not check(proc, "os validate --verbose"):
        print("boot-test: os validate failed", file=sys.stderr)
        error_exit(proc, cidfile)


kwds: dict[str, str] = {
    "help": "Boot an iso in qemu and run validation against it",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument("iso", help="Path to the iso to boot")
    _ = parser.add_argument(
        "--from",
        dest="fromVariant",
        metavar="VARIANT",
        help="Test installing and upgrading from the latest version of VARIANT, or from a local iso",
    )
    _ = parser.add_argument(
        "--branch",
        default="iso-runner",
        help="iso-runner image ref to use, defaults to iso-runner.",
    )


def command(args: Namespace) -> None:
    targetIso: str = os.path.abspath(cast(str, args.iso))
    if not os.path.exists(targetIso):
        print(f"iso not found: {targetIso}", file=sys.stderr)
        sys.exit(1)

    variant: str | None = cast(str | None, args.fromVariant)
    branch: str = ref(cast(str, args.branch))
    image: str = f"{BUILDER}:{branch}"
    _ = atexit.register(clear_stdin)
    with tempfile.TemporaryDirectory(
        prefix="iso-runner-", dir=workspace_path()
    ) as workspace:
        # The iso to install. In --from mode this is the latest published
        # release for the variant; otherwise it is the passed-in iso argument.
        iso: str = targetIso
        if variant is not None:
            if os.path.isfile(variant):
                iso = variant

            else:
                res = requests.get(
                    "https://api.github.com/repos/Eeems/arkes/releases/tags/latest",
                    timeout=20,
                )
                res.raise_for_status()
                prefix = f"arkes-{variant}-"
                for line in cast(
                    str, cast(dict[str, Any], res.json())["body"]
                ).splitlines():
                    cells = [
                        cell.strip() for cell in line.strip().strip("|").split("|")
                    ]
                    cell = cells[0] if cells else ""
                    if not (cell.startswith("[") and "](" in cell):
                        continue

                    name, _, rest = cell[1:].partition("](")
                    found_url = rest.partition(")")[0]
                    if not (
                        name.startswith(prefix)
                        and name.endswith(".iso")
                        and name[len(prefix)].isdigit()
                    ):
                        continue

                    filename = name
                    url = found_url
                    sha256 = cells[-1].partition("`")[2].partition("`")[0]
                    break

                else:
                    print("boot-test: Unable to find iso for variant", file=sys.stderr)
                    sys.exit(1)

                dest = os.path.join(workspace, filename)
                print(f"boot-test: downloading {filename}", file=sys.stderr)
                execute(
                    "wget",
                    "--progress=dot:giga",
                    "--tries=3",
                    "--output-document",
                    dest,
                    url,
                )
                sums = os.path.join(workspace, "iso.sha256")
                with open(sums, "w") as f:
                    _ = f.write(f"{sha256}  {dest}\n")

                execute("sha256sum", "--check", sums)
                iso = dest

        pod_args: list[str] = [
            f"--volume={workspace}:/workspace",
            "--security-opt=label=disable",
            *(["--device=/dev/kvm"] if os.path.exists("/dev/kvm") else []),
        ]
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
        podman(
            "run",
            "--rm",
            *pod_args,
            image,
            "bash",
            "-c",
            "cp /usr/share/OVMF/OVMF_VARS_4M.fd /workspace/OVMF_VARS_4M.fd",
        )
        disk: str = "/workspace/disk.qcow2"
        # Phase 1: boot the iso, validate, install to the target disk.
        cidfile: str = os.path.join(workspace, "phase1.cid")
        # Published isos older than the serial console wiring cannot be
        # driven through their own bootloader. The kernel and initrd are
        # extracted from the iso and booted directly; OVMF loads them via
        # fw_cfg, keeping efivars available for the legacy os install to
        # enroll its boot entries.
        kernel: tuple[str, str, str] | None = None
        if variant is not None:
            kernel = extract_boot(iso, workspace, branch)

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
                *qemu_cmd(
                    graphical=False,
                    monitor=False,
                    disk=disk,
                    cdrom=kernel is None,
                    kernel=kernel,
                ),
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

            validate(proc, cidfile)
            if not partition_disk(proc):
                print("boot-test: failed to partition /dev/vda", file=sys.stderr)
                error_exit(proc, cidfile)

            if not install(proc, fastInstall=variant is not None):
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
        phase2_args: list[str] = list(pod_args)
        cdrom: bool = False
        if variant is not None:
            phase2_args.append(f"--volume={targetIso}:/iso:ro")
            cdrom = True

        proc = subprocess.Popen(
            podman_cmd(
                "run",
                "--rm",
                "-i",
                "--cidfile",
                cidfile,
                *phase2_args,
                image,
                "qemu-system-x86_64",
                *qemu_cmd(
                    graphical=False,
                    monitor=False,
                    disk=disk,
                    cdrom=cdrom,
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

            if variant is None:
                validate(proc, cidfile)

            elif not check(
                proc,
                """
                  echo '[test] mounting iso'
                  sudo mkdir -p /mnt/iso /mnt/sfs
                  sudo mount -o ro /dev/sr0 /mnt/iso
                  sudo modprobe loop
                  sudo modprobe squashfs
                  sudo mount -o loop,ro /mnt/iso/arkes/x86_64/airootfs.sfs /mnt/sfs
                  sudo mkdir -p /var/tmp/sfs-upper /var/tmp/sfs-work
                  sudo mount -t overlay overlay \\
                    -o lowerdir=/mnt/sfs/var/lib/containers/storage,upperdir=/var/tmp/sfs-upper,workdir=/var/tmp/sfs-work \\
                    /mnt/sfs/var/lib/containers/storage
                """,
            ):
                print(
                    "boot-test: failed to mount iso",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            output = run(
                proc,
                "awk 'NR==1{print $2; exit}' /mnt/sfs/etc/system/Systemfile",
                timeout=5,
            )
            if output is None:
                print(
                    "boot-test: failed to read FROM line",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            image = image_qualified_name(output.decode().strip())
            if not check(
                proc,
                f"""
                  echo '[test] copying image {image}'
                  sudo skopeo --insecure-policy copy \\
                    "containers-storage:[overlay@/mnt/sfs/var/lib/containers/storage+/var/tmp/podman-runroot]{image}" \\
                    "containers-storage:{image}"
                """,
            ):
                print(
                    "boot-test: failed to load build into installed system",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            if variant is not None and not check(
                proc,
                """
                  sudo cp /mnt/sfs/etc/system/Systemfile /etc/system/Systemfile
                  sudo sed -i '1a RUN echo "nameserver 10.0.2.3" > /etc/resolv.conf' /etc/system/Systemfile
                """,
            ):
                print("boot-test: failed to patch Systemfile", file=sys.stderr)
                error_exit(proc, cidfile)

            # Run the upgrade in the background while verifying that the
            # os-daemon holds a logind inhibitor lock for its duration.
            if not check(
                proc,
                """
                  os upgrade --no-pull &
                  pid=$!
                  found=0
                  while kill -0 $pid 2>/dev/null; do
                    if systemd-inhibit --list --no-legend --no-pager |
                      awk '/^os-daemon[[:space:]]/ {found=1} END {exit !found}'; then
                      found=1
                      break
                    fi
                    sleep 1
                  done
                  if [ $found -eq 0 ]; then
                    echo "No inhibitor was created" >&2
                    exit 1
                  fi
                  wait $pid
                  rc=$?
                  if [ $rc -eq 0 ] && ! systemd-inhibit --list --no-legend --no-pager |
                    awk '/^os-daemon[[:space:]]/ {found=1} END {exit found}'; then
                    echo "Inhibitor was not released" >&2
                    exit 1
                  fi
                  exit $rc
                """,
            ):
                print(
                    "boot-test: os upgrade failed or inhibitor not held/released",
                    file=sys.stderr,
                )
                error_exit(proc, cidfile)

            reboot(proc, cidfile)
            validate(proc, cidfile)
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

            if variant is not None:
                if not check(
                    proc,
                    "os upgrade --no-pull",
                ):
                    print(
                        "boot-test: second os upgrade failed",
                        file=sys.stderr,
                    )
                    error_exit(proc, cidfile)

                reboot(proc, cidfile)
                validate(proc, cidfile)

            if not stop(proc):
                print("boot-test: phase 2 shutdown failed", file=sys.stderr)
                error_exit(proc, cidfile)

        except KeyboardInterrupt, Exception:
            traceback.print_exc()
            error_exit(proc, cidfile)

    print("boot-test: validation passed", file=sys.stderr)


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
