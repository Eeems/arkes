import flet as ft

from typing import Callable
from typing import override

@ft.control
class Monitor(ft.Container):
    def __init__(
        self,
        name: str,
        resolution: tuple[int, int],
        position: tuple[int, int],
        scale: float,
        vrr: bool,
        on_click: ft.ControlEventHandler[ft.Container] | None,
        primary_monitor: Callable[[], str | None],
        selected_monitor: Callable[[], str | None],
        canvas_min_x: Callable[[], int],
        canvas_min_y: Callable[[], int],
        canvas_scale_factor: Callable[[], float],
    ):
        self.name: str = name
        self._primary_monitor = primary_monitor
        self._selected_monitor = selected_monitor
        self._canvas_min_x = canvas_min_x
        self._canvas_min_y = canvas_min_y
        self._canvas_scale_factor = canvas_scale_factor
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
            f"{'* ' if self.primary else ''}{name}",
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
            on_click=on_click,
        )
        self._update()

    def _update(self) -> None:
        canvas_min_x = self._canvas_min_x()
        canvas_min_y = self._canvas_min_y()
        canvas_scale_factor = self._canvas_scale_factor()
        w, h = self.resolution
        x, y = self.position
        self.left = (x - canvas_min_x) * canvas_scale_factor
        self.top = (y - canvas_min_y) * canvas_scale_factor
        self.width = int(w / self.monitor_scale) * canvas_scale_factor
        self.height = int(h / self.monitor_scale) * canvas_scale_factor

    @override
    def update(self) -> None:
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
        return self.name == self._primary_monitor()

    @property
    def selected(self) -> bool:
        return self.name == self._selected_monitor()

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
