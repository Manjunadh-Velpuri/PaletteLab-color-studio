"""
PaletteLab HSV / HSB Format Parser.
Extracts HSV/HSB color definitions from text and converts them to standard HEX.
"""

import re
from typing import List
from core_logic.core.color_utils import hex_from_hsv

# Matches: hsv(180, 50%, 80%), hsva(180, 50%, 80%, 1.0), hsb(180, 50%, 80%), hsv: 180, 50%, 80%
HSV_RE = re.compile(
    r"\b(?:hsv|hsb)a?\s*(?:\(\s*|\s*:\s*)(-?[0-9]*\.?[0-9]+(?:deg)?)\s*[, ]\s*([0-9]*\.?[0-9]+%?)\s*[, ]\s*([0-9]*\.?[0-9]+%?)(?:\s*[,/]\s*[0-9.]+%?)?\s*\)?",
    re.IGNORECASE
)


def extract_hsv(text: str) -> List[str]:
    """
    Extract valid HSV/HSB colors from arbitrary text and convert to #RRGGBB.
    """
    results: List[str] = []

    for match in HSV_RE.finditer(text):
        h_str, s_str, v_str = match.group(1), match.group(2), match.group(3)

        try:
            h_str = h_str.lower().rstrip("deg")
            h = float(h_str)

            s_str = s_str.rstrip("%")
            s = float(s_str)

            v_str = v_str.rstrip("%")
            v = float(v_str)

            h = h % 360.0
            if 0.0 <= s <= 100.0 and 0.0 <= v <= 100.0:
                hex_val = hex_from_hsv(h, s, v)
                if hex_val not in results:
                    results.append(hex_val)
        except (ValueError, TypeError):
            continue

    return results
