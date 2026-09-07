"""
PaletteLab Web settings and persistence manager.
Uses a simple dictionary state hydrated from session cookies per-request.
"""
from typing import Optional

class AppSettings:
    def __init__(self):
        self._state = {
            "theme_mode": "dark",
            "theme_name": "Midnight Plum",
            "wallpaper_path": "",
            "use_wallpaper": False,
            "auto_background": True,
            "default_layout": "Chips",
            "default_sort": "Original"
        }

    @property
    def theme_mode(self) -> str:
        return self._state.get("theme_mode", "dark")

    @theme_mode.setter
    def theme_mode(self, value: str):
        self._state["theme_mode"] = value.lower()

    @property
    def theme_name(self) -> str:
        val = self._state.get("theme_name", "Midnight Plum")
        valid_themes = (
            "Midnight Plum", "Sapphire Tide", "Wine & Charcoal",
            "Obsidian Mint", "Cyberpunk Violet",
            "Snow Pearl", "Vanilla Sky", "Mint Breeze", "Peach Blossom", "Lavender Mist"
        )
        if val not in valid_themes:
            return "Midnight Plum" if self.theme_mode == "dark" else "Snow Pearl"
        return val

    @theme_name.setter
    def theme_name(self, value: str):
        self._state["theme_name"] = value

    @property
    def wallpaper_path(self) -> Optional[str]:
        return self._state.get("wallpaper_path") or None

    @wallpaper_path.setter
    def wallpaper_path(self, value: Optional[str]):
        self._state["wallpaper_path"] = value or ""

    @property
    def use_wallpaper(self) -> bool:
        return bool(self._state.get("use_wallpaper", False))

    @use_wallpaper.setter
    def use_wallpaper(self, value: bool):
        self._state["use_wallpaper"] = bool(value)

    @property
    def auto_background(self) -> bool:
        return bool(self._state.get("auto_background", True))

    @auto_background.setter
    def auto_background(self, value: bool):
        self._state["auto_background"] = bool(value)

    @property
    def default_layout(self) -> str:
        return self._state.get("default_layout", "Chips")

    @default_layout.setter
    def default_layout(self, value: str):
        self._state["default_layout"] = value

    @property
    def default_sort(self) -> str:
        return self._state.get("default_sort", "Original")

    @default_sort.setter
    def default_sort(self, value: str):
        self._state["default_sort"] = value

# Global settings singleton fallback
settings = AppSettings()
