import traceback
import subprocess
import json
import os

import flet as ft
import kdl

from typing import cast
from typing import Any

from settingspanel import SettingsPanel
from monitor import Monitor

CONFIG_PATH = os.path.expanduser("~/.config/niri/monitors.kdl")


def main(page: ft.Page):
    page.title = "Niri Monitor Configuration"

    def on_close() -> None:
        nonlocal closed
        closed = True

    page.on_close = lambda _: on_close()

    closed: bool = False
    selected_monitor_name: str | None = None
    primary_monitor_name: str | None = None
    canvas_width: float = 0.0
    canvas_height: float = 0.0
    canvas_scale_factor: float = 1.0
    canvas_min_x: int = 0
    canvas_min_y: int = 0
    outputs: dict[str, dict[str, Any]] = {}

    status_text = ft.Text("", size=14, color="gray")
    canvas = ft.Stack(expand=True, on_size_change=lambda e: on_canvas_resize(e))
    settings_panel = SettingsPanel(
        on_resolution_change=lambda _: update(),
        on_scale_change=lambda _: update(),
        on_vrr_change=lambda _: update(),
        on_make_primary_click=lambda _: on_make_primary_click(),
        on_x_change=lambda _: update(),
        on_y_change=lambda _: update(),
        on_apply=lambda m, e: on_apply(e),
        on_reset=lambda _: on_reset(),
    )
    page.add(
        ft.Column(
            [
                ft.Text(
                    "Niri Monitor Configuration",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                status_text,
                ft.Divider(),
                ft.Row(
                    [
                        ft.Container(
                            content=canvas,
                            expand=True,
                            border=ft.Border.all(2, "gray"),
                            padding=5,
                        ),
                        settings_panel,
                    ],
                    expand=True,
                    spacing=10,
                ),
            ],
            expand=True,
            spacing=10,
        )
    )

    def update() -> None:
        update_status()
        update_canvas_display()

    def on_make_primary_click() -> None:
        nonlocal selected_monitor_name
        nonlocal primary_monitor_name

        if not selected_monitor_name:
            return

        if primary_monitor_name:
            monitor = get_monitor(primary_monitor_name)
            if monitor:
                monitor.pending.add("primary")

        primary_monitor_name = selected_monitor_name
        update()

    def update_status() -> None:
        nonlocal selected_monitor_name
        status_text.value = ""
        if selected_monitor_name is None:
            return

        monitor = get_monitor(selected_monitor_name)
        if monitor is None or not monitor.pending:
            return

        status_text.value = "Pending changes"
        status_text.color = "orange"

    def on_canvas_resize(e: ft.LayoutSizeChangeEvent[ft.LayoutControl]) -> None:
        nonlocal canvas_width
        nonlocal canvas_height
        canvas_width = e.width
        canvas_height = e.height
        update_canvas_display()

    def calculate_scaling_factor() -> None:
        nonlocal outputs
        nonlocal canvas_width
        nonlocal canvas_height
        nonlocal canvas_scale_factor
        nonlocal canvas_min_x
        nonlocal canvas_min_y
        canvas_max_x: int = 0
        canvas_max_y: int = 0
        for name, output in outputs.items():
            outputs[name] = output
            monitor = get_monitor(name)
            if monitor:
                x, y = monitor.position
                width, height = monitor.resolution
                width = int(width / monitor.monitor_scale)
                height = int(height / monitor.monitor_scale)

            else:
                logical = cast(dict[str, int], output.get("logical", {}))
                x = logical.get("x", 0)
                y = logical.get("y", 0)
                width = logical.get("width", 1920)
                height = logical.get("height", 1080)

            canvas_min_x = min(x, canvas_min_x)
            canvas_min_y = min(y, canvas_min_y)
            canvas_max_x = max(x + width, canvas_max_x)
            canvas_max_y = max(y + height, canvas_max_y)

        canvas_scale_factor = (
            min(
                canvas_width / max(canvas_max_x - canvas_min_x, 1),
                canvas_height / max(canvas_max_y - canvas_min_y, 1),
            )
            * 0.95
        )

    def update_canvas_controls() -> None:
        for monitor in canvas.controls:
            try:
                monitor.update()

            except RuntimeError:
                pass

    def is_primary_monitor(monitor: Monitor) -> bool:
        nonlocal primary_monitor_name
        return monitor.name == primary_monitor_name

    def is_selected_monitor(monitor: Monitor) -> bool:
        nonlocal selected_monitor_name
        return monitor.name == selected_monitor_name

    def layout_monitor(monitor: Monitor) -> None:
        nonlocal canvas_scale_factor
        nonlocal canvas_min_x
        nonlocal canvas_min_y
        monitor.left = (monitor.left - canvas_min_x) * canvas_scale_factor
        monitor.top = (monitor.top - canvas_min_y) * canvas_scale_factor
        monitor.width *= canvas_scale_factor
        monitor.height *= canvas_scale_factor

    def update_canvas_display() -> None:
        nonlocal outputs
        nonlocal canvas_scale_factor
        """Update canvas without re-fetching from niri - just refreshes the display based on current data"""
        try:
            valid_outputs = list(outputs.keys())
            calculate_scaling_factor()
            for name, output in outputs.items():
                logical = output.get("logical", {})

                x = cast(int, logical.get("x", 0))
                y = cast(int, logical.get("y", 0))
                scale = cast(float, logical.get("scale", 1.0))
                mode = output.get("modes", [{}])[output.get("current_mode", 0)]
                width = cast(int, mode.get("width", 1920))
                height = cast(int, mode.get("height", 1080))

                monitor = get_monitor(name)
                if monitor is None:
                    monitor = Monitor(
                        name,
                        (width, height),
                        (x, y),
                        scale,
                        cast(bool, logical.get("vrr", False)),
                        lambda _, n=name: select_monitor_by_name(n),
                        is_primary=is_primary_monitor,
                        is_selected=is_selected_monitor,
                        on_layout=lambda m: layout_monitor(m),
                    )
                    canvas.controls.append(monitor)

                else:
                    if "scale" not in monitor.pending:
                        monitor.monitor_scale = scale

                    if "resolution" not in monitor.pending:
                        monitor.resolution = (width, height)

                    if "position" not in monitor.pending:
                        monitor.position = (x, y)

            for monitor in list(canvas.controls):
                if monitor.name not in valid_outputs:
                    canvas.controls.remove(monitor)

        except Exception as e:
            print(traceback.print_exc())
            status_text.value = f"Error: {e}"

        finally:
            page.schedule_update()
            update_canvas_controls()

    def get_monitor(name: str) -> Monitor | None:
        for monitor in canvas.controls:
            if monitor.name == name:
                return monitor

        return None

    def select_monitor_by_name(name: str) -> None:
        output = outputs.get(name)
        if output:
            select_monitor(output)

    def select_monitor(output: dict[str, Any]) -> None:
        nonlocal selected_monitor_name
        nonlocal primary_monitor_name
        selected_monitor_name = cast(str | None, output.get("name"))
        if not selected_monitor_name:
            settings_panel.monitor = None
            update_canvas_controls()
            return

        monitor = get_monitor(selected_monitor_name)
        settings_panel.monitor = monitor
        update_canvas_controls()
        if not monitor:
            return

        # Get available modes and populate dropdown
        modes = output.get("modes", [])
        mode_options = []
        seen = set()
        for mode in modes:
            mode_str = f"{mode['width']}x{mode['height']}"
            if mode_str not in seen:
                seen.add(mode_str)
                mode_options.append(ft.dropdown.Option(mode_str))

        # Sort by resolution (largest first)
        mode_options.sort(
            key=lambda opt: (int(opt.key.split("x")[0]), int(opt.key.split("x")[1])),
            reverse=True,
        )
        settings_panel.resolution_dropdown.options = mode_options
        w, h = monitor.resolution
        settings_panel.resolution_dropdown.value = f"{w}x{h}"
        settings_panel.scale_slider.value = monitor.monitor_scale
        settings_panel.scale_input.value = str(monitor.monitor_scale)
        settings_panel.vrr_switch.value = monitor.vrr
        x, y = monitor.position
        settings_panel.pos_x_input.value = str(x)
        settings_panel.pos_y_input.value = str(y)
        settings_panel.primary_button.disabled = monitor.primary
        monitor.update()
        update()

    def refresh_monitors(e=None) -> None:
        nonlocal primary_monitor_name
        nonlocal outputs
        try:
            result = subprocess.run(
                ["niri", "msg", "--json", "outputs"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                status_text.value = f"Error: niri returned {result.returncode}"
                status_text.color = "red"
                page.schedule_update()
                return

            outputs = cast(dict[str, dict[str, Any]], json.loads(result.stdout))
            primary_monitor_name = get_primary_monitor()

            if not outputs:
                status_text.value = "No monitors connected"
                status_text.color = "red"

            else:
                status_text.value = ""

            update_canvas_display()
            if selected_monitor_name:
                select_monitor_by_name(selected_monitor_name)

            page.schedule_update()

        except Exception as e:
            print(traceback.print_exc())
            status_text.value = f"Error: {e}"
            status_text.color = "red"
            page.schedule_update()

    def get_primary_monitor() -> str | None:
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r") as f:
                    doc = kdl.parse(f.read())
                    for node in doc.nodes:
                        if node.name == "output" and node.args:
                            name = str(node.args[0])
                            for child in node.nodes:
                                if child.name == "focus-at-startup":
                                    return name
        except Exception:
            print(traceback.print_exc())

        return None

    def write_kdl_config() -> None:
        """Write monitor configuration to ~/.config/monitors.kdl"""
        nonlocal primary_monitor_name
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

            kdl_config = kdl.Document()
            for monitor in sorted(
                cast(list[Monitor], canvas.controls), key=lambda x: x.name
            ):
                vrr_node = kdl.Node(name="variable-refresh-rate")
                if not monitor.vrr:
                    vrr_node.props["on-demand"] = True

                x, y = monitor.position
                nodes = [
                    kdl.Node(name="scale", args=[monitor.monitor_scale]),
                    kdl.Node(
                        name="position",
                        args=[],
                        props={"x": x, "y": y},
                    ),
                    vrr_node,
                ]
                if monitor.primary:
                    nodes.append(kdl.Node(name="focus-at-startup"))

                output_node = kdl.Node(
                    name="output",
                    args=[monitor.name],
                    nodes=nodes,
                )
                kdl_config.nodes.append(output_node)

            # Write to file
            with open(CONFIG_PATH, "w") as f:
                f.write(kdl_config.print())

        except Exception as e:
            print(traceback.print_exc())
            status_text.value = f"Error writing KDL config: {e}"
            status_text.color = "red"
            page.schedule_update()

    def on_apply(errors: list[str]) -> None:
        update_status()
        if errors:
            status_text.value = f"Errors: {'; '.join(errors)}"
            status_text.color = "red"

        else:
            write_kdl_config()
            status_text.value = "Applied settings"
            status_text.color = "green"

        refresh_monitors()

    def on_reset() -> None:
        nonlocal primary_monitor_name
        update_status()
        primary_monitor_name = get_primary_monitor()
        status_text.value = "All changes reset"
        status_text.color = "gray"
        update_canvas_display()

    refresh_monitors()


if __name__ == "__main__":
    ft.run(main)
