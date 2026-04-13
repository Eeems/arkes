import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from collections.abc import Callable
from typing import (
    Any,
    Literal,
    cast,
)

import _os  # pyright: ignore[reportMissingImports]
from podman import PodmanClient

from . import (
    REPO,
    _image_digests_write_cache,  # pyright: ignore[reportPrivateUsage]
    image_digest,
    image_labels,
    is_root,
    podman,
)

get_client = cast(Callable[[], PodmanClient], _os.podman.get_client)  # pyright: ignore[reportUnknownMemberType]

kwds: dict[str, str] = {
    "help": "Push one or more tags to the remote repository",
}


def register(parser: ArgumentParser) -> None:
    _ = parser.add_argument(
        "target",
        action="extend",
        nargs="+",
        type=str,
        metavar="TAG",
        help="Tag to push",
    )


def command(args: Namespace) -> None:
    if not is_root():
        print("Must be run as root", file=sys.stderr)
        sys.exit(1)

    for target in cast(list[str], args.target):
        push(target)


def push(target: str) -> None:
    client = get_client()
    image = f"{REPO}:{target}"
    _image = client.images.get(image)
    labels = image_labels(image, False)
    tags: list[str] = []
    if labels.get("os-release.VERSION", None):
        version = labels["os-release.VERSION"]
        version_id = labels.get("os-release.VERSION_ID", None)
        if version_id and version != version_id:
            tag = f"{target}_{version}.{version_id}"
            tags.append(tag)
            assert _image.tag(REPO, tag), "Failed to tag image"

        tag = f"{target}_{version}"
        tags.append(tag)
        assert _image.tag(REPO, tag), "Failed to tag image"

    for tag in [*tags, target]:
        image = f"{REPO}:{tag}"
        podman("push", "--retry=5", "--compression-format=zstd:chunked", image)
        print(f"Pushed {image}")
        _image_digests_write_cache(image, image_digest(image, False, False))

    results: list[
        dict[Literal["Deleted", "Untagged", "Errors", "ExitCode"], str | int]
    ] = []
    for tag in tags:
        results.extend(client.images.remove(f"{REPO}:{tag}"))

    errors = [x.get("Errors") for x in results if x.get("Errors") is not None]
    if errors:
        raise ExceptionGroup(
            "Failed to remove tags",
            [Exception(x) for x in errors],
        )


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
