import traceback
import subprocess

import flet as ft

from typing import Callable

from monitor import Monitor


@ft.control
class SettingsPanel(ft.Container):
    def __init__(
        self,
        on_resolution_change=Callable[[tuple[int, int]], None],
        on_scale_change=Callable[[float], None],
        on_vrr_change=Callable[[bool], None],
        on_make_primary_click=Callable[[Monitor], None],
        on_x_change=Callable[[int], None],
        on_y_change=Callable[[int], None],
        on_apply=Callable[[Monitor, list[str]], None],
        on_reset=Callable[[Monitor], None],
    ):
        self._monitor: Monitor | None = None
        self.on_resolution_change: Callable[[tuple[int, int]], None] = (
            on_resolution_change
        )
        self.on_scale_change: Callable[[float], None] = on_scale_change
        self.on_vrr_change: Callable[[float], None] = on_vrr_change
        self.on_make_primary_click: Callable[[Monitor], None] = on_make_primary_click
        self.on_x_change: Callable[[int], None] = on_x_change
        self.on_y_change: Callable[[int], None] = on_y_change
        self.on_apply: Callable[[Monitor, list[str]], None] = on_apply
        self.on_reset: Callable[[Monitor], None] = on_reset
        self.resolution_dropdown = ft.Dropdown(
            label="Resolution",
            options=[],
            width=200,
            on_select=lambda _: self._on_resolution_change(),
        )
        self.scale_slider = ft.Slider(
            min=0.5,
            max=3.0,
            value=1.0,
            divisions=20,
            width=200,
            label="Scale",
            on_change=lambda _: self._on_slider_change(),
        )
        self.scale_input = ft.TextField(
            label="Scale",
            width=80,
            on_change=lambda _: on_scale_change(),
        )
        self.vrr_switch = ft.Switch(
            label="VRR", on_change=lambda _: self._on_vrr_change()
        )
        self.primary_button = ft.Button(
            "Make primary", on_click=lambda _: self._on_make_primary_click()
        )
        self.pos_x_input = ft.TextField(
            label="X",
            width=80,
            on_change=lambda _: self._on_x_change(),
        )
        self.pos_y_input = ft.TextField(
            label="Y",
            width=80,
            on_change=lambda e: self._on_y_change(),
        )
        super().__init__(
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
                                on_click=lambda _: self.close(),
                            ),
                        ]
                    ),
                    ft.Divider(),
                    self.resolution_dropdown,
                    ft.Text("Scale", size=12, weight=ft.FontWeight.BOLD),
                    self.scale_slider,
                    ft.Row([self.scale_input], alignment=ft.MainAxisAlignment.START),
                    self.vrr_switch,
                    self.primary_button,
                    ft.Divider(),
                    ft.Text("Position", size=12, weight=ft.FontWeight.BOLD),
                    ft.Row([self.pos_x_input, self.pos_y_input]),
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.Button("Save", on_click=lambda _: self.apply()),
                            ft.Button("Reset", on_click=lambda _: self.reset()),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
            width=280,
            padding=10,
            visible=False,
        )

    def close(self) -> None:
        self.visible = False
        self.monitor = None
        self.on_close()

    def apply(self):
        if self.monitor is None:
            return

        errors: list[str] = []
        if "position" in self.monitor.pending:
            try:
                x, y = self.monitor.position
                result = subprocess.run(
                    [
                        "niri",
                        "msg",
                        "output",
                        self.monitor.name,
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
                    errors.append(f"{self.monitor.name} Position: {result.stderr}")

            except Exception as ex:
                print(traceback.print_exc())
                errors.append(f"{self.monitor.name} Position: {ex}")

        if "scale" in self.monitor.pending:
            try:
                result = subprocess.run(
                    [
                        "niri",
                        "msg",
                        "output",
                        self.monitor.name,
                        "scale",
                        str(self.monitor.monitor_scale),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"{self.monitor.name} Scale: {result.stderr}")

            except Exception as ex:
                print(traceback.print_exc())
                errors.append(f"{self.monitor.name} Scale: {ex}")

        if "vrr" in self.monitor.pending:
            vrr_val = "on" if self.monitor.vrr else "off"
            try:
                result = subprocess.run(
                    ["niri", "msg", "output", self.monitor.name, "vrr", vrr_val],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"{self.monitor.name} VRR: {result.stderr}")

            except Exception as ex:
                print(traceback.print_exc())
                errors.append(f"{self.monitor.name} VRR: {ex}")

        if "resolution" in self.monitor.pending:
            try:
                w, h = self.monitor.resolution
                result = subprocess.run(
                    ["niri", "msg", "output", self.monitor.name, "mode", f"{w}x{h}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"{self.monitor.name} Mode: {result.stderr}")

            except Exception as ex:
                print(traceback.print_exc())
                errors.append(f"{self.monitor.name} Mode: {ex}")

        self.monitor.pending.clear()
        self.on_apply(self.monitor, errors)

    def reset(self) -> None:
        if self.monitor is None:
            return

        self.monitor.pending.clear()
        self.on_reset(self.monitor)
        w, h = self.monitor.resolution
        self.resolution_dropdown.value = f"{w}x{h}"
        self.scale_slider.value = self.monitor.monitor_scale
        self.scale_input.value = str(round(self.monitor.monitor_scale, 1))
        self.vrr_switch.value = self.monitor.vrr
        x, y = self.monitor.position
        self.pos_x_input.value = str(x)
        self.pos_y_input.value = str(y)
        self.primary_button.disabled = self.monitor.primary

    @property
    def monitor(self) -> Monitor | None:
        return self._monitor

    @monitor.setter
    def monitor(self, monitor: Monitor | None) -> None:
        self._monitor = monitor
        self.visible = True

    def _on_resolution_change(self) -> None:
        if self.monitor is None:
            return

        x, y = self.resolution_dropdown.value.split("x")
        self.monitor.resolution = (int(x), int(y))
        self.monitor.pending.add("resolution")
        self.on_resolution_change(self.monitor.resolution)

    def _on_slider_change(self) -> None:
        if self.monitor is None:
            return

        self.scale_input.value = str(
            round(max(0.5, min(3.0, self.scale_slider.value or 1.0)), 1)
        )
        self.monitor.monitor_scale = self.scale_slider.value
        self.monitor.pending.add("scale")
        self.on_scale_change(self.monitor.monitor_scale)

    def _on_scale_change(self) -> None:
        if self.monitor is None:
            return

        try:
            self.scale_slider.value = round(
                max(0.5, min(3.0, float(self.scale_input.value))), 1
            )

        except ValueError:
            print(traceback.print_exc())

        self.scale_input.value = str(self.scale_slider.value)
        self.monitor.monitor_scale = self.scale_slider.value
        self.monitor.pending.add("scale")
        self.on_scale_change(self.monitor.monitor_scale)

    def _on_vrr_change(self) -> None:
        if self.monitor is None:
            return

        self.monitor.vrr = self.vrr_switch.value
        self.monitor.pending.add("vrr")
        self.on_vrr_change(self.monitor.vrr)

    def _on_make_primary_click(self) -> None:
        if self.monitor is None:
            return

        self.monitor.pending.add("primary")
        self.on_make_primary_click(self.monitor)

    def _on_x_change(self) -> None:
        if self.monitor is None:
            return

        try:
            x = int(self.pos_x_input.value or 0)

        except ValueError:
            print(traceback.print_exc())
            return

        _, y = self.monitor.position
        self.monitor.position = (x, y)
        self.monitor.pending.add("position")
        self.on_x_change(x)

    def _on_y_change(self) -> None:
        if self.monitor is None:
            return

        try:
            y = int(self.pos_y_input.value or 0)

        except ValueError:
            print(traceback.print_exc())
            return

        x, _ = self.monitor.position
        self.monitor.position = (x, y)
        self.monitor.pending.add("position")
        self.on_y_change(y)
