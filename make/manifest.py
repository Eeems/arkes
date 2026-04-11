import os
import subprocess
import tempfile
from argparse import (
    ArgumentParser,
    Namespace,
)
from collections.abc import (
    Callable,
    Generator,
)
from concurrent.futures import (
    Future,
    as_completed,
)
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import (
    Any,
    cast,
)

from . import (
    REPO,
    _os,  # pyright: ignore[reportPrivateUsage, reportPrivateLocalImportUsage]
    chronic,
    escape_label,
    image_digest_cached,
    image_labels,
    image_tags,
    podman,
    podman_cmd,
    progress_bar,
)
from .config import parse_all_config

_latest_manifest = cast(Callable[[], bool], _os.podman._latest_manifest)  # pyright:ignore [reportUnknownMemberType]

kwds: dict[str, str] = {
    "help": "Generate the manifest image",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--push",
        action="store_true",
        help="Push the manifest after it builds",
    )


def command(args: Namespace) -> None:
    _assertkind("_manifest", "manifest")
    _assertkind("_x", "other")
    _assertkind("root!", "other")
    _assertkind("rootfs", "variant")
    _assertkind("rootfs_2025.11.18", "version")
    _assertkind("rootfs_2025.11.18.0", "build")

    print("Getting latest manifest...")
    _ = _latest_manifest()
    print("Getting manifest labels...")
    try:
        manifest = image_labels(f"{REPO}:_manifest", True)

    except subprocess.CalledProcessError:
        manifest = {}

    config = parse_all_config()
    print("Getting all tags...")
    all_tags = image_tags(REPO, True)
    assert all_tags, "No tags found"
    digest_worker_queue: list[tuple[str, bool]] = []
    valid_variants = ["rootfs", *config["variants"].keys()]
    print("Classifying tags...")
    for tag in all_tags:
        kind, a, version = _classify_tag(tag)
        if kind in ("other", "manifest"):
            continue

        if kind not in ("build", "version", "variant"):
            digest_worker_queue.append((tag, False))
            continue

        assert a
        parts = a.split("-", 1)
        variant = parts[0]
        if variant not in valid_variants:
            continue

        if "-" in a and parts[1] not in [
            y
            for x in config["variants"].values()
            for y in cast(list[str], x.get("templates", []))
        ]:
            continue

        skip = True
        if kind in ("version", "build"):
            assert version is not None
            if kind == "build":
                version = version.rsplit(".", 1)[0]

            tag_date = datetime.strptime(version, "%Y.%m.%d")
            age = datetime.now(UTC).date() - tag_date.date()
            skip = age > timedelta(days=3)

        digest_worker_queue.append((tag, skip))

    assert digest_worker_queue, "No tags found"

    digest_queue: dict[Future[str], str] = {}
    digests: list[tuple[str, str]] = []
    print("Queuing digest requests...")
    for tag, skip in digest_worker_queue:
        digest = None
        if not skip:
            digest = manifest.get(f"arkes.manifest.tag.{tag}", None)

        if digest is not None:
            digests.append((tag, digest))
            continue

        future = image_digest_cached(f"{REPO}:{tag}", skip_manifest=skip)
        digest_queue[future] = tag

    labels: dict[str, str] = {}
    for tag, digest in progress_bar(
        _as_completed_digests(digests, digest_queue),
        prefix="Encoding digests... ",
        count=len(digest_worker_queue),
    ):
        labels[f"tag.{tag}"] = digest

    labels["timestamp"] = datetime.now(tz=UTC).replace(microsecond=0).isoformat() + "Z"
    print("Generating Containerfile...")
    with tempfile.TemporaryDirectory() as tmpdir:
        containerfile = os.path.join(tmpdir, "Containerfile")
        with open(containerfile, "w") as f:
            _ = f.write("FROM scratch\nLABEL \\")
            for k, v in labels.items():
                _ = f.write(f'\n  arkes.manifest.{k}="{escape_label(v)}" \\')

            _ = f.write('\n  arkes.manifest.version="1"\n')

        image = f"{REPO}:_manifest"
        print(f"Building {image}...")
        try:
            chronic(
                podman_cmd(
                    "build",
                    f"--tag={image}",
                    f"--file={containerfile}",
                    tmpdir,
                )
            )

        except Exception:
            tmppath = f"/tmp/{os.getpid()}.manifest.Containerfile"
            with (
                open(containerfile, "r") as f,
                open(tmppath, "w") as out,
            ):
                _ = out.write(f.read())

            print(f"Containerfile: {tmppath}")
            raise
        if cast(bool, args.push):
            podman("push", image)


def _assertkind(tag: str, expected_kind: str) -> None:
    kind, _, _ = _classify_tag(tag)
    assert kind == expected_kind, f"{kind} != {expected_kind}: {tag}"


def _as_completed_digests(
    digests: list[tuple[str, str]], digest_queue: dict[Future[str], str]
) -> Generator[tuple[str, str]]:
    yield from digests
    for future in as_completed(digest_queue.keys()):
        yield digest_queue[future], future.result()


def _classify_tag(tag: str) -> tuple[str, str | None, str | None]:
    if tag.startswith("_"):
        if tag == "_manifest":
            return "manifest", None, None

        return "other", None, None

    if "_" not in tag:
        if all(c.isalnum() or c == "-" for c in tag):
            return "variant", tag, None

        return "other", None, None

    sep_idx = tag.rfind("_")
    if sep_idx <= 0:
        return "other", None, None

    variant = tag[:sep_idx]
    rest = tag[sep_idx + 1 :]
    if not (variant and all(c.isalnum() or c == "-" for c in variant)):
        return "other", None, None

    if "." in rest:
        last_dot = rest.rfind(".")
        if last_dot > 0:
            build_num = rest[last_dot + 1 :]
            if build_num.isdigit():
                version_part = rest[:last_dot]
                if version_part.count(".") >= 2:
                    full_version = f"{version_part}.{build_num}"
                    return "build", variant, full_version

    if rest and all(c.isalnum() or c in ".-" for c in rest):
        return "version", variant, rest

    return "other", None, None


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
