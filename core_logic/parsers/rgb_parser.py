"""
PaletteLab RGB Format Parser.
Extracts RGB color definitions from text and converts them to standard HEX.
"""

import re
from typing import List
from core_logic.core.color_utils import hex_from_rgb

# Matches: rgb(255, 128, 0), rgba(255, 128, 0, 0.5), rgb(100%, 50%, 0%), rgb: 255, 128, 0
RGB_RE = re.compile(
    r"\brgba?\s*(?:\(\s*|\s*:\s*)([0-9]{1,3}%?)\s*[, ]\s*([0-9]{1,3}%?)\s*[, ]\s*([0-9]{1,3}%?)(?:\s*[,/]\s*[0-9.]+%?)?\s*\)?",
    re.IGNORECASE
)


def extract_rgb(text: str) -> List[str]:
    """
    Extract valid RGB/RGBA colors from arbitrary text and convert to #RRGGBB.
    """
    results: List[str] = []

    for match in RGB_RE.finditer(text):
        r_str, g_str, b_str = match.group(1), match.group(2), match.group(3)

        try:
            if r_str.endswith("%"):
                r = float(r_str[:-1]) * 2.55
            else:
                r = float(r_str)

            if g_str.endswith("%"):
                g = float(g_str[:-1]) * 2.55
            else:
                g = float(g_str)

            if b_str.endswith("%"):
                b = float(b_str[:-1]) * 2.55
            else:
                b = float(b_str)

            if 0.0 <= r <= 255.0 and 0.0 <= g <= 255.0 and 0.0 <= b <= 255.0:
                hex_val = hex_from_rgb((r, g, b))
                if hex_val not in results:
                    results.append(hex_val)
        except (ValueError, TypeError):
            continue

    return results
