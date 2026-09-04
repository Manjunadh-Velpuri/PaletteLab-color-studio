"""
PaletteLab Multi-format Color Parsers.
Exposes parsers for HEX, RGB, HSL, HSV, CMYK, and LAB color formats.
"""

from core_logic.core.color_utils import extract_hexes
from core_logic.parsers.rgb_parser import extract_rgb
from core_logic.parsers.hsl_parser import extract_hsl
from core_logic.parsers.hsv_parser import extract_hsv
from core_logic.parsers.cmyk_parser import extract_cmyk
from core_logic.parsers.lab_parser import extract_lab

PARSERS = {
    "HEX": extract_hexes,
    "RGB": extract_rgb,
    "HSL": extract_hsl,
    "HSV": extract_hsv,
    "CMYK": extract_cmyk,
    "LAB": extract_lab,
}
