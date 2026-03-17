import dbus  # pyright:ignore [reportMissingTypeStubs]
import dbus.service  # pyright:ignore [reportMissingTypeStubs]
import grp
import pwd

from dbus.mainloop.glib import DBusGMainLoop  # pyright:ignore [reportMissingTypeStubs,reportUnknownVariableType]
from gi.repository import GLib  # pyright:ignore [reportMissingTypeStubs,reportUnknownVariableType,reportAttributeAccessIssue]

from typing import Callable
from typing import cast
from .console import print_stderr


def checkupdates(
    force: bool = False,
    onstderr: Callable[[str], None] = print_stderr,
) -> list[str]:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.checkupdates",
    )
    if not force:
        updates = cast(Callable[[], list[str]], interface.updates)()
        if updates:
            return updates

    loop = GLib.MainLoop()  # pyright:ignore [reportUnknownMemberType,reportUnknownVariableType]

    def on_status(status: str):
        setattr(on_status, "status", status)
        if status in ["error", "none", "available"]:
            loop.quit()  # pyright:ignore [reportUnknownMemberType]

    connect_to_signal = cast(
        Callable[[str, Callable[[str], None]], None],
        interface.connect_to_signal,
    )
    connect_to_signal("checkupdates_status", on_status)
    connect_to_signal("checkupdates_stderr", onstderr)
    cast(Callable[[], None], interface.checkupdates)()

    loop.run()  # pyright:ignore [reportUnknownMemberType]
    if getattr(on_status, "status") == "error":
        raise Exception("Checkupdates failed")

    return cast(Callable[[], list[str]], interface.updates)()


def pull(
    onstdout: Callable[[str], None] = print,
    onstderr: Callable[[str], None] = print_stderr,
):
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.pull",
    )
    loop = GLib.MainLoop()  # pyright:ignore [reportUnknownMemberType,reportUnknownVariableType]

    def on_status(status: str):
        print(f"Status: {status}")
        setattr(on_status, "status", status)
        if status in ["error", "success"]:
            loop.quit()  # pyright:ignore [reportUnknownMemberType]

    connect_to_signal = cast(
        Callable[[str, Callable[[str], None]], None],
        interface.connect_to_signal,
    )
    connect_to_signal("pull_stdout", onstdout)
    connect_to_signal("pull_stderr", onstderr)
    connect_to_signal("pull_status", on_status)
    cast(Callable[[], None], interface.pull)()

    loop.run()  # pyright:ignore [reportUnknownMemberType]
    if getattr(on_status, "status") == "error":
        raise Exception("Base image pull failed")


def upgrade(
    onstdout: Callable[[str], None] = print,
    onstderr: Callable[[str], None] = print_stderr,
    onprogress: Callable[[int], None] = lambda _: None,
):
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.upgrade",
    )
    loop = GLib.MainLoop()  # pyright:ignore [reportUnknownMemberType,reportUnknownVariableType]

    def on_status(status: str):
        onstderr(f"Status: {status}")
        setattr(on_status, "status", status)
        if status in ["error", "success"]:
            loop.quit()  # pyright:ignore [reportUnknownMemberType]

    connect_to_signal = cast(
        Callable[[str, Callable[..., None]], None],
        interface.connect_to_signal,
    )
    connect_to_signal("upgrade_stdout", onstdout)
    connect_to_signal("upgrade_stderr", onstderr)
    connect_to_signal("upgrade_status", on_status)
    connect_to_signal("progress", onprogress)
    cast(Callable[[], None], interface.upgrade)()

    loop.run()  # pyright:ignore [reportUnknownMemberType]
    if getattr(on_status, "status") == "error":
        raise Exception("Upgrade failed")


def upgrade_status() -> str:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.upgrade",
    )
    return cast(Callable[[], str], interface.status)()


def build(
    onstdout: Callable[[str], None] = print,
    onstderr: Callable[[str], None] = print_stderr,
    onprogress: Callable[[int], None] = lambda _: None,
):
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.build",
    )
    loop = GLib.MainLoop()  # pyright:ignore [reportUnknownMemberType,reportUnknownVariableType]

    def on_status(status: str):
        onstderr(f"Status: {status}")
        setattr(on_status, "status", status)
        if status in ["error", "success"]:
            loop.quit()  # pyright:ignore [reportUnknownMemberType]

    connect_to_signal = cast(
        Callable[[str, Callable[..., None]], None],
        interface.connect_to_signal,
    )
    connect_to_signal("build_stdout", onstdout)
    connect_to_signal("build_stderr", onstderr)
    connect_to_signal("build_status", on_status)
    connect_to_signal("progress", onprogress)
    cast(Callable[[], None], interface.build)()

    loop.run()  # pyright:ignore [reportUnknownMemberType]
    if getattr(on_status, "status") == "error":
        raise Exception("Build failed")


def build_status() -> str:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    interface = dbus.Interface(
        bus.get_object(  # pyright:ignore [reportUnknownMemberType]
            "os.system",
            "/system",
        ),
        "system.build",
    )
    return cast(Callable[[], str], interface.status)()


def groups_for_sender(obj: dbus.service.Object, sender: str) -> set[str]:
    userid = cast(
        Callable[[str], int],
        obj.connection.get_unix_user,  # pyright:ignore [reportAttributeAccessIssue,reportUnknownMemberType]
    )(sender)
    user = pwd.getpwuid(userid).pw_name
    return set([x.gr_name for x in grp.getgrall() if user in x.gr_mem])
