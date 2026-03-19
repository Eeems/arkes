import os
import tempfile

from datetime import datetime
from datetime import UTC
from datetime import timedelta
from argparse import ArgumentParser
from argparse import Namespace
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from typing import Any
from typing import cast

from . import image_tags
from . import hex_to_base62
from . import progress_bar
from . import podman
from . import chronic
from . import podman_cmd
from . import escape_label
from . import _image_digest_cached  # pyright: ignore[reportPrivateUsage]
from . import _image_digests_write_cache  # pyright: ignore[reportPrivateUsage]
from . import REPO

from .config import parse_all_config


kwds: dict[str, str] = {
    "help": "Generate the manifest image",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "--push",
        action="store_true",
        help="Push the manifest after it builds",
    )


def _assertkind(tag: str, expected_kind: str):
    kind, _, _ = _classify_tag(tag)
    assert kind == expected_kind, f"{kind} != {expected_kind}: {tag}"


def command(args: Namespace) -> None:
    _assertkind("_manifest", "manifest")
    _assertkind("_x", "other")
    _assertkind("root!", "other")
    _assertkind("rootfs", "variant")
    _assertkind("rootfs_2025.11.18", "version")
    _assertkind("rootfs_2025.11.18.0", "build")

    config = parse_all_config()
    print("Getting all tags...")
    all_tags = image_tags(REPO, True)
    assert all_tags, "No tags found"
    digest_info: dict[str, tuple[list[str], str]] = {}
    digest_worker_queue: list[tuple[str, bool]] = []
    valid_variants = ["rootfs", *config["variants"].keys()]
    for tag in progress_bar(
        all_tags,
        prefix="Classifying tags:" + " " * 9,
    ):
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

    def _digest_worker(
        data: tuple[str, bool],
    ) -> tuple[str, Future[str] | str]:
        tag, skip = data
        image = f"{REPO}:{tag}"
        future = _image_digest_cached(image, skip_manifest=skip)
        if isinstance(future, Future):
            future.add_done_callback(
                lambda x: _image_digests_write_cache(image, x.result())
            )

        return tag, future

    with ThreadPoolExecutor(max_workers=50) as exc:
        for future in progress_bar(
            as_completed([exc.submit(_digest_worker, x) for x in digest_worker_queue]),
            count=len(digest_worker_queue),
            prefix="Getting tag digests:" + " " * 6,
        ):
            tag, digest = future.result()
            if isinstance(digest, Future):
                digest = digest.result()

            b62 = hex_to_base62(digest)
            if b62 not in digest_info:
                digest_info[b62] = ([], digest)

            digest_info[b62] = (digest_info[b62][0] + [tag], digest)

    labels: dict[str, str] = {}
    for b62, (tags, digest) in progress_bar(
        digest_info.items(), prefix="Generating tag labels:" + " " * 4
    ):
        for tag in tags:
            labels[f"tag.{tag}"] = digest

    labels["timestamp"] = datetime.now(tz=UTC).replace(microsecond=0).isoformat() + "Z"
    with tempfile.TemporaryDirectory() as tmpdir:
        containerfile = os.path.join(tmpdir, "Containerfile")
        with open(containerfile, "w") as f:
            _ = f.write("FROM scratch\nLABEL \\")
            for k, v in progress_bar(
                labels.items(), prefix="Generating Containerfile: "
            ):
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
