"""
PaletteLab CMYK Format Parser.
Extracts CMYK color definitions from text and converts them to standard HEX.
"""

import re
from typing import List
from core_logic.core.color_utils import hex_from_cmyk

# Matches: cmyk(0%, 50%, 100%, 0%), cmyk(0, 50, 100, 0), cmyk: 0%, 50%, 100%, 0%
CMYK_RE = re.compile(
    r"\bcmyk\s*(?:\(\s*|\s*:\s*)([0-9]+(?:\.[0-9]+)?%?)\s*[, ]\s*([0-9]+(?:\.[0-9]+)?%?)\s*[, ]\s*([0-9]+(?:\.[0-9]+)?%?)\s*[, ]\s*([0-9]+(?:\.[0-9]+)?%?)\s*\)?",
    re.IGNORECASE
)


def extract_cmyk(text: str) -> List[str]:
    """
    Extract valid CMYK colors from arbitrary text and convert to #RRGGBB.
    """
    results: List[str] = []

    for match in CMYK_RE.finditer(text):
        c_str, m_str, y_str, k_str = match.group(1), match.group(2), match.group(3), match.group(4)

        try:
            c = float(c_str.rstrip("%"))
            m = float(m_str.rstrip("%"))
            y = float(y_str.rstrip("%"))
            k = float(k_str.rstrip("%"))

            # If input was 0.0 - 1.0 decimals without %:
            if c <= 1.0 and m <= 1.0 and y <= 1.0 and k <= 1.0 and (c > 0 or m > 0 or y > 0 or k > 0) and not any(s.endswith("%") for s in [c_str, m_str, y_str, k_str]):
                # If all are <= 1.0 and none has %, treat as decimal fraction 0-1
                if max(c, m, y, k) <= 1.0:
                    c *= 100.0
                    m *= 100.0
                    y *= 100.0
                    k *= 100.0

            if 0.0 <= c <= 100.0 and 0.0 <= m <= 100.0 and 0.0 <= y <= 100.0 and 0.0 <= k <= 100.0:
                hex_val = hex_from_cmyk(c, m, y, k)
                if hex_val not in results:
                    results.append(hex_val)
        except (ValueError, TypeError):
            continue

    return results
