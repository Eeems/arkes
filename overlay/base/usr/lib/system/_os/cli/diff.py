import os
import subprocess
import sys
import tempfile
from argparse import (
    ArgumentParser,
    Namespace,
)
from enum import StrEnum
from glob import iglob
from typing import (
    Any,
    cast,
)

from ..console import bytes_to_stdout
from ..ostree import (
    Deployment,
    deployments,
    ostree,
)
from ..podman import context_hash
from ..system import (
    baseImage,
    file_hash,
    is_root,
    wait_for_processes,
)

kwds = {"help": "Diff the changes between two deployments"}


class Selection(StrEnum):
    PACKAGES = "packages"
    CONTEXT = "context"
    FULL = "full"


class Output(StrEnum):
    DIFF = "diff"
    NAME_ONLY = "name-only"
    NAME_STATUS = "name-status"


def register(parser: ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group()
    _ = selection.add_argument(
        "--packages",
        action="store_const",
        const=Selection.PACKAGES,
        dest="selection",
        help="Diff the installed packages",
    )
    _ = selection.add_argument(
        "--context",
        action="store_const",
        const=Selection.CONTEXT,
        dest="selection",
        help="Diff the context files",
    )
    _ = selection.add_argument(
        "--full",
        action="store_const",
        const=Selection.FULL,
        dest="selection",
        help="Diff all files",
    )
    output = parser.add_mutually_exclusive_group()
    _ = output.add_argument(
        "--diff",
        action="store_const",
        const=Output.DIFF,
        dest="output",
        help="Show the actual differences",
    )
    _ = output.add_argument(
        "--name-only",
        action="store_const",
        const=Output.NAME_ONLY,
        dest="output",
        help="Show only the names of the differences",
    )
    _ = output.add_argument(
        "--name-status",
        action="store_const",
        const=Output.NAME_STATUS,
        dest="output",
        help="Show the names and status of the differences",
    )
    _ = parser.add_argument(
        "from_deployment",
        type=int,
        help="Deployment to diff from",
    )
    _ = parser.add_argument(
        "to_deployment",
        type=int,
        help="Deployment to diff to",
    )
    parser.set_defaults(selection=Selection.PACKAGES, output=Output.DIFF)


def diff_dicts(
    from_items: dict[str, str], to_items: dict[str, str]
) -> dict[str, tuple[str | None, str | None]]:
    changes: dict[str, tuple[str | None, str | None]] = {}
    for item in sorted(set(from_items) | set(to_items)):
        from_value = from_items.get(item)
        to_value = to_items.get(item)
        if from_value != to_value:
            changes[item] = from_value, to_value

    return changes


def context_files(deployment: Deployment) -> dict[str, str]:
    context = f"{deployment.path}/etc/system"
    return {
        os.path.relpath(file, deployment.path): file_hash(file)
        for file in iglob(f"{context}/**", recursive=True)
        if not os.path.isdir(file)
    }


def diff_files(
    from_path: str,
    to_path: str,
    from_label: str | None = None,
    to_label: str | None = None,
) -> None:
    cmd = [
        "diff",
        "-U0",
        *([] if from_label is None else [f"--label={from_label}"]),
        *([] if to_label is None else [f"--label={to_label}"]),
        from_path,
        to_path,
    ]
    diff_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert diff_proc.stdout is not None
    color_proc = subprocess.Popen(
        ["colordiff", "--always"],
        stdin=diff_proc.stdout,
        stdout=subprocess.PIPE,
    )
    assert color_proc.stdout is not None
    diff_proc.stdout.close()
    highlight_proc = subprocess.Popen(
        ["/usr/share/git/diff-highlight/diff-highlight"],
        stdin=color_proc.stdout,
        stdout=subprocess.PIPE,
    )
    color_proc.stdout.close()
    output = highlight_proc.communicate()[0]
    wait_for_processes(color_proc, highlight_proc)
    if diff_proc.wait() not in (0, 1):
        raise subprocess.CalledProcessError(diff_proc.returncode, cmd)

    bytes_to_stdout(output)


def print_file_changes(
    from_deployment: Deployment,
    to_deployment: Deployment,
    changes: dict[str, tuple[str | None, str | None]],
    output: Output,
) -> None:
    match output:
        case Output.DIFF:
            for file, (from_hash, to_hash) in changes.items():
                from_path = (
                    f"{from_deployment.path}/{file}"
                    if from_hash is not None
                    else "/dev/null"
                )
                to_path = (
                    f"{to_deployment.path}/{file}"
                    if to_hash is not None
                    else "/dev/null"
                )
                _ = sys.stdout.buffer.write(f"--- {file}\n".encode())
                diff_files(from_path, to_path)

        case Output.NAME_ONLY:
            for file in changes:
                print(file)

        case Output.NAME_STATUS:
            for file, (from_hash, to_hash) in changes.items():
                if from_hash is None:
                    status = "\033[32mA\033[0m"
                elif to_hash is None:
                    status = "\033[31mD\033[0m"
                else:
                    status = "\033[33mM\033[0m"
                print(f"{status} {file}")


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    _deployments = list(deployments())
    from_index = cast(int, args.from_deployment)
    to_index = cast(int, args.to_deployment)
    from_deployment = _deployments[from_index]
    to_deployment = _deployments[to_index]
    output = cast(Output, args.output)
    changes: dict[str, tuple[str | None, str | None]]
    match cast(Selection, args.selection):
        case Selection.PACKAGES:
            from_hash = context_hash(path=from_deployment.path)
            to_hash = context_hash(path=to_deployment.path)
            from_info = from_deployment.os_info
            to_info = to_deployment.os_info
            from_id = from_info.get("VERSION_ID", "0")
            to_id = to_info.get("VERSION_ID", "0")
            from_image = baseImage(f"{from_deployment.path}/etc/system/Systemfile")
            to_image = baseImage(f"{to_deployment.path}/etc/system/Systemfile")
            from_version = f"{from_info.get('VERSION', '0')}.{from_id}"
            to_version = f"{to_info.get('VERSION', '0')}.{to_id}"
            if output == Output.DIFF:
                from_list = (
                    f"Systemfile {from_hash[:9]}\n{from_image} {from_version}\n"
                    + "".join(
                        f"{pkg} {version}\n"
                        for pkg, version in sorted(from_deployment.packages.items())
                    )
                ).encode()
                to_list = (
                    f"Systemfile {to_hash[:9]}\n{to_image} {to_version}\n"
                    + "".join(
                        f"{pkg} {version}\n"
                        for pkg, version in sorted(to_deployment.packages.items())
                    )
                ).encode()
                with (
                    tempfile.NamedTemporaryFile() as from_file,
                    tempfile.NamedTemporaryFile() as to_file,
                ):
                    _ = from_file.write(from_list)
                    from_file.flush()
                    _ = to_file.write(to_list)
                    to_file.flush()
                    diff_files(
                        from_file.name,
                        to_file.name,
                        str(from_index),
                        str(to_index),
                    )

                return

            changes = {}
            if from_hash != to_hash:
                changes["Systemfile"] = from_hash[:9], to_hash[:9]

            if from_image != to_image:
                changes[from_image] = from_version, None
                changes[to_image] = None, to_version

            elif from_id != to_id:
                changes[from_image] = from_version, to_version

            changes.update(diff_dicts(from_deployment.packages, to_deployment.packages))
            print_file_changes(from_deployment, to_deployment, changes, output)

        case Selection.CONTEXT:
            print_file_changes(
                from_deployment,
                to_deployment,
                diff_dicts(
                    context_files(from_deployment),
                    context_files(to_deployment),
                ),
                output,
            )

        case Selection.FULL:
            diff_output: list[bytes] = []
            ostree(
                "diff",
                from_deployment.checksum,
                to_deployment.checksum,
                onstdout=diff_output.append,
            )
            changes = {}
            for line in b"".join(diff_output).decode("utf-8").splitlines():
                if not line:
                    continue

                path = line[1:].strip().lstrip("/")
                if os.path.isdir(f"{from_deployment.path}/{path}") or os.path.isdir(
                    f"{to_deployment.path}/{path}"
                ):
                    continue

                match line[0]:
                    case "A":
                        changes[path] = None, ""

                    case "D":
                        changes[path] = "", None

                    case "M":
                        changes[path] = "", ""

                    case _:
                        pass

            if changes:
                print_file_changes(
                    from_deployment,
                    to_deployment,
                    dict(sorted(changes.items())),
                    output,
                )


if __name__ == "__main__":
    parser = ArgumentParser(
        **cast(dict[str, Any], kwds),  # pyright:ignore [reportAny,reportExplicitAny]
    )
    register(parser)
    args = parser.parse_args()
    command(args)
