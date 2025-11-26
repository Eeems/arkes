import sys
import _os  # pyright: ignore[reportMissingImports]

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast
from typing import Literal
from typing import Callable
from podman import PodmanClient

from . import is_root
from . import image_labels
from . import podman
from . import image_digest
from . import _image_digests_write_cache  # pyright: ignore[reportPrivateUsage]
from . import REPO

get_client = cast(Callable[[], PodmanClient], _os.podman.get_client)  # pyright: ignore[reportUnknownMemberType]

kwds: dict[str, str] = {
    "help": "Push one or more tags to the remote repository",
}


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "target",
        action="extend",
        nargs="+",
        type=str,
        metavar="TAG",
        help="Tag to push",
    )


def command(args: Namespace):
    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    for target in cast(list[str], args.target):
        push(target)


def push(target: str):
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

    for tag in [*tags, image]:
        tag = f"{REPO}:{tag}"
        podman("push", "--retry=5", "--compression-format=zstd:chunked", tag)
        print(f"Pushed {tag}")
        _image_digests_write_cache(tag, image_digest(tag, False))

    results: list[
        dict[Literal["Deleted", "Untagged", "Errors", "ExitCode"], str | int]
    ] = []
    for tag in tags:
        results.extend(client.images.remove(f"{REPO}:{tag}"))

    results = [x for x in results if x.get("ExitCode") != 0]
    if results:
        raise ExceptionGroup(  # noqa: F821
            "Failed to remove tags",
            [
                Exception(
                    f"{x.get('ExitCode')} {x.get('Errors', 'Unknown')}" for x in results
                )
            ],
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
