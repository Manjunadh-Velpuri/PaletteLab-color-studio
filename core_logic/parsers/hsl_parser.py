"""
PaletteLab HSL Format Parser.
Extracts HSL color definitions from text and converts them to standard HEX.
"""

import re
from typing import List
from core_logic.core.color_utils import hex_from_hsl

# Matches: hsl(240, 100%, 50%), hsla(240, 100%, 50%, 0.8), hsl: 240, 100%, 50%, hsl(240 100% 50%)
HSL_RE = re.compile(
    r"\bhsla?\s*(?:\(\s*|\s*:\s*)(-?[0-9]*\.?[0-9]+(?:deg)?)\s*[, ]\s*([0-9]*\.?[0-9]+%?)\s*[, ]\s*([0-9]*\.?[0-9]+%?)(?:\s*[,/]\s*[0-9.]+%?)?\s*\)?",
    re.IGNORECASE
)


def extract_hsl(text: str) -> List[str]:
    """
    Extract valid HSL colors from arbitrary text and convert to #RRGGBB.
    """
    results: List[str] = []

    for match in HSL_RE.finditer(text):
        h_str, s_str, l_str = match.group(1), match.group(2), match.group(3)

        try:
            h_str = h_str.lower().rstrip("deg")
            h = float(h_str)

            s_str = s_str.rstrip("%")
            s = float(s_str)

            l_str = l_str.rstrip("%")
            l = float(l_str)

            h = h % 360.0
            if 0.0 <= s <= 100.0 and 0.0 <= l <= 100.0:
                hex_val = hex_from_hsl(h, s, l)
                if hex_val not in results:
                    results.append(hex_val)
        except (ValueError, TypeError):
            continue

    return results
