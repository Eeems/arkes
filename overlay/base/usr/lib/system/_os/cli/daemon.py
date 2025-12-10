import sys
import os
import importlib
import dbus  # pyright:ignore [reportMissingTypeStubs]
import dbus.service  # pyright:ignore [reportMissingTypeStubs]

from typing import cast
from typing import Callable
from dbus.mainloop.glib import DBusGMainLoop  # pyright:ignore [reportMissingTypeStubs,reportUnknownVariableType]
from gi.repository import GLib  # pyright:ignore [reportMissingTypeStubs,reportUnknownVariableType,reportAttributeAccessIssue]
from argparse import ArgumentParser
from argparse import Namespace
from glob import iglob

from ..system import is_root
from ..system import chronic


def register(parser: ArgumentParser):
    _ = parser.add_argument(
        "--list-modules",
        dest="listModules",
        action="store_true",
        help="Display list of configured daemon modules and exit",
    )


POLICY = """
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="root">
    <allow own="os.system"/>
  </policy>
  <policy context="default">
    <allow send_destination="os.system"/>
    <allow receive_sender="os.system" receive_type="signal"/>
  </policy>
</busconfig>
"""


def command(args: Namespace):
    if cast(bool, args.listModules):
        print("Modules:")
        print("\n".join([f"  {x}" for x in modules()]))
        return

    if not is_root():
        print("Must be run as root")
        sys.exit(1)

    os.makedirs("/etc/dbus-1/system.d", exist_ok=True)
    with open("/etc/dbus-1/system.d/os.conf", "w") as f:
        _ = f.write(POLICY)

    chronic("systemctl", "reload", "dbus")
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    bus_name = cast(dbus.service.BusName, dbus.service.BusName("os.system", bus))
    objects: list[dbus.service.Object] = []
    for name in modules():
        parent = ".".join(__name__.split(".")[:-2])
        module = importlib.import_module(f"{parent}.daemon.{name}", parent)
        objects.append(
            cast(
                Callable[[dbus.service.BusName], dbus.service.Object],
                module.Object,
            )(bus_name)
        )

    GLib.MainLoop().run()  # pyright:ignore [reportUnknownMemberType]


def modules() -> list[str]:
    if "__compiled__" in globals():
        from ..daemon import __all__  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]

        return cast(list[str], __all__)

    return [
        os.path.splitext(os.path.basename(x))[0]
        for x in iglob(os.path.join(os.path.dirname(__file__), "..", "daemon", "*.py"))
        if not x.endswith("__.py")
    ]


if __name__ == "__main__":
    parser = ArgumentParser()
    register(parser)
    args = parser.parse_args()
    command(args)
