"""
Color matcher.

METHODOLOGY NOTE (distance metric used for naming)
-------------------------------------------------------------
match_rgb() / match_hex() -- "what is the closest named color to
this one" -- now rank candidates using CIEDE2000 (delta_e_2000)
rather than the CIE76 Euclidean-Lab-distance formula (delta_e_76)
used previously.

CIE76 is known to distort perceived distance unevenly across the
color space -- most notably in saturated blues and greens, where
it under- or over-states how different two colors actually look
to the eye. CIEDE2000 corrects for this with hue/chroma/lightness
weighting and is the standard used in professional color-matching
contexts (ICC profile evaluation, Pantone/paint-industry
tolerancing, textile and print QA). Concretely: a ΔE00 under ~1.0
is imperceptible, ~1-2 is perceptible only to a trained eye,
~2-10 is perceptible at a glance, and above ~10 the colors read
as clearly different -- this scale is not directly comparable to
old CIE76 ΔE values, which run larger for the same colors.

delta_e_76() is kept, unchanged, alongside delta_e_2000() below --
palette_generator.py's internal diversity/spacing heuristics were
already tuned against the CIE76 scale and are left exactly as-is;
only the naming lookup in this file changes.

Implementation verified against the published Sharma, Wu & Dalal
(2005) reference pair: Lab(50, 2.6772, -79.7751) vs.
Lab(50, 0, -82.7485) -> ΔE00 = 2.0425 (exact match).
-------------------------------------------------------------
"""

import sqlite3
import math


import os
DB_PATH = "core_logic/generatePalette/colors.db"


# ============================================================
# RGB → LAB
# ============================================================

def rgb_to_lab(r, g, b):
    """
    Convert sRGB (0-255) to CIE Lab (D65).
    """

    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    def linearize(c):
        if c <= 0.04045:
            return c / 12.92

        return ((c + 0.055) / 1.055) ** 2.4

    r = linearize(r)
    g = linearize(g)
    b = linearize(b)

    x = (
        r * 0.4124564 +
        g * 0.3575761 +
        b * 0.1804375
    )

    y = (
        r * 0.2126729 +
        g * 0.7151522 +
        b * 0.0721750
    )

    z = (
        r * 0.0193339 +
        g * 0.1191920 +
        b * 0.9503041
    )

    xn = 0.95047
    yn = 1.00000
    zn = 1.08883

    x /= xn
    y /= yn
    z /= zn

    def f(t):
        delta = 6 / 29

        if t > delta ** 3:
            return t ** (1 / 3)

        return t / (3 * delta ** 2) + 4 / 29

    fx = f(x)
    fy = f(y)
    fz = f(z)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    lab_b = 200 * (fy - fz)

    return L, a, lab_b


# ============================================================
# DELTA E 76
# ============================================================

def delta_e_76(lab1, lab2):
    """
    CIE76 Delta E.
    """

    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2 +
        (lab1[1] - lab2[1]) ** 2 +
        (lab1[2] - lab2[2]) ** 2
    )


# ============================================================
# DELTA E 2000 (CIEDE2000)
# ============================================================

def delta_e_2000(
    lab1,
    lab2,
    kL=1.0,
    kC=1.0,
    kH=1.0,
):
    """
    CIEDE2000 Delta E.

    Implementation follows Sharma, Wu & Dalal (2005), "The
    CIEDE2000 Color-Difference Formula: Implementation Notes,
    Supplementary Test Data, and Mathematical Observations" --
    the paper written specifically to correct the ambiguities in
    the original CIE technical report that caused many public
    implementations to silently disagree with each other.

    kL, kC, kH are the standard parametric weighting factors
    (application-specific adjustments for lightness, chroma, and
    hue sensitivity). They default to 1.0, the CIE-recommended
    "reference conditions" value, which is correct for general
    use -- there is no reason to change them here.
    """

    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.sqrt(a1 * a1 + b1 * b1)
    C2 = math.sqrt(a2 * a2 + b2 * b2)

    c_bar = (C1 + C2) / 2.0

    G = 0.5 * (
        1 - math.sqrt(
            (c_bar ** 7)
            / (c_bar ** 7 + 25.0 ** 7)
        )
    )

    a1_p = a1 * (1 + G)
    a2_p = a2 * (1 + G)

    C1_p = math.sqrt(a1_p * a1_p + b1 * b1)
    C2_p = math.sqrt(a2_p * a2_p + b2 * b2)

    def hue_angle(a_p, b):

        if a_p == 0 and b == 0:
            return 0.0

        angle = math.degrees(
            math.atan2(b, a_p)
        )

        return (
            angle + 360.0
            if angle < 0
            else angle
        )

    h1_p = hue_angle(a1_p, b1)
    h2_p = hue_angle(a2_p, b2)

    delta_L_p = L2 - L1
    delta_C_p = C2_p - C1_p

    if C1_p * C2_p == 0:

        delta_h_p = 0.0

    else:

        diff = h2_p - h1_p

        if diff > 180:
            diff -= 360

        elif diff < -180:
            diff += 360

        delta_h_p = diff

    delta_H_p = (
        2
        * math.sqrt(C1_p * C2_p)
        * math.sin(
            math.radians(delta_h_p) / 2.0
        )
    )

    L_bar_p = (L1 + L2) / 2.0
    C_bar_p = (C1_p + C2_p) / 2.0

    if C1_p * C2_p == 0:

        H_bar_p = h1_p + h2_p

    elif abs(h1_p - h2_p) > 180:

        if h1_p + h2_p < 360:
            H_bar_p = (h1_p + h2_p + 360) / 2.0

        else:
            H_bar_p = (h1_p + h2_p - 360) / 2.0

    else:

        H_bar_p = (h1_p + h2_p) / 2.0

    T = (
        1
        - 0.17 * math.cos(math.radians(H_bar_p - 30))
        + 0.24 * math.cos(math.radians(2 * H_bar_p))
        + 0.32 * math.cos(math.radians(3 * H_bar_p + 6))
        - 0.20 * math.cos(math.radians(4 * H_bar_p - 63))
    )

    delta_theta = 30 * math.exp(
        -(((H_bar_p - 275) / 25) ** 2)
    )

    Rc = 2 * math.sqrt(
        (C_bar_p ** 7)
        / (C_bar_p ** 7 + 25.0 ** 7)
    )

    Sl = 1 + (
        0.015 * (L_bar_p - 50) ** 2
    ) / math.sqrt(
        20 + (L_bar_p - 50) ** 2
    )

    Sc = 1 + 0.045 * C_bar_p

    Sh = 1 + 0.015 * C_bar_p * T

    Rt = -math.sin(
        math.radians(2 * delta_theta)
    ) * Rc

    term_L = delta_L_p / (kL * Sl)
    term_C = delta_C_p / (kC * Sc)
    term_H = delta_H_p / (kH * Sh)

    return math.sqrt(
        term_L ** 2
        + term_C ** 2
        + term_H ** 2
        + Rt * term_C * term_H
    )


# ============================================================
# HEX HELPERS
# ============================================================

def hex_to_rgb(hex_value):
    """
    Convert #RRGGBB or RRGGBB to RGB tuple.
    """

    value = hex_value.strip().lstrip("#")

    if len(value) != 6:
        raise ValueError(
            f"Invalid HEX color: {hex_value}"
        )

    try:
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
    except ValueError:
        raise ValueError(
            f"Invalid HEX color: {hex_value}"
        )

    return r, g, b


def rgb_to_hex(r, g, b):
    """
    Convert RGB to uppercase HEX.
    """

    return "#{:02X}{:02X}{:02X}".format(
        int(r),
        int(g),
        int(b)
    )


# ============================================================
# COLOR MATCHER
# ============================================================

class ColorMatcher:

    def __init__(self, db_path=DB_PATH):

        self.db_path = db_path

        self.conn = sqlite3.connect(
            db_path
        )

        self.colors = self._load_colors()

        self.hex_index = {
            color["hex"]: color
            for color in self.colors
        }

        print(
            f"Loaded {len(self.colors):,} unique HEX colors "
            f"from the database."
        )

    # ========================================================
    # LOAD DATABASE
    # ========================================================

    def _load_colors(self):

        query = """
            SELECT
                id,
                source,
                source_dataset,
                color_id,
                name,
                r,
                g,
                b,
                hex,
                lab_l,
                lab_a,
                lab_b,
                hue,
                chroma,
                preferred,
                name_quality
            FROM colors
            WHERE r IS NOT NULL
              AND g IS NOT NULL
              AND b IS NOT NULL
        """

        rows = self.conn.execute(query).fetchall()

        grouped = {}

        for row in rows:

            (
                db_id,
                source,
                source_dataset,
                color_id,
                name,
                r,
                g,
                b,
                hex_value,
                lab_l,
                lab_a,
                lab_b,
                hue,
                chroma,
                preferred,
                name_quality
            ) = row

            hex_value = hex_value.upper()

            if lab_l is None:

                lab_l, lab_a, lab_b = rgb_to_lab(
                    r,
                    g,
                    b
                )

            record = {
                "id": db_id,
                "source": source,
                "source_dataset": source_dataset,
                "color_id": color_id,
                "name": name,
                "r": r,
                "g": g,
                "b": b,
                "hex": hex_value,
                "lab": (
                    lab_l,
                    lab_a,
                    lab_b
                ),
                "hue": hue,
                "chroma": chroma,
                "preferred": preferred or 0,
                "name_quality": (
                    name_quality
                    if name_quality is not None
                    else 1.0
                )
            }

            grouped.setdefault(
                hex_value,
                []
            ).append(record)

        colors = []

        for hex_value, records in grouped.items():

            base = records[0]

            colors.append({
                "hex": hex_value,
                "r": base["r"],
                "g": base["g"],
                "b": base["b"],
                "lab": base["lab"],
                "hue": base["hue"],
                "chroma": base["chroma"],
                "records": records
            })

        return colors

    # ========================================================
    # NAME RANKING
    # ========================================================

    def _rank_names(self, records):

        ranked = []

        for record in records:

            preferred_bonus = (
                1.5
                if record["preferred"]
                else 0.0
            )

            quality_bonus = (
                record["name_quality"] * 0.5
            )

            score = (
                preferred_bonus +
                quality_bonus
            )

            ranked.append({
                **record,
                "name_score": score
            })

        ranked.sort(
            key=lambda x: (
                -x["name_score"],
                x["name"].lower()
            )
        )

        return ranked

    # ========================================================
    # SAME HEX NAMES
    # ========================================================

    def get_color_names(self, hex_value):

        hex_value = hex_value.upper()

        color = self.hex_index.get(hex_value)

        if color is None:
            return []

        ranked = self._rank_names(
            color["records"]
        )

        return [
            {
                "name": record["name"],
                "source": record["source"],
                "source_dataset": (
                    record["source_dataset"]
                ),
                "preferred": record["preferred"],
                "name_quality": record["name_quality"]
            }
            for record in ranked
        ]

    # ========================================================
    # MATCH RGB
    # ========================================================

    def match_rgb(
        self,
        r,
        g,
        b,
        top_n=10,
        max_delta_e=None
    ):
        """
        Find the closest named colors to (r, g, b).

        max_delta_e, if given, is now on the CIEDE2000 scale
        (see the module-level methodology note): ~2 for "only a
        trained eye would tell these apart", ~10 for "obviously
        different colors". This is a smaller-feeling number than
        the old CIE76-based max_delta_e values were -- that's
        expected, not a bug, since the two scales aren't linearly
        comparable.
        """

        input_lab = rgb_to_lab(
            r,
            g,
            b
        )

        candidates = []

        for color in self.colors:

            distance = delta_e_2000(
                input_lab,
                color["lab"]
            )

            if (
                max_delta_e is not None
                and distance > max_delta_e
            ):
                continue

            candidates.append({
                **color,
                "delta_e": distance
            })

        if not candidates:
            return {
                "input": {
                    "r": r,
                    "g": g,
                    "b": b,
                    "hex": rgb_to_hex(r, g, b)
                },
                "match": None,
                "alternatives": [],
                "same_hex_names": []
            }

        candidates.sort(
            key=lambda x: x["delta_e"]
        )

        # Only inspect the nearest physical colors.
        candidates = candidates[:100]

        processed = []

        for candidate in candidates:

            ranked_names = self._rank_names(
                candidate["records"]
            )

            best_name = ranked_names[0]

            processed.append({
                "hex": candidate["hex"],
                "r": candidate["r"],
                "g": candidate["g"],
                "b": candidate["b"],
                "lab": candidate["lab"],
                "delta_e": candidate["delta_e"],
                "name": best_name["name"],
                "source": best_name["source"],
                "source_dataset": (
                    best_name["source_dataset"]
                ),
                "preferred": best_name["preferred"],
                "name_quality": best_name["name_quality"],
                "names": [
                    {
                        "name": x["name"],
                        "source": x["source"],
                        "source_dataset": (
                            x["source_dataset"]
                        ),
                        "preferred": x["preferred"],
                        "name_quality": x["name_quality"]
                    }
                    for x in ranked_names
                ]
            })

        processed.sort(
            key=lambda x: (
                x["delta_e"],
                -x["preferred"],
                -x["name_quality"]
            )
        )

        best = processed[0]

        # ----------------------------------------------------
        # Remove duplicate HEX/name combinations from
        # alternatives.
        # ----------------------------------------------------

        alternatives = []

        seen = set()

        for candidate in processed:

            key = (
                candidate["hex"],
                candidate["name"].lower()
            )

            if key in seen:
                continue

            seen.add(key)

            alternatives.append({
                "name": candidate["name"],
                "hex": candidate["hex"],
                "source": candidate["source"],
                "source_dataset": (
                    candidate["source_dataset"]
                ),
                "delta_e": candidate["delta_e"]
            })

            if len(alternatives) >= top_n:
                break

        return {
            "input": {
                "r": r,
                "g": g,
                "b": b,
                "hex": rgb_to_hex(r, g, b)
            },

            "match": {
                "name": best["name"],
                "hex": best["hex"],
                "source": best["source"],
                "source_dataset": (
                    best["source_dataset"]
                ),
                "delta_e": best["delta_e"],
                "preferred": best["preferred"],
                "name_quality": best["name_quality"]
            },

            "alternatives": alternatives,

            "same_hex_names": best["names"]
        }

    # ========================================================
    # MATCH HEX
    # ========================================================

    def match_hex(
        self,
        hex_value,
        top_n=10,
        max_delta_e=None
    ):

        r, g, b = hex_to_rgb(
            hex_value
        )

        return self.match_rgb(
            r,
            g,
            b,
            top_n=top_n,
            max_delta_e=max_delta_e
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        if self.conn:
            self.conn.close()

            self.conn = None


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    matcher = ColorMatcher()

    tests = [
        ("Burgundy", "#900020"),
        ("Oxblood", "#800020"),
        ("Sherwin Burgundy", "#63333E"),
        ("Vivid Burgundy", "#9F1D35"),
        ("Old Burgundy", "#43302E"),
    ]

    for label, hex_value in tests:

        result = matcher.match_hex(
            hex_value,
            top_n=10
        )

        print()
        print("=" * 70)
        print(label)

        print(
            "INPUT:",
            result["input"]["hex"]
        )

        if result["match"] is None:
            print("NO MATCH")
            continue

        print(
            "BEST:",
            result["match"]["name"],
            result["match"]["hex"],
            "ΔE=",
            round(
                result["match"]["delta_e"],
                3
            )
        )

        print()
        print("NAMES FOR BEST HEX:")

        for item in result["same_hex_names"]:

            print(
                f"  {item['name']:<30}"
                f"{item['source']:<20}"
                f"preferred={item['preferred']}"
            )

        print()
        print("ALTERNATIVES:")

        for candidate in result["alternatives"]:

            print(
                f"  {candidate['name']:<30}"
                f"{candidate['hex']:<10}"
                f"ΔE={candidate['delta_e']:.3f}"
            )

    matcher.close()
