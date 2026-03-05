import traceback
import subprocess
import json
import os

import flet as ft
import kdl

from typing import cast, override
from typing import Any

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

    @ft.control
    class Monitor(ft.Container):
        def __init__(
            self,
            name: str,
            resolution: tuple[int, int],
            position: tuple[int, int],
            scale: float,
            vrr: bool,
        ):
            nonlocal primary_monitor_name
            nonlocal canvas_min_x
            nonlocal canvas_scale_factor
            nonlocal canvas_min_y
            self.name: str = name
            self._resolution: tuple[int, int] = resolution
            self._position: tuple[int, int] = position
            self._scale: float = scale
            self.vrr: bool = vrr
            self.pending: set[str] = set()
            w, h = resolution
            x, y = position

            self.scale_text = ft.Text(f"s={scale}", size=9, color=self.text_color)
            self.resolution_text = ft.Text(f"{w}x{h}", size=9, color=self.text_color)
            self.position_text = ft.Text(f"({x}, {y})", size=9, color=self.text_color)
            self.name_text = ft.Text(
                f"{'* ' if name == primary_monitor_name else ''}{name}",
                size=11,
                weight=ft.FontWeight.BOLD,
                color=self.text_color,
            )

            super().__init__(
                content=ft.Column(
                    [
                        self.name_text,
                        self.resolution_text,
                        self.position_text,
                        self.scale_text,
                    ],
                    spacing=1,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor=self.bg_color,
                border=ft.Border.all(2, self.border_color),
                border_radius=4,
                padding=4,
                on_click=lambda e, n=name: select_monitor_by_name(n),
            )
            self._update()

        def _update(self) -> None:
            nonlocal canvas_min_x
            nonlocal canvas_min_y
            nonlocal canvas_scale_factor
            w, h = self.resolution
            x, y = self.position
            self.left = (x - canvas_min_x) * canvas_scale_factor
            self.top = (y - canvas_min_y) * canvas_scale_factor
            self.width = int(w / self.monitor_scale) * canvas_scale_factor
            self.height = int(h / self.monitor_scale) * canvas_scale_factor

        @override
        def update(self) -> None:
            nonlocal primary_monitor_name
            self.bgcolor = self.bg_color
            self.border = ft.Border.all(2, self.border_color)
            self.scale_text.color = self.resolution_text.color = (
                self.position_text.color
            ) = self.name_text.color = self.text_color
            self.name_text.value = f"{'* ' if self.primary else ''}{self.name}"
            self._update()
            super().update()

        @property
        def primary(self) -> bool:
            nonlocal primary_monitor_name
            return self.name == primary_monitor_name

        @property
        def selected(self) -> bool:
            nonlocal selected_monitor_name
            return self.name == selected_monitor_name

        @property
        def resolution(self) -> tuple[int, int]:
            return self._resolution

        @resolution.setter
        def resolution(self, resolution: tuple[int, int]) -> None:
            self._resolution = resolution
            w, h = resolution
            self.resolution_text.value = f"{w}x{h}"
            self._update()

        @property
        def position(self) -> tuple[int, int]:
            return self._position

        @position.setter
        def position(self, position: tuple[int, int]) -> None:
            self._position = position
            x, y = position
            self.position_text.value = f"({x},{y})"
            self._update()

        @property
        def monitor_scale(self) -> float:
            return self._scale

        @monitor_scale.setter
        def monitor_scale(self, scale: float | None) -> None:
            self._scale = max(0.5, min(3.0, scale or 1.0))
            self.scale_text.value = f"s={self.monitor_scale}"
            self._update()

        @property
        def text_color(self) -> str:
            return "white" if self.selected else "black"

        @property
        def bg_color(self) -> str:
            return (
                "blue" if self.selected else "orange" if self.pending else "lightblue"
            )

        @property
        def border_color(self) -> str:
            return (
                "darkblue"
                if self.selected
                else "darkorange"
                if self.pending
                else "blue"
            )

    status_text = ft.Text("Loading...", size=14, color="gray")
    canvas = ft.Stack(expand=True, on_size_change=lambda e: on_canvas_resize(e))
    resolution_dropdown = ft.Dropdown(
        label="Resolution",
        options=[],
        width=200,
        on_select=lambda e: on_resolution_change(),
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
        on_change=lambda _: on_scale_change(),
    )
    vrr_switch = ft.Switch(label="VRR", on_change=lambda _: on_vrr_change())
    primary_button = ft.Button("Make primary", on_click=lambda _: make_primary_click())
    pos_x_input = ft.TextField(
        label="X", width=80, on_change=lambda e: move_monitor_from_input(e)
    )
    pos_y_input = ft.TextField(
        label="Y", width=80, on_change=lambda e: move_monitor_from_input(e)
    )
    apply_btn = ft.Button("Apply Changes", on_click=lambda e: apply_settings_click(e))
    reset_btn = ft.Button("Reset", on_click=lambda e: reset_settings_click(e))
    settings_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Monitor Settings",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            expand=True,
                        ),
                        ft.Button(
                            ft.Icon(ft.Icons.CLOSE_ROUNDED),
                            style=ft.ButtonStyle(shape=ft.CircleBorder()),
                            on_click=lambda _: on_settings_close(),
                        ),
                    ]
                ),
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

    def on_settings_close() -> None:
        settings_panel.visible = False

    def make_primary_click() -> None:
        nonlocal selected_monitor_name
        nonlocal primary_monitor_name

        if not selected_monitor_name:
            return

        primary_monitor_name = selected_monitor_name
        update_status()
        update_canvas_display()
        page.schedule_update()

    def on_resolution_change() -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            return

        monitor = get_monitor(selected_monitor_name)
        if monitor is not None:
            x, y = resolution_dropdown.value.split("x")
            monitor.resolution = (int(x), int(y))
            monitor.pending.add("resolution")

        update_status()
        update_canvas_display()

    def on_vrr_change() -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            return

        monitor = get_monitor(selected_monitor_name)
        if monitor is not None:
            monitor.vrr = vrr_switch.value
            monitor.pending.add("vrr")

        update_status()
        update_canvas_display()

    def on_slider_change() -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            return

        scale_input.value = str(round(max(0.5, min(3.0, scale_slider.value or 1.0)), 1))
        monitor = get_monitor(selected_monitor_name)
        if monitor is not None:
            monitor.monitor_scale = scale_slider.value
            monitor.pending.add("scale")

        update_status()
        update_canvas_display()

    def on_scale_change() -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            return

        try:
            scale_slider.value = round(max(0.5, min(3.0, float(scale_input.value))), 1)

        except ValueError:
            print(traceback.print_exc())

        scale_input.value = str(scale_slider.value)
        monitor = get_monitor(selected_monitor_name)
        if monitor is not None:
            monitor.monitor_scale = scale_slider.value
            monitor.pending.add("scale")

        update_status()
        update_canvas_display()

    def update_status() -> None:
        nonlocal selected_monitor_name
        monitor = get_monitor(selected_monitor_name or "")
        if monitor and monitor.pending:
            status_text.value = "Pending changes"
            status_text.color = "orange"

        else:
            status_text.value = ""

    def on_canvas_resize(e: ft.LayoutSizeChangeEvent[ft.LayoutControl]) -> None:
        nonlocal canvas_width
        nonlocal canvas_height
        canvas_width = e.width
        canvas_height = e.height
        print(f"Canvas: {e.width}x{e.height}")
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
                height = int(width / monitor.monitor_scale)

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

    def update_canvas_display() -> None:
        nonlocal outputs
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
                    )
                    canvas.controls.append(monitor)

                else:
                    if "scale" not in monitor.pending:
                        monitor.scale = scale

                    if "resolution" not in monitor.pending:
                        monitor.resolution = (width, height)

                    if "position" not in monitor.pending:
                        monitor.position = (x, y)

            for monitor in canvas.controls:
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
        monitor = get_monitor(selected_monitor_name or "")
        settings_panel.visible = bool(monitor)
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
        resolution_dropdown.options = mode_options
        w, h = monitor.resolution
        resolution_dropdown.value = f"{w}x{h}"
        scale_slider.value = monitor.monitor_scale
        scale_input.value = str(monitor.monitor_scale)
        vrr_switch.value = monitor.vrr
        x, y = monitor.position
        pos_x_input.value = str(x)
        pos_y_input.value = str(y)
        primary_button.disabled = monitor.primary
        monitor.update()
        update_status()
        update_canvas_display()
        page.schedule_update()

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

    def apply_settings_click(e) -> None:
        errors: list[str] = []
        count = 0

        for monitor in sorted(
            cast(list[Monitor], canvas.controls), key=lambda x: x.name
        ):
            if not monitor.pending:
                continue

            count += 1

            if "position" in monitor.pending:
                try:
                    x, y = monitor.position
                    result = subprocess.run(
                        [
                            "niri",
                            "msg",
                            "output",
                            monitor.name,
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
                        errors.append(f"{monitor.name} Position: {result.stderr}")

                except Exception as ex:
                    print(traceback.print_exc())
                    errors.append(f"{monitor.name} Position: {ex}")

            if "scale" in monitor.pending:
                try:
                    result = subprocess.run(
                        [
                            "niri",
                            "msg",
                            "output",
                            monitor.name,
                            "scale",
                            str(monitor.monitor_scale),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor.name} Scale: {result.stderr}")

                except Exception as ex:
                    print(traceback.print_exc())
                    errors.append(f"{monitor.name} Scale: {ex}")

            if "vrr" in monitor.pending:
                vrr_val = "on" if monitor.vrr else "off"
                try:
                    result = subprocess.run(
                        ["niri", "msg", "output", monitor.name, "vrr", vrr_val],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor.name} VRR: {result.stderr}")

                except Exception as ex:
                    print(traceback.print_exc())
                    errors.append(f"{monitor.name} VRR: {ex}")

            if "resolution" in monitor.pending:
                try:
                    w, h = monitor.resolution
                    result = subprocess.run(
                        ["niri", "msg", "output", monitor.name, "mode", f"{w}x{h}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        errors.append(f"{monitor.name} Mode: {result.stderr}")

                except Exception as ex:
                    print(traceback.print_exc())
                    errors.append(f"{monitor.name} Mode: {ex}")

            monitor.pending.clear()

        update_status()
        if errors:
            status_text.value = f"Errors: {'; '.join(errors)}"
            status_text.color = "red"

        else:
            status_text.value = f"Applied settings to {count} monitor(s)"
            status_text.color = "green"

        write_kdl_config()
        refresh_monitors()

    def reset_settings_click(e) -> None:
        nonlocal primary_monitor_name
        nonlocal selected_monitor_name
        update_status()
        primary_monitor_name = get_primary_monitor()
        if selected_monitor_name:
            output = outputs.get(selected_monitor_name)
            monitor = get_monitor(selected_monitor_name)
            if monitor:
                monitor.pending.clear()

            if output:
                logical = output.get("logical", {})
                width = cast(int, logical.get("width", 1920))
                height = cast(int, logical.get("height", 1080))
                scale = cast(float, logical.get("scale", 1.0))
                vrr = cast(bool, output.get("vrr_enabled", False))
                x = cast(int, logical.get("x", 0))
                y = cast(int, logical.get("y", 0))

                resolution_dropdown.value = f"{width}x{height}"
                scale_slider.value = scale
                scale_input.value = str(round(scale, 1))
                vrr_switch.value = vrr
                pos_x_input.value = str(x)
                pos_y_input.value = str(y)

                if monitor:
                    monitor.resolution = (width, height)
                    monitor.monitor_scale = scale
                    monitor.position = (x, y)
                    monitor.vrr = vrr
                    print(monitor.primary)

        primary_button.disabled = primary_monitor_name == selected_monitor_name
        status_text.value = "All changes reset"
        status_text.color = "gray"
        update_canvas_display()

    def move_monitor_from_input(e) -> None:
        nonlocal selected_monitor_name
        if not selected_monitor_name:
            print("Error: No monitor selected")
            return

        try:
            x = int(pos_x_input.value or 0)
            y = int(pos_y_input.value or 0)

        except ValueError:
            print(traceback.print_exc())
            status_text.value = "Invalid position values"
            status_text.color = "red"
            page.schedule_update()
            return

        monitor = get_monitor(selected_monitor_name)
        if monitor is not None:
            monitor.position = (x, y)
            monitor.pending.add("position")

        update_status()
        update_canvas_display()

    refresh_monitors()


if __name__ == "__main__":
    ft.run(main)
