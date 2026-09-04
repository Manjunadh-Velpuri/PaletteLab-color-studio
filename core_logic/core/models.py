"""
PaletteLab core data models and constants.
"""

from dataclasses import dataclass

APP_NAME = "PaletteLab"

MIN_EXPORT_SIDE = 2048

PREVIEW_SUPERSAMPLE = 4
EXPORT_SUPERSAMPLE = 2

LAYOUTS = (
    "Pillars",
    "Orbs",
    "Ribbons",
    "Chips",
    "Collage",
    "Honeycomb",
    "Canvas",
    "Blocks",
)

SORTS = (
    "Original",
    "Manual",
    "Hue",
    "Saturation",
    "Lightness",
    "Value",
)

WORKSPACES = (
    "Palette",
    "Convert",
)


@dataclass
class ColorItem:
    id: int
    original: str
    current: str
    selected: bool = True
    shade: float = 0.0
