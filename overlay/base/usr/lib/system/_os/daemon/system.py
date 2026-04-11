import os
import subprocess
import threading
import time
import traceback
from collections.abc import Callable
from typing import cast

import dbus  # pyright:ignore [reportMissingTypeStubs]
import dbus.service  # pyright:ignore [reportMissingTypeStubs]

from .. import SYSTEM_PATH
from ..console import (
    bytes_to_stderr,
    bytes_to_stdout,
)
from ..dbus import groups_for_sender
from ..ostree import (
    commit_export,
    deploy,
    prune,
)
from ..podman import (
    build,
    image_digest,
    image_exists,
    pull,
)
from ..system import (
    baseImage,
    checkupdates,
    system_kernelCommandLine,
    update_bootloader,
)


class Object(dbus.service.Object):
    def __init__(self, bus_name: dbus.service.BusName):
        super().__init__(  # pyright:ignore [reportUnknownMemberType]
            bus_name=bus_name,
            object_path="/system",
        )
        self._updates: list[str] = []
        self._updates_ttl: float = time.time()
        self._notification: dict[str, str] = {}
        self._upgrade_status: str = ""
        self._build_status: str = ""
        self._pull_status: str = ""
        self._checkupdates_status: str = ""
        self._upgrade_progress: int = 0
        self._build_progress: int = 0
        self._upgrade_event: threading.Event = threading.Event()
        self._upgrade_progress_status: tuple[int, int] = (0, 0)
        self._upgrade_step_progress_status: tuple[int, int] = (0, 0)
        self._upgrade_dkms_progress_status: tuple[int, int] = (0, 0)
        self._build_step_progress_status: tuple[int, int] = (0, 0)
        self._build_dkms_progress_status: tuple[int, int] = (0, 0)
        self._upgrade_thread: threading.Thread | None = None
        self._build_thread: threading.Thread | None = None
        self._pull_thread: threading.Thread | None = None
        self._checkupdates_thread: threading.Thread | None = None

    def notify_all(self, msg: str, action: str):
        for path in os.scandir("/run/user"):
            if not path.is_dir():
                continue

            uid = path.name
            if uid == "0":
                continue

            user = (
                subprocess.check_output(["id", "-u", "-n", uid]).decode("utf-8").strip()
            )
            # TODO use org.freedesktop.Notifications over dbus intead
            args = [
                "sudo",
                "-u",
                user,
                f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
                "notify-send",
                "--print-id",
                "--urgency=normal",
            ]
            if action in self._notification:
                args.append(f"--replace-id={self._notification[action]}")

            try:
                self._notification[action] = (
                    subprocess.check_output([*args, msg]).strip().decode("utf-8")
                )

            except subprocess.CalledProcessError as e:
                print(e)
                output = cast(bytes | None, e.output)
                if output is not None:
                    print(output.strip().decode("utf-8"))

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        sender_keyword="sender",
        async_callbacks=("success", "error"),
    )
    def upgrade(
        self,
        success: Callable[[], None],
        error: Callable[..., None],
        sender: str | None = None,
    ):
        try:
            assert sender is not None
            if not set(["adm", "wheel", "root"]) & groups_for_sender(self, sender):
                error("Permission denied")
                return

            if self._upgrade_status == "pending":
                success()
                return

            assert self._upgrade_thread is None
            self.upgrade_status("pending")
            self._upgrade_thread = threading.Thread(
                target=self._upgrade, args=(sender,)
            )
            self._upgrade_thread.start()
            success()

        except BaseException as e:
            error(f"Exception: {e}\n{traceback.format_exc()}")

    def _upgrade(self, sender: str):
        self.notify_all("Starting system upgrade", "upgrade")
        try:
            self.upgrade_stderr(b"PROGRESS 1/5 Building system:latest\n")
            if not os.path.exists("/ostree"):
                self.upgrade_stderr(b"OSTree repo missing")
                self.upgrade_status("error")
                self.notify_all("System upgrade failed", "upgrade")
                return

            if not os.path.exists(SYSTEM_PATH):
                os.makedirs(SYSTEM_PATH, exist_ok=True)

            def onerror(msg: str):
                self.upgrade_status("error")
                self.upgrade_stderr(f"Build failed: {msg}\n".encode())
                self._upgrade_event.set()

            self.build(lambda: None, onerror, sender)
            while self._build_status == "pending":
                _ = self._upgrade_event.wait()
                self._upgrade_event.clear()

            if self._build_status == "error":
                self.upgrade_status("error")
                self.notify_all("System upgrade failed", "upgrade")
                return

            self.upgrade_stderr(b"PROGRESS 2/5 Committing to ostree\n")
            commit_export(
                onstdout=self.upgrade_stdout,
                onstderr=self.upgrade_stderr,
            )
            self.upgrade_stderr(b"PROGRESS 3/5 Pruning ostree\n")
            prune(onstdout=self.upgrade_stdout, onstderr=self.upgrade_stderr)
            self.upgrade_stderr(b"PROGRESS 4/5 Deploying ostree\n")
            deploy(
                onstdout=self.upgrade_stdout,
                onstderr=self.upgrade_stderr,
            )
            self.upgrade_stderr(b"PROGRESS 5/5 Updating bootloader\n")
            update_bootloader(
                onstdout=self.upgrade_stdout,
                onstderr=self.upgrade_stderr,
            )
            self.upgrade_stderr(b"[system] Done\n")
            self.upgrade_progress(100)
            self.upgrade_status("success")
            self.notify_all("System upgrade complete, reboot required", "upgrade")

        except BaseException as e:
            self.upgrade_stderr(
                f"Exception: {e}\n{traceback.format_exc()}".encode("utf-8")
            )
            self.upgrade_status("error")
            self.notify_all("System upgrade failed", "upgrade")

        finally:
            self._upgrade_thread = None

        return False

    def _upgrade_parse(self, line: bytes):
        if line.startswith(b"PROGRESS "):
            parts = line[9:].split(b"/", 1)
            if len(parts) != 2:
                self.upgrade_stderr(
                    f"Failed to parse PROGRESS: {line!r}\n\tNo b'/' found\n".encode()
                )
                return

            second_part = parts[1].split(b" ")
            try:
                current = int(parts[0])
                total = int(second_part[0])

            except ValueError as e:
                self.upgrade_stderr(
                    f"Failed to parse PROGRESS: {line!r}\n\t{e}\n".encode()
                )
                return

            self._upgrade_progress_status = (current, total)
            self._upgrade_step_progress_status = (0, 0)
            self._upgrade_dkms_progress_status = (0, 0)
            self._emit_upgrade_progress()

        elif line.startswith(b"STEP "):
            parts = line[5:].split(b"/", 1)
            if len(parts) != 2:
                self.upgrade_stderr(
                    f"Failed to parse STEP: {line!r}\n\tNo b'/' found\n".encode()
                )
                return

            second_part = parts[1].split(b":")
            try:
                current = int(parts[0])
                total = int(second_part[0])

            except ValueError as e:
                self.upgrade_stderr(f"Failed to parse STEP: {line!r}\n\t{e}\n".encode())
                return

            self._upgrade_step_progress_status = (current, total)
            self._upgrade_dkms_progress_status = (0, 0)
            self._emit_upgrade_progress()

        elif line.startswith(b"[dkms] ("):
            parts = line.split(b"(", 1)
            parts = parts[1].split(b"/", 1)
            if len(parts) != 2:
                self.upgrade_stderr(
                    f"Failed to parse [dkms]: {line!r}\n\tNo b'/' found\n".encode()
                )
                return

            second_part = parts[1].split(b")")
            try:
                current = int(parts[0])
                total = int(second_part[0])

            except ValueError as e:
                self.upgrade_stderr(
                    f"Failed to parse [dkms]: {line!r}\n\t{e}\n".encode()
                )
                return

            self._upgrade_dkms_progress_status = (current, total)
            self._emit_upgrade_progress()

    def _emit_upgrade_progress(self) -> None:
        if self._upgrade_thread is None:
            return

        build_scale = 0.8  # How much of the bar should the build step be?
        status_current, status_total = self._upgrade_progress_status
        assert status_total
        build_scale_100 = 1 + build_scale
        total = status_total * build_scale_100
        current = status_current - 1
        # The build step takes up 80% of the bar, so any steps after it need to adjust
        if current:
            current = (
                build_scale
                + (status_current - 2) / (status_total - 1) * (1 - build_scale)
            ) * total

        dkms_current, dkms_total = self._upgrade_dkms_progress_status
        step_current, step_total = self._upgrade_step_progress_status
        if dkms_total > 0:
            dkms_percent = (dkms_current - 1) / dkms_total
            step_percent = (dkms_percent + step_current - 1) / step_total
            current += total * build_scale * step_percent

        elif step_total > 0:
            step_percent = (step_current - 1) / step_total
            current += total * build_scale * step_percent

        self.upgrade_progress(round(current / total * 100))

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        signature="s",
    )
    def upgrade_status(self, status: str):
        self._upgrade_status = status
        print(f"upgrade status: {status}")

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        signature="s",
    )
    def upgrade_stdout(self, stdout: bytes):
        bytes_to_stdout(b"[upgrade:1] " + stdout)
        self._upgrade_parse(stdout)

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        signature="s",
    )
    def upgrade_stderr(self, stderr: bytes):
        bytes_to_stderr(b"[upgrade:2] " + stderr)
        self._upgrade_parse(stderr)

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        signature="i",
    )
    def upgrade_progress(self, progress: int):
        self._upgrade_progress = progress
        print(f"Upgrade progress: {progress}")

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        out_signature="i",
    )
    def progress_status(self) -> int:
        return 0 if self._upgrade_thread is None else self._upgrade_progress

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.upgrade",
        out_signature="s",
    )
    def get_upgrade_status(self) -> str:
        return self._upgrade_status

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        in_signature="",
        out_signature="",
        sender_keyword="sender",
        async_callbacks=("success", "error"),
    )
    def build(
        self,
        success: Callable[[], None],
        error: Callable[..., None],
        sender: str | None = None,
    ):
        try:
            assert sender is not None
            if not set(["adm", "wheel", "root"]) & groups_for_sender(self, sender):
                error("Permission denied")
                return

            if self._build_status == "pending":
                success()
                return

            assert self._build_thread is None
            self.build_status("pending")
            self._build_thread = threading.Thread(target=self._build)
            self._build_thread.start()
            success()

        except BaseException as e:
            error(f"Exception: {e}\n{traceback.format_exc()}")

    def _emit_build_progress(self) -> None:
        status_current, status_total = self._build_step_progress_status
        assert status_total
        current = status_current - 1
        dkms_current, dkms_total = self._build_dkms_progress_status
        if dkms_total > 0:
            step_percent = (dkms_current - 1) / dkms_total
            current += status_total * step_percent

        self.build_progress(round(current / status_total * 100))

    def _build_parse(self, line: bytes):
        if line.startswith(b"STEP "):
            parts = line[5:].split(b"/", 1)
            if len(parts) != 2:
                self.upgrade_stderr(
                    f"Failed to parse STEP: {line!r}\n\tNo b'/' found\n".encode()
                )
                return

            second_part = parts[1].split(b":")
            try:
                current = int(parts[0])
                total = int(second_part[0])

            except ValueError as e:
                self.upgrade_stderr(f"Failed to parse STEP: {line!r}\n\t{e}\n".encode())
                return

            self._build_step_progress_status = (current, total)
            self._build_dkms_progress_status = (0, 0)
            self._emit_build_progress()

        elif line.startswith(b"[dkms] ("):
            parts = line.split(b"(", 1)
            parts = parts[1].split(b"/", 1)
            if len(parts) != 2:
                self.upgrade_stderr(
                    f"Failed to parse [dkms]: {line!r}\n\tNo b'/' found\n".encode()
                )
                return

            second_part = parts[1].split(b")")
            try:
                current = int(parts[0])
                total = int(second_part[0])

            except ValueError as e:
                self.upgrade_stderr(
                    f"Failed to parse [dkms]: {line!r}\n\t{e}\n".encode()
                )
                return

            self._build_dkms_progress_status = (current, total)
            self._emit_build_progress()

    def _build(self):
        self.notify_all("Building system image", "build")
        try:
            build(
                buildArgs={"KARGS": system_kernelCommandLine()},
                onstdout=self.build_stdout,
                onstderr=self.build_stderr,
            )
            self.build_stderr(b"[system] Done\n")
            self.build_progress(100)
            self.build_status("success")
            self.notify_all("System image built successfully", "build")

        except BaseException as e:
            self.build_stderr(
                f"Exception: {e}\n{traceback.format_exc()}".encode("utf-8")
            )
            self.build_status("error")
            self.notify_all("System build failed", "build")

        finally:
            self._build_thread = None

        return False

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        signature="i",
    )
    def build_progress(self, progress: int):
        self._build_progress = progress
        print(f"Build progress: {progress}")

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        signature="s",
    )
    def build_status(self, status: str):
        self._build_status = status
        print(f"build status: {status}")
        self._upgrade_event.set()

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        signature="s",
    )
    def build_stdout(self, stdout: bytes):
        bytes_to_stdout(b"[build:1] " + stdout)
        self._build_parse(stdout)
        if self._upgrade_thread is None:
            self._upgrade_parse(stdout)

        else:
            self.upgrade_stdout(stdout)

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        signature="s",
    )
    def build_stderr(self, stderr: bytes):
        bytes_to_stderr(b"[build:2] " + stderr)
        self._build_parse(stderr)
        if self._upgrade_thread is None:
            self._upgrade_parse(stderr)

        else:
            self.upgrade_stderr(stderr)

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.build",
        in_signature="",
        out_signature="s",
    )
    def get_build_status(self) -> str:
        return self._build_status

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.checkupdates",
        in_signature="",
        out_signature="",
        sender_keyword="sender",
        async_callbacks=("success", "error"),
    )
    def checkupdates(
        self,
        success: Callable[[], None],
        error: Callable[..., None],
        sender: str | None = None,
    ):
        try:
            assert sender is not None
            if not set(["adm", "wheel", "root"]) & groups_for_sender(self, sender):
                error("Permission denied")
                return

            if self._checkupdates_status == "pending":
                success()
                return

            assert self._checkupdates_thread is None
            self.checkupdates_status("pending")
            self._checkupdates_thread = threading.Thread(target=self._checkupdates)
            self._checkupdates_thread.start()
            success()

        except BaseException as e:
            error(f"Exception: {e}\n{traceback.format_exc()}")

    def _checkupdates(self):
        try:
            self._updates = checkupdates()
            self._updates_ttl = time.time() + 60 * 5  # recheck in 5 minutes
            if not self._updates:
                self.checkupdates_status("none")

            else:
                self.checkupdates_status("available")
                self.notify_all(
                    f"{len(self._updates)} updates available:\n"
                    + "\n".join(self._updates),
                    "checkupdates",
                )

        except subprocess.CalledProcessError as e:
            self.checkupdates_stderr(cast(bytes, e.stderr or e.output or b""))
            self.checkupdates_status("error")
            self.notify_all("Failed to checkupdates base image", "checkupdates")
            raise

        except BaseException as e:
            self.checkupdates_stderr(
                f"Exception: {e}\n{traceback.format_exc()}".encode("utf-8")
            )
            self.checkupdates_status("error")
            self.notify_all("Failed to checkupdates base image", "checkupdates")
            raise

        finally:
            self._checkupdates_thread = None

        return False

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.checkupdates",
        signature="s",
    )
    def checkupdates_status(self, status: str):
        self._checkupdates_status = status
        print(f"checkupdates status: {status}")

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.checkupdates",
        signature="s",
    )
    def checkupdates_stderr(self, stderr: bytes):
        bytes_to_stderr(b"[checkupdates:2] " + stderr)

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.checkupdates",
        in_signature="",
        out_signature="as",
    )
    def updates(self) -> list[str]:
        if time.time() >= self._updates_ttl:
            return []

        return self._updates

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.pull",
        in_signature="",
        out_signature="",
        sender_keyword="sender",
        async_callbacks=("success", "error"),
    )
    def pull(
        self,
        success: Callable[[], None],
        error: Callable[..., None],
        sender: str | None = None,
    ):
        try:
            assert sender is not None
            if not set(["adm", "wheel", "root"]) & groups_for_sender(self, sender):
                error("Permission denied")
                return

            if self._pull_status == "pending":
                success()
                return

            assert self._pull_thread is None
            self.pull_status("pending")
            self._pull_thread = threading.Thread(target=self._pull)
            self._pull_thread.start()
            success()

        except BaseException as e:
            error(f"Exception: {e}\n{traceback.format_exc()}")

    def _pull(self):
        self.notify_all("Pulling base image", "pull")
        try:
            image = baseImage()
            pull(
                image,
                onstdout=self.pull_stdout,
                onstderr=self.pull_stderr,
            )
            self.pull_status("success")
            self.notify_all("Base image pulled", "pull")

        except subprocess.CalledProcessError as e:
            self.pull_stderr(cast(bytes, e.stderr or e.output or b""))
            self.pull_status("error")
            self.notify_all("Failed to pull base image", "pull")
            raise

        except BaseException as e:
            self.pull_stderr(
                f"Exception: {e}\n{traceback.format_exc()}".encode("utf-8")
            )
            self.pull_status("error")
            self.notify_all("Failed to pull base image", "pull")
            raise

        finally:
            self._pull_thread = None

        return False

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.pull",
        signature="s",
    )
    def pull_status(self, status: str):
        self._pull_status = status
        print(f"pull status: {status}")

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.pull",
        signature="s",
    )
    def pull_stdout(self, stdout: bytes):
        bytes_to_stdout(b"[pull:1] " + stdout)

    @dbus.service.signal(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.pull",
        signature="s",
    )
    def pull_stderr(self, stderr: bytes):
        bytes_to_stderr(b"[pull:2] " + stderr)

    @dbus.service.method(  # pyright:ignore [reportUnknownMemberType]
        dbus_interface="system.pull",
        in_signature="",
        out_signature="b",
    )
    def pull_available(self) -> bool:
        image = baseImage()
        return not image_exists(image, remote=False) or (
            image_digest(image, remote=False) != image_digest(image, remote=True)
        )
