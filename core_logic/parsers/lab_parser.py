"""
PaletteLab CIE L*a*b* Format Parser.
Extracts CIELAB color definitions from text and converts them to standard HEX.
"""

import re
from typing import List
from core_logic.core.color_utils import hex_from_lab

# Matches: lab(53.23, 80.11, 67.22), cielab(50, -30, 40), lab: 50, -20, 30, lab(50% 20 -30)
LAB_RE = re.compile(
    r"\b(?:cie-?)?lab\s*(?:\(\s*|\s*:\s*)([0-9]+(?:\.[0-9]+)?%?)\s*[, ]\s*(-?[0-9]+(?:\.[0-9]+)?%?)\s*[, ]\s*(-?[0-9]+(?:\.[0-9]+)?%?)(?:\s*[,/]\s*[0-9.]+%?)?\s*\)?",
    re.IGNORECASE
)


def extract_lab(text: str) -> List[str]:
    """
    Extract valid CIE L*a*b* colors from arbitrary text and convert to #RRGGBB.
    """
    results: List[str] = []

    for match in LAB_RE.finditer(text):
        l_str, a_str, b_str = match.group(1), match.group(2), match.group(3)

        try:
            l = float(l_str.rstrip("%"))
            a = float(a_str.rstrip("%"))
            b = float(b_str.rstrip("%"))

            if 0.0 <= l <= 100.0 and -160.0 <= a <= 160.0 and -160.0 <= b <= 160.0:
                hex_val = hex_from_lab(l, a, b)
                if hex_val not in results:
                    results.append(hex_val)
        except (ValueError, TypeError):
            continue

    return results
