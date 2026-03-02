import flet as ft


def main(page: ft.Page) -> None:
    page.title = "Niri Config"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    output = ft.TextField(
        multiline=True,
        read_only=True,
        min_lines=20,
        width=800,
    )

    def generate_config(e: ft.ControlEvent) -> None:
        config = """# Niri Configuration
# See https://github.com/YaLTeR/niri/wiki/Configuration

{
    # Output configuration
    "outputs": [
        {
            "name": "DP-1",
            "mode": { "width": 2560, "height": 1440, "refresh-rate": 144 },
            "position": { "x": 0, "y": 0 },
            "scale": 1.0
        }
    ],

    # Keybindings
    "keys": {
        "Alt-Tab": "cycle-next-window",
        "Alt-Shift-Tab": "cycle-prev-window",
        "Super-Return": "spawn-wezterm",
        "Super-Q": "close-window",
        "Super-M": "toggle-maximize"
    },

    # Mouse bindings
    "mouse": {
        "drag": { "left": "move-window" },
        "resize": { "right": "resize-window" }
    }
}
"""
        output.value = config

    page.add(
        ft.Text("Niri Configuration Generator", size=24, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.ElevatedButton("Generate Config", on_click=generate_config),
        ]),
        output,
    )


if __name__ == "__main__":
    ft.app(target=main)
