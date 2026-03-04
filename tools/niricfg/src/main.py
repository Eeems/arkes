import subprocess
import json
import threading
import os

import flet as ft
import kdl

from typing import cast
from typing import Any


def main(page: ft.Page):
    page.title = "Niri Monitor Configuration"

    selected_monitor_name: str | None = None
    primary_monitor_name: str | None = None
    pending_changes: dict[str, Any] = {}
    monitors_data: dict[str, Any] = {}

    header = ft.Text("Niri Monitor Configuration", size=24, weight=ft.FontWeight.BOLD)
    status_text = ft.Text("Loading...", size=14, color="gray")

    canvas = ft.Stack(expand=True)

    canvas_container = ft.Container(
        content=canvas,
        expand=True,
        border=ft.Border.all(2, "gray"),
        padding=5,
    )

    resolution_dropdown = ft.Dropdown(
        label="Resolution",
        options=[],
        width=200,
        on_select=lambda e: on_control_change(),
    )
    scale_slider = ft.Slider(
        min=0.5,
        max=3.0,
        value=1.0,
        divisions=20,
        width=200,
        label="Scale",
        on_change=lambda _: on_slider_change(),
    )
    scale_input = ft.TextField(
        label="Scale",
        width=80,
        on_submit=lambda _: on_scale_input_submit(),
    )
    vrr_switch = ft.Switch(label="VRR", on_change=lambda _: on_control_change())

    def make_primary_click(_) -> None:
        nonlocal selected_monitor_name
        nonlocal primary_monitor_name

        if not selected_monitor_name:
            return

        primary_monitor_name = selected_monitor_name
        update_pending_indicator()
        update_canvas_display()
        page.update()

    primary_button = ft.Button("Make primary", on_click=make_primary_click)

    # Position controls
    pos_x_input = ft.TextField(label="X", width=80)
    pos_y_input = ft.TextField(label="Y", width=80)

    apply_btn = ft.Button("Apply Changes")
    reset_btn = ft.Button("Reset")

    pending_indicator = ft.Text("", size=12, color="orange", weight=ft.FontWeight.BOLD)

    settings_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("Monitor Settings", size=18, weight=ft.FontWeight.BOLD),
                pending_indicator,
                ft.Divider(),
                resolution_dropdown,
                ft.Text("Scale", size=12, weight=ft.FontWeight.BOLD),
                scale_slider,
                ft.Row([scale_input], alignment=ft.MainAxisAlignment.START),
                vrr_switch,
                primary_button,
                ft.Divider(),
                ft.Text("Position", size=12, weight=ft.FontWeight.BOLD),
                ft.Row([pos_x_input, pos_y_input]),
                ft.Divider(),
                ft.Row([apply_btn, reset_btn], spacing=10),
            ],
            spacing=10,
        ),
        width=280,
        padding=10,
        visible=False,
    )

    page.add(
        ft.Column(
            [
                header,
                status_text,
                ft.Divider(),
                ft.Row([canvas_container, settings_panel], expand=True, spacing=10),
            ],
            expand=True,
            spacing=10,
        )
    )

    def on_slider_change() -> None:
        scale_input.value = str(round(scale_slider.value or 1.0, 2))
        on_control_change()

    def on_scale_input_submit() -> None:
        try:
            val = float(scale_input.value)
            val = max(0.5, min(3.0, val))
            scale_slider.value = val
            on_control_change()
            page.update()
        except ValueError:
            pass

    def on_control_change() -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            return
        try:
            x = int(pos_x_input.value or 0)
            y = int(pos_y_input.value or 0)
        except ValueError:
            x = 0
            y = 0

        if selected_monitor_name not in pending_changes:
            pending_changes[selected_monitor_name] = {}

        pending_changes[selected_monitor_name]["resolution"] = resolution_dropdown.value
        pending_changes[selected_monitor_name]["scale"] = scale_slider.value
        pending_changes[selected_monitor_name]["vrr"] = vrr_switch.value
        pending_changes[selected_monitor_name]["x"] = x
        pending_changes[selected_monitor_name]["y"] = y
        update_pending_indicator()
        update_canvas_display()
        page.update()

    def update_pending_indicator() -> None:
        nonlocal selected_monitor_name
        if selected_monitor_name and selected_monitor_name in pending_changes:
            pending_indicator.value = "Pending changes - click Apply"
            pending_indicator.color = "orange"
        else:
            pending_indicator.value = ""

    def get_scale_factor(outputs: dict[str, dict[str, Any]]) -> float:
        max_x = max(
            (
                o.get("logical", {}).get("x", 0)
                + o.get("logical", {}).get("width", 1920)
                for o in outputs.values()
            ),
            default=1920,
        )
        max_y = max(
            (
                o.get("logical", {}).get("y", 0)
                + o.get("logical", {}).get("height", 1080)
                for o in outputs.values()
            ),
            default=1080,
        )
        canvas_w = 790
        canvas_h = 490
        return min(canvas_w / max(max_x, 1), canvas_h / max(max_y, 1)) * 0.95

    def update_canvas_display() -> None:
        """Update canvas without re-fetching from niri - just refreshes the display based on current data"""
        try:
            result = subprocess.run(
                ["niri", "msg", "--json", "outputs"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return
            outputs = json.loads(result.stdout)

            scale_factor = get_scale_factor(outputs)
            canvas.controls.clear()

            for name, output in outputs.items():
                monitors_data[name] = output

                logical = output.get("logical", {})
                width = logical.get("width", 1920)
                height = logical.get("height", 1080)
                x = logical.get("x", 0)
                y = logical.get("y", 0)
                scale = logical.get("scale", 1.0)

                is_pending = name in pending_changes
                is_selected = name == selected_monitor_name

                if is_pending and name in pending_changes:
                    pending = pending_changes[name]
                    if "x" in pending:
                        x = pending["x"]
                    if "y" in pending:
                        y = pending["y"]

                canvas_x = x * scale_factor
                canvas_y = y * scale_factor
                canvas_w = width * scale_factor
                canvas_h = height * scale_factor

                canvas_w = max(canvas_w, 80)
                canvas_h = max(canvas_h, 50)

                canvas_x = min(canvas_x, 790 - canvas_w)
                canvas_y = min(canvas_y, 490 - canvas_h)

                if is_selected:
                    bg_color = "blue"
                    border_color = "darkblue"
                    text_color = "white"
                elif is_pending:
                    bg_color = "orange"
                    border_color = "darkorange"
                    text_color = "black"
                else:
                    bg_color = "lightblue"
                    border_color = "blue"
                    text_color = "black"

                monitor_content = ft.Container(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"{'* ' if name == primary_monitor_name else ''}{name}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=text_color,
                                ),
                                ft.Text(
                                    f"{int(width * scale)}x{int(height * scale)}",
                                    size=9,
                                    color=text_color,
                                ),
                                ft.Text(f"({x}, {y})", size=9, color=text_color),
                                ft.Text(f"s={scale}", size=9, color=text_color),
                            ],
                            spacing=1,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        width=canvas_w,
                        height=canvas_h,
                        bgcolor=bg_color,
                        border=ft.Border.all(2, border_color),
                        border_radius=4,
                        padding=4,
                    ),
                    width=canvas_w,
                    height=canvas_h,
                    left=canvas_x,
                    top=canvas_y,
                    on_click=lambda e, n=name: select_monitor_by_name(n),
                )
                canvas.controls.append(monitor_content)

            page.update()

        except Exception as e:
            status_text.value = f"Error: {e}"
            page.update()

    def select_monitor_by_name(name: str) -> None:
        output = monitors_data.get(name)
        if output:
            select_monitor(output)

    def select_monitor(monitor: dict[str, Any]) -> None:
        nonlocal selected_monitor_name
        nonlocal primary_monitor_name

        selected_monitor_name = cast(str | None, monitor.get("name"))

        logical = monitor.get("logical", {})
        width = logical.get("width", 1920)
        height = logical.get("height", 1080)
        scale = logical.get("scale", 1.0)
        vrr = monitor.get("vrr_enabled", False)

        # Get available modes and populate dropdown
        modes = monitor.get("modes", [])
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
        resolution_dropdown.options = mode_options

        # Physical resolution = logical * scale
        physical_width = int(width * scale)
        physical_height = int(height * scale)

        if selected_monitor_name in pending_changes:
            changes = pending_changes[selected_monitor_name]
            resolution_dropdown.value = changes.get(
                "resolution", f"{physical_width}x{physical_height}"
            )
            scale_slider.value = changes.get("scale", scale)
            vrr_switch.value = changes.get("vrr", vrr)
            pos_x_input.value = str(changes.get("x", logical.get("x", 0)))
            pos_y_input.value = str(changes.get("y", logical.get("y", 0)))
        else:
            resolution_dropdown.value = f"{physical_width}x{physical_height}"
            scale_slider.value = scale
            vrr_switch.value = vrr
            pos_x_input.value = str(logical.get("x", 0))
            pos_y_input.value = str(logical.get("y", 0))

        primary_button.disabled = selected_monitor_name == primary_monitor_name
        scale_input.value = str(round(scale_slider.value or 1.0, 2))

        settings_panel.visible = True
        update_pending_indicator()
        update_canvas_display()
        page.update()

    def refresh_monitors(e=None) -> None:
        nonlocal primary_monitor_name
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
                page.update()
                return

            outputs = json.loads(result.stdout)

            primary_monitor_name = get_primary_monitor()

            for name, output in outputs.items():
                monitors_data[name] = output

            if not outputs:
                status_text.value = "No monitors connected"
            else:
                status_text.value = f"Found {len(outputs)} monitor(s)"
                status_text.color = "green"

            update_canvas_display()
            if selected_monitor_name:
                select_monitor_by_name(selected_monitor_name)

            page.update()

        except Exception as e:
            status_text.value = f"Error: {e}"
            status_text.color = "red"
            page.update()

    def get_primary_monitor() -> str | None:
        try:
            config_path = os.path.expanduser("~/.config/monitors.kdl")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    doc = kdl.parse(f.read())
                    for node in doc.nodes:
                        if node.name == "output" and node.args:
                            name = str(node.args[0])
                            for child in node.nodes:
                                if child.name == "focus-at-startup":
                                    return name
        except Exception as e:
            print(e)

        return None

    def write_kdl_config() -> None:
        """Write monitor configuration to ~/.config/monitors.kdl"""
        nonlocal primary_monitor_name
        try:
            config_path = os.path.expanduser("~/.config/monitors.kdl")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            kdl_config = kdl.Document()

            for name in monitors_data.keys():
                output = monitors_data[name]
                logical = output.get("logical", {})
                vrr_node = kdl.Node(name="variable-refresh-rate")
                if not output.get("vrr_enabled", False):
                    vrr_node.props["on-demand"] = True

                nodes = [
                    kdl.Node(name="scale", args=[logical.get("scale", 1.0)]),
                    kdl.Node(
                        name="position",
                        args=[],
                        props={"x": logical.get("x", 0), "y": logical.get("y", 0)},
                    ),
                    vrr_node,
                ]
                if name == primary_monitor_name:
                    nodes.append(kdl.Node(name="focus-at-startup"))

                output_node = kdl.Node(
                    name="output",
                    args=[name],
                    nodes=nodes,
                )
                kdl_config.nodes.append(output_node)

            # Write to file
            with open(config_path, "w") as f:
                f.write(kdl_config.print())

        except Exception as e:
            status_text.value = f"Error writing KDL config: {e}"
            status_text.color = "red"
            page.update()

    def apply_settings_click(e) -> None:
        errors = []
        applied = []

        for monitor_name, changes in pending_changes.items():
            if "x" in changes or "y" in changes:
                x = changes.get("x", 0)
                y = changes.get("y", 0)
                try:
                    result = subprocess.run(
                        [
                            "niri",
                            "msg",
                            "output",
                            monitor_name,
                            "position",
                            "set",
                            str(x),
                            str(y),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor_name} Position: {result.stderr}")
                except Exception as ex:
                    errors.append(f"{monitor_name} Position: {ex}")

            if "scale" in changes:
                try:
                    result = subprocess.run(
                        [
                            "niri",
                            "msg",
                            "output",
                            monitor_name,
                            "scale",
                            str(changes["scale"]),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor_name} Scale: {result.stderr}")
                except Exception as ex:
                    errors.append(f"{monitor_name} Scale: {ex}")

            if "vrr" in changes:
                vrr_val = "on" if changes["vrr"] else "off"
                try:
                    result = subprocess.run(
                        ["niri", "msg", "output", monitor_name, "vrr", vrr_val],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor_name} VRR: {result.stderr}")
                except Exception as ex:
                    errors.append(f"{monitor_name} VRR: {ex}")

            if "resolution" in changes:
                mode = changes["resolution"]
                try:
                    result = subprocess.run(
                        ["niri", "msg", "output", monitor_name, "mode", mode],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor_name} Mode: {result.stderr}")
                except Exception as ex:
                    errors.append(f"{monitor_name} Mode: {ex}")

            applied.append(monitor_name)

        for monitor_name in applied:
            if monitor_name in pending_changes:
                del pending_changes[monitor_name]

        update_pending_indicator()

        if errors:
            status_text.value = f"Errors: {'; '.join(errors)}"
            status_text.color = "red"
        else:
            status_text.value = f"Applied settings to {len(applied)} monitor(s)"
            status_text.color = "green"

        page.update()
        write_kdl_config()
        refresh_monitors()

    def reset_settings_click(e) -> None:
        pending_changes.clear()
        update_pending_indicator()
        if selected_monitor_name:
            output = monitors_data.get(selected_monitor_name)
            if output:
                logical = output.get("logical", {})
                width = logical.get("width", 1920)
                height = logical.get("height", 1080)
                scale = logical.get("scale", 1.0)
                vrr = output.get("vrr_enabled", False)
                x = logical.get("x", 0)
                y = logical.get("y", 0)

                resolution_dropdown.value = f"{width}x{height}"
                scale_slider.value = scale
                vrr_switch.value = vrr
                scale_input.value = str(round(scale, 2))
                pos_x_input.value = str(x)
                pos_y_input.value = str(y)
        update_canvas_display()
        primary_button.disabled = primary_monitor_name == selected_monitor_name
        status_text.value = "All changes reset"
        status_text.color = "gray"
        page.update()

    def start_event_listener() -> None:
        def listener() -> None:
            try:
                proc = subprocess.Popen(
                    ["niri", "msg", "--json", "event-stream"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if proc.stdout is None:
                    return
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    try:
                        event = json.loads(line)
                        event_type = event.get("type", "")
                        if event_type in (
                            "OutputCreated",
                            "OutputDestroyed",
                            "OutputChanged",
                        ):

                            def do_refresh() -> None:
                                refresh_monitors()

                            page.run_thread(do_refresh)
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()

    def move_monitor_from_input(e) -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            print("Error: No monitor selected")
            return

        try:
            x = int(pos_x_input.value or 0)
            y = int(pos_y_input.value or 0)
        except ValueError:
            status_text.value = "Invalid position values"
            status_text.color = "red"
            page.update()
            return

        if selected_monitor_name not in pending_changes:
            pending_changes[selected_monitor_name] = {}

        pending_changes[selected_monitor_name]["x"] = x
        pending_changes[selected_monitor_name]["y"] = y
        update_pending_indicator()
        page.update()
        update_canvas_display()

    apply_btn.on_click = apply_settings_click
    reset_btn.on_click = reset_settings_click
    pos_x_input.on_change = move_monitor_from_input
    pos_y_input.on_change = move_monitor_from_input

    refresh_monitors()

    start_event_listener()


if __name__ == "__main__":
    ft.run(main)
