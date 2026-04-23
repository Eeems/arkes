import json
import os
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from glob import iglob
from hashlib import sha256
from select import select
from typing import (
    BinaryIO,
    TextIO,
    cast,
)

import xattr  # pyright: ignore[reportMissingTypeStubs]

from . import SYSTEM_PATH
from .console import bytes_to_stderr, bytes_to_stdout


def file_hash(file: str) -> str:
    m = sha256()
    st = os.stat(file)
    m.update(f"{st.st_mode, st.st_uid, st.st_gid}".encode())
    xattrList = cast(Callable[[str], list[bytes]], getattr(xattr, "list"))
    m.update(b"\n".join(xattrList(file)))
    if os.path.isdir(file):
        m.update(file.encode("utf-8"))

    else:
        with open(file, "rb") as f:
            m.update(f.read())

    return m.hexdigest()


def baseImage(systemFile: str = "/etc/system/Systemfile") -> str:
    from .podman import base_images

    results = list(base_images(systemFile))
    if not results:
        raise RuntimeError("No FROM statement in the Systemfile")

    if len(results) > 1:
        raise RuntimeError(
            "Multiple FROM statements are not currently supported in a Systemfile"
        )

    return results[0]


def _execute(cmd: str) -> int:
    status = os.system(cmd)
    return os.waitstatus_to_exitcode(status)


def execute(
    cmd: str | list[str],
    *args: str,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
):
    if isinstance(cmd, str):
        _args = [cmd]
    else:
        _args = cmd

    ret = execute_pipe(*_args, *args, onstdout=onstdout, onstderr=onstderr)
    if ret:
        raise subprocess.CalledProcessError(ret, cmd, None, None)


def chronic(cmd: str | list[str], *args: str):
    argv: list[str] = []
    if isinstance(cmd, str):
        argv.append(cmd)

    else:
        argv += cmd

    if args:
        argv += args

    try:
        _ = subprocess.check_output(argv, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf-8"))  # pyright:ignore [reportAny]
        raise


def execute_pipe(
    *args: str,
    stdin: bytes | str | BinaryIO | TextIO | None = None,
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> int:
    p = subprocess.Popen(
        args,
        stdin=None if stdin is None else subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    while p.stdout is None or p.stderr is None:
        pass

    if isinstance(stdin, bytes):
        while p.stdin is None:
            pass

        _ = p.stdin.write(stdin)
        p.stdin.close()

    elif isinstance(stdin, str):
        while p.stdin is None:
            pass

        _ = p.stdin.write(stdin.encode("utf-8"))
        p.stdin.close()
    elif stdin is not None:
        os.set_blocking(stdin.fileno(), False)

    if stdin is not None:
        while p.stdin is None:
            pass

    os.set_blocking(p.stdout.fileno(), False)
    os.set_blocking(p.stderr.fileno(), False)
    while p.poll() is None:
        _ = select([p.stderr, p.stdout], [] if p.stdin is None else [p.stdin], [])
        line = p.stdout.readline()
        if line:
            onstdout(line)

        line = p.stderr.readline()
        if line:
            onstderr(line)

        if p.stdin is None or p.stdin.closed:
            continue

        if isinstance(stdin, BinaryIO):
            line = stdin.readline()
            if line:
                _ = p.stdin.write(line)

            if stdin.closed:
                p.stdin.close()

        elif isinstance(stdin, TextIO):
            line = stdin.readline().encode("utf-8")
            if line:
                _ = p.stdin.write(line)

            if stdin.closed:
                p.stdin.close()

        else:
            p.stdin.close()

    # Drain remaining buffered data from file objects
    for line in p.stdout.readlines():
        onstdout(line)

    for line in p.stderr.readlines():
        onstderr(line)

    return p.returncode


def system_kernelCommandLine() -> str:
    if os.path.exists("/etc/system/commandline"):
        with open("/etc/system/commandline", "r") as f:
            return f.read().strip()

    return ""


def checkupdates(image: str | None = None) -> list[str]:
    from .ostree import current_deployment
    from .podman import context_hash, image_labels, system_hash

    if image is None:
        image = baseImage()

    updates: list[str] = []
    new_hash = context_hash(f"KARGS={system_kernelCommandLine()}".encode("utf-8"))
    current_hash = system_hash()
    if new_hash != current_hash:
        updates.append(f"Systemfile {current_hash[:9]} -> {new_hash[:9]}")

    remote_labels = image_labels(image, remote=True)
    with open("/usr/lib/os-release", "r") as f:
        local_info = {
            x[0]: x[1]
            for x in [
                x.strip().split("=", 1)
                for x in f.readlines()
                if x.startswith("VERSION_ID=") or x.startswith("VERSION=")
            ]
        }

    local_id = local_info.get("VERSION_ID", "0")
    remote_id = remote_labels.get("os-release.VERSION_ID", "0")
    if local_id != remote_id:
        remote_version = remote_labels.get("os-release.VERSION", "0")
        local_version = local_info.get("VERSION", "0")
        updates.append(
            f"{image} {local_version}.{local_id} -> {remote_version}.{remote_id}"
        )

    system_updates: list[str] = []
    try:
        system_updates = (
            in_nspawn_system_output("checkupdates", etc="overlay")
            .strip()
            .decode("utf-8")
            .splitlines()
        )

    except subprocess.CalledProcessError as e:
        if e.returncode != 2:
            raise

    version_changes: dict[str, tuple[str, str]] = {}
    for pkg, change in [x.split(" ", 1) for x in system_updates if " " in x]:
        if " " not in change:
            continue

        fromv, tov = change.split(" -> ", 1)
        version_changes[pkg] = fromv, tov

    removals: dict[str, str] = {}
    additions: dict[str, str] = {}
    remote_packages = remote_labels.get("packages", "")
    remote_pkgs: dict[str, str] = {}
    for line in remote_packages.splitlines():
        if " " not in line:
            continue

        pkg, ver = line.split(" ", 1)
        remote_pkgs[pkg] = ver

    deployment = current_deployment()
    image_packages = deployment.imagePackages
    deployment_packages = deployment.packages
    local_pkgs = image_packages or deployment_packages

    for pkg, value in local_pkgs.items():
        if pkg in version_changes:
            continue

        if pkg not in remote_pkgs:
            removals[pkg] = value

        elif remote_pkgs[pkg] != value:
            version_changes[pkg] = value, remote_pkgs[pkg]

    for pkg, value in remote_pkgs.items():
        if pkg in version_changes or pkg in local_pkgs:
            continue

        additions[pkg] = value

    user_pkgs = {
        k: v
        for k, v in deployment_packages.items()
        if k not in image_packages and k not in remote_pkgs
    }
    mirrorlist_str = remote_labels.get("mirrorlist", "")
    if mirrorlist_str and user_pkgs:
        mirrorlist_urls = (
            cast(list[str], json.loads(mirrorlist_str)) if mirrorlist_str else []
        )
        mirrorlist_content = "\n".join(f"Server = {url}" for url in mirrorlist_urls)
        mirrorlist_path: str | None = None
        packages_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".mirrorlist", delete=False
            ) as f:
                _ = f.write(mirrorlist_content)
                mirrorlist_path = f.name

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".packages", delete=False
            ) as f:
                packages_path = f.name
                for pkg in user_pkgs.keys():
                    _ = f.write(f"{pkg}\n")

            packages_script: list[str] = [
                "set -e",
                "overlay_dir=$(mktemp -d)",
                'mkdir -p "$overlay_dir/upper" "$overlay_dir/work"',
                'mount -t overlay overlay -o lowerdir=/usr/lib/pacman,upperdir="$overlay_dir/upper",workdir="$overlay_dir/work" /usr/lib/pacman',
                "chronic pacman -Sy",
                "error_dir=$(mktemp -d)",
                "c(){",
                "  output=$(pacman -Sp --print-format '%n %v' \"$1\" 2>&1)",
                "  ret=$?",
                "  if [ $ret -ne 0 ]; then",
                "    case $output in",
                "      'error: target not found:'*) echo \"$output\" >&2;;",
                "      *'could not satisfy dependencies'*|*'failed to prepare transaction'*)",
                "        version=$(pacman -Si \"$1\" 2>/dev/null | grep '^Version' | awk '{print $3}')",
                '        if [ -n "$version" ]; then',
                '          echo "$1 $version"',
                "        else",
                '          echo "$output" >&2',
                "        fi",
                "        ;;",
                '      *) echo "$output" > "${error_dir}/${BASHPID}";;',
                "    esac",
                "  else",
                '    echo "$output"',
                "  fi",
                "}",
                "export -f c",
                "export error_dir",
                "cat /tmp/packages | xargs -rn 1 -P $(nproc) bash -c 'c \"$@\"' _",
                "umount /usr/lib/pacman",
                'rm -rf "$overlay_dir"',
                'if ls "$error_dir"/* >/dev/null 2>&1; then',
                '  cat "$error_dir"/*',
                '  rm -rf "$error_dir"',
                "  exit 1",
                "fi",
                'rm -rf "$error_dir"',
            ]
            output = (
                in_nspawn_system_output(
                    "sh",
                    "-ec",
                    "\n".join(packages_script),
                    binds=[
                        f"{packages_path}:/tmp/packages",
                        f"{mirrorlist_path}:/etc/pacman.d/mirrorlist",
                    ],
                )
                .strip()
                .decode("utf-8")
            )

            for line in output.splitlines():
                if " " not in line:
                    continue

                name, version = line.split(" ", 1)
                if name not in deployment_packages:
                    if name not in additions:
                        additions[name] = version

                elif (
                    name not in version_changes and deployment_packages[name] != version
                ):
                    version_changes[name] = deployment_packages[name], version

        finally:
            if mirrorlist_path is not None:
                os.unlink(mirrorlist_path)

            if packages_path is not None:
                os.unlink(packages_path)

    return (
        updates
        + [
            f"{k} {' -> '.join(version_changes[k])}"
            for k in sorted(version_changes.keys())
        ]
        + [f"{k} - -> {additions[k]}" for k in sorted(additions.keys())]
        + [f"{k} {removals[k]} -> -" for k in sorted(removals.keys())]
    )


def in_nspawn_system_cmd(
    *args: str,
    quiet: bool = False,
    deployment: object | None = None,  # ostree.Deployment
    binds: list[str] | None = None,
    overlays: list[str] | None = None,
    etc: str = "ro",
    home: str = "ro",
    var: str = "ro",
) -> list[str]:
    from .ostree import Deployment, current_deployment

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
        from .ostree import ostree

        setattr(ostree, "repo", repo)
        if not os.path.exists(repo):
            ostree("init")

    cache = "/var/cache/pacman"
    if not os.path.exists(cache):
        os.makedirs(cache, exist_ok=True)

    deployment = cast(Deployment | None, deployment)
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


def in_nspawn_system(
    *args: str,
    check: bool = False,
    quiet: bool = False,
    deployment: object | None = None,  # ostree.Deployment
    binds: list[str] | None = None,
    overlays: list[str] | None = None,
    etc: str = "ro",
    home: str = "ro",
    var: str = "ro",
) -> int:
    if not is_root():
        raise RuntimeError("in_nspawn_system can only be called as root")

    cmd = in_nspawn_system_cmd(
        *args,
        quiet=quiet,
        deployment=deployment,
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


def in_nspawn_system_output(
    *args: str,
    quiet: bool = False,
    deployment: object | None = None,  # ostree.Deployment
    binds: list[str] | None = None,
    overlays: list[str] | None = None,
    etc: str = "ro",
    home: str = "ro",
    var: str = "ro",
) -> bytes:
    if not is_root():
        raise RuntimeError("in_nspawn_system_output can only be called as root")

    return subprocess.check_output(
        in_nspawn_system_cmd(
            *args,
            quiet=quiet,
            deployment=deployment,
            binds=binds,
            overlays=overlays,
            etc=etc,
            home=home,
            var=var,
        ),
        stderr=subprocess.DEVNULL if quiet else None,
    )


def update_bootloader(
    onstdout: Callable[[bytes], None] = bytes_to_stdout,
    onstderr: Callable[[bytes], None] = bytes_to_stderr,
) -> None:
    execute(
        "/usr/bin/grub-mkconfig",
        "-o",
        "/boot/efi/EFI/grub/grub.cfg",
        onstderr=onstderr,
        onstdout=onstdout,
    )


def delete(glob: str):
    for path in iglob(glob):
        if os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)

        else:
            shutil.rmtree(path)


def is_root() -> bool:
    return os.geteuid() == 0


def wait_for_processes(
    *processes: subprocess.Popen[bytes],
    cleanup: Callable[[], None] | None = None,
    fast_fail: bool = True,
):
    errors: list[subprocess.CalledProcessError] = []
    queue = list(processes)
    while queue:
        for proc in list(queue):
            try:
                _ = proc.wait(1)

            except subprocess.TimeoutExpired:
                continue

            if proc.returncode is None:
                continue

            queue.remove(proc)
            if not proc.returncode:
                continue

            errors.append(subprocess.CalledProcessError(proc.returncode, proc.args))
            if not fast_fail:
                continue

            for proc in queue:
                proc.terminate()

            for proc in queue:
                try:
                    if proc.returncode is None:
                        _ = proc.wait(timeout=5)

                except subprocess.TimeoutExpired:
                    proc.kill()

            for proc in queue:
                if proc.wait():
                    errors.append(
                        subprocess.CalledProcessError(proc.returncode, proc.args)
                    )

            queue = []
            break

    if cleanup is not None:
        cleanup()

    if errors:
        raise ExceptionGroup("CalledProcessError", errors)  # noqa: F821
