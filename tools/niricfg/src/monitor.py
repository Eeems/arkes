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
        is_primary: Callable[["Monitor"], bool],
        is_selected: Callable[["Monitor"], bool],
        on_layout: Callable[["Monitor"], None],
    ):
        self.name: str = name
        self.is_primary: Callable[["Monitor"], bool] = is_primary
        self.is_selected: Callable[["Monitor"], bool] = is_selected
        self.on_layout: Callable[["Monitor"], None] = on_layout
        self._resolution: tuple[int, int] = resolution
        self._orig_resolution: tuple[int, int] = self._resolution
        self._position: tuple[int, int] = position
        self._orig_position: tuple[int, int] = self._position
        self._scale: float = self._clamp_scale(scale)
        self._orig_scale: float = self._scale
        self._vrr: bool = vrr
        self._orig_vrr: bool = self.vrr
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
        w, h = self.resolution
        x, y = self.position
        self.left = x
        self.top = y
        self.width = int(w / self.monitor_scale)
        self.height = int(h / self.monitor_scale)
        self.on_layout(self)

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

    def reset(self) -> None:
        for name in self.pending:
            match name:
                case "position":
                    self._position = self._orig_position

                case "scale":
                    self._scale = self._orig_scale

                case "resolution":
                    self._resolution = self._orig_resolution

                case "vrr":
                    self._vrr = self._orig_vrr

        self.pending.clear()
        self.update()

    def apply(self) -> None:
        for name in self.pending:
            match name:
                case "position":
                    self._orig_position = self._position

                case "scale":
                    self._orig_scale = self._scale

                case "resolution":
                    self._orig_resolution = self._resolution

                case "vrr":
                    self._orig_vrr = self._vrr

        self.pending.clear()
        self.update()

    @property
    def vrr(self) -> bool:
        return self._vrr

    @property
    def primary(self) -> bool:
        return self.is_primary(self)

    @property
    def selected(self) -> bool:
        return self.is_selected(self)

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
        self._scale = self._clamp_scale(scale)
        self.scale_text.value = f"s={self.monitor_scale}"
        self._update()

    def _clamp_scale(self, scale: float | None) -> float:
        return round(max(0.5, min(3.0, scale or 1.0)), 1)

    @property
    def text_color(self) -> str:
        return "white" if self.selected else "black"

    @property
    def bg_color(self) -> str:
        return "blue" if self.selected else "orange" if self.pending else "lightblue"

    @property
    def border_color(self) -> str:
        return "darkblue" if self.selected else "darkorange" if self.pending else "blue"
