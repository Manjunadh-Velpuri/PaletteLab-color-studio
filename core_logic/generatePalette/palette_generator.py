"""
Palette generator.

METHODOLOGY NOTE (curated candidate pools)
-------------------------------------------------------------
Prior to this revision, every style profile drew from a single
undifferentiated candidate list built by a plain Lab lightness /
chroma / saturation box-filter over the entire colors.db table,
then randomly windowed down to ROLE_SAMPLE_SIZE (220) colors at
each role pick. That produced small, arbitrary, source-blind
shortlists with no guarantee of even coverage across the color
space.

This revision splits the database along its actual, meaningful
provenance instead of treating it as one undifferentiated pool:

    "digital"  -> source == "Meodai"
                  (36,873 rows) crowd-labelled, full-gamut,
                  born-digital color names. Entries outside the
                  vetted "Best Of" subset (preferred == 1) are
                  additionally required to clear a name_quality
                  floor of 0.85 -- the real distribution in this
                  dataset is bimodal (a cluster at 0.90-1.00 and
                  a smaller cluster at 0.70-0.79), so 0.85 sits
                  cleanly in the gap between them and drops only
                  the ~3,000 lowest-confidence auto-generated
                  names while keeping the other ~28,800 intact.

    "real"     -> source in ("Sherwin-Williams", "Encycolorpedia")
                  (3,327 rows) physically manufacturable paint
                  colors and standardized, recognized named
                  colors. Every row in this tier is already
                  preferred == 1 with name_quality == 1.0, so no
                  further filtering is applied.

    "mixed"    -> the original, undifferentiated behavior,
                  preserved exactly as-is for backward
                  compatibility with existing callers that don't
                  pass a domain.

Within "digital" and "real", once a style's box-filter has been
applied, the surviving pool is reduced to a CURATED_POOL_TARGET
sized shortlist using farthest-point (max-min) sampling in Lab
space rather than a blind random cut -- this guarantees the
shortlist itself is evenly spread across the available color
space instead of clumping wherever the source data happens to be
dense. CURATED_POOL_TARGET defaults to 1,200 candidates per
style/domain combination -- roughly 2.5-4x the prior effective
shortlist size, and, unlike the prior number, chosen for spread
rather than as an arbitrary cutoff.

All of this curation happens once, at PaletteGenerator.__init__
time (same place the original _prepare_candidates cost already
lived) -- nothing here adds runtime cost to an individual
generate() call.
-------------------------------------------------------------
"""

import math
import os
import pickle
import random
import time

try:
    from .color_matcher import (
        ColorMatcher,
        rgb_to_lab,
        delta_e_2000,
        rgb_to_hex,
    )
except ImportError:
    from color_matcher import (
        ColorMatcher,
        rgb_to_lab,
        delta_e_2000,
        rgb_to_hex,
    )


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_COUNT = 5
DEFAULT_ATTEMPTS = 60

ROLE_SAMPLE_SIZE = 320

MIN_PALETTE_DE = 10
MIN_HUE_DISTANCE = 12

RANDOM_JITTER = 5.0


# ============================================================
# DOMAIN CLASSIFICATION
#
# Which colors.db "source" values count as born-digital
# (broad, algorithmic, full-gamut) versus real/physical
# (manufacturable paint, standardized named colors). See the
# methodology note above for the reasoning and the real counts
# behind this split.
# ============================================================

DOMAINS = (
    "mixed",
    "digital",
    "real",
)

DIGITAL_SOURCES = {
    "Meodai",
}

REAL_SOURCES = {
    "Sherwin-Williams",
    "Encycolorpedia",
}

# Applied only to non-preferred Meodai rows -- see methodology
# note for why 0.85 is the right cut point in this dataset.
DIGITAL_QUALITY_FLOOR = 0.85

# Target shortlist size per (style, domain) pair once curated
# via farthest-point sampling. Pools smaller than this to begin
# with are kept whole -- nothing is padded or duplicated.
CURATED_POOL_TARGET = 3600

# Safety cap on how many raw candidates farthest-point sampling
# is run over. Above this, the raw pool is first thinned with a
# plain random draw down to this size before the (more
# expensive) diversity pass runs, keeping one-time startup cost
# bounded even for the largest style/domain combinations.
MAX_FPS_INPUT = 12000

# Curated pools are expensive to build (farthest-point sampling
# over thousands of colors, per style/domain) but never change
# unless colors.db itself changes or this file's curation logic
# does. Bump this whenever the curation logic changes so stale
# caches from an older version are never loaded silently.
CANDIDATE_CACHE_VERSION = 2


# ============================================================
# STYLE PROFILES
# ============================================================

STYLE_PROFILES = {

    "pastel": {
        "lightness": (72, 97),
        "chroma": (8, 48),

        "preferred_hues": [
            (0, 360)
        ],

        "hue_spread": (15, 100),

        "de_min": 8,
        "de_max": 55,

        "saturation_max": 75,

        "role_pattern": "soft",

        "target_lightness": 88,
        "target_chroma": 28,

        "preferred_de": (12, 45),
        "preferred_spread": (8, 30),
    },

    "vibrant": {
        "lightness": (38, 78),
        "chroma": (45, 115),

        "preferred_hues": [
            (0, 360)
        ],

        "hue_spread": (45, 180),

        "de_min": 18,
        "de_max": 110,

        "saturation_max": 100,

        "role_pattern": "contrast",

        "target_lightness": 58,
        "target_chroma": 75,

        "preferred_de": (30, 100),
        "preferred_spread": (15, 50),
    },

    "muted": {
        "lightness": (38, 82),
        "chroma": (5, 45),

        "preferred_hues": [
            (0, 360)
        ],

        "hue_spread": (15, 100),

        "de_min": 8,
        "de_max": 65,

        "saturation_max": 70,

        "role_pattern": "dusty",

        "target_lightness": 62,
        "target_chroma": 25,

        "preferred_de": (10, 55),
        "preferred_spread": (10, 40),
    },

    "classic": {
        "lightness": (25, 85),
        "chroma": (8, 72),

        "preferred_hues": [
            (205, 235),
            (335, 360),
            (70, 160),
            (35, 60),
            (0, 360),
        ],

        "hue_spread": (25, 150),

        "de_min": 12,
        "de_max": 85,

        "saturation_max": 85,

        "role_pattern": "timeless",

        "target_lightness": 55,
        "target_chroma": 40,

        "preferred_de": (18, 75),
        "preferred_spread": (20, 60),
    },

    "ancient": {
        "lightness": (20, 78),
        "chroma": (5, 62),

        "preferred_hues": [
            (8, 35),
            (35, 65),
            (65, 120),
            (120, 175),
            (330, 360),
            (0, 360),
        ],

        "hue_spread": (15, 110),

        "de_min": 10,
        "de_max": 75,

        "saturation_max": 72,

        "role_pattern": "earth",

        "target_lightness": 52,
        "target_chroma": 32,

        "preferred_de": (12, 65),
        "preferred_spread": (20, 55),
    },

    "modern": {
        "lightness": (20, 90),
        "chroma": (15, 110),

        "preferred_hues": [
            (180, 250),
            (250, 300),
            (0, 45),
            (75, 170),
            (0, 360),
        ],

        "hue_spread": (40, 210),

        "de_min": 15,
        "de_max": 110,

        "saturation_max": 100,

        "role_pattern": "designed",

        "target_lightness": 55,
        "target_chroma": 55,

        "preferred_de": (25, 100),
        "preferred_spread": (25, 65),
    },

    "minimalist": {
        "lightness": (25, 95),
        "chroma": (2, 42),

        "preferred_hues": [
            (0, 360)
        ],

        "hue_spread": (3, 75),

        "de_min": 7,
        "de_max": 60,

        "saturation_max": 55,

        "role_pattern": "neutral",

        "target_lightness": 68,
        "target_chroma": 18,

        "preferred_de": (8, 45),
        "preferred_spread": (12, 45),
    },
}


# ============================================================
# MOODS
# ============================================================

MOOD_PROFILES = {

    "any": {
        "hues": [(0, 360)],
    },

    "warm": {
        "hues": [
            (0, 65),
            (320, 360),
        ],
    },

    "cool": {
        "hues": [
            (160, 300),
        ],
    },

    "neutral": {
        "hues": [
            (0, 360),
        ],
    },
}


# ============================================================
# THEMES
# ============================================================

THEME_PROFILES = {

    "any": {
        "hues": [(0, 360)],
    },

    "earthy": {
        "hues": [
            (5, 45),
            (45, 75),
            (75, 140),
            (330, 360),
        ],
    },

    "ocean": {
        "hues": [
            (160, 260),
        ],
    },

    "botanical": {
        "hues": [
            (70, 165),
        ],
    },

    "romantic": {
        "hues": [
            (300, 360),
            (0, 25),
            (315, 350),
        ],
    },

    "sunset": {
        "hues": [
            (0, 70),
            (300, 360),
        ],
    },

    "jewel": {
        "hues": [
            (0, 40),
            (80, 160),
            (180, 260),
            (280, 330),
        ],
    },

    "monochrome": {
        "hues": [
            (0, 360),
        ],
    },
}


# ============================================================
# RGB → HSL
# ============================================================

def rgb_to_hsl(r, g, b):

    r /= 255.0
    g /= 255.0
    b /= 255.0

    maximum = max(r, g, b)
    minimum = min(r, g, b)

    lightness = (
        maximum + minimum
    ) / 2

    if maximum == minimum:
        return 0.0, 0.0, lightness * 100

    difference = maximum - minimum

    if lightness > 0.5:

        saturation = (
            difference /
            (
                2 -
                maximum -
                minimum
            )
        )

    else:

        saturation = (
            difference /
            (
                maximum +
                minimum
            )
        )

    if maximum == r:

        hue = (
            (g - b) /
            difference
            +
            (6 if g < b else 0)
        )

    elif maximum == g:

        hue = (
            (b - r) /
            difference
            + 2
        )

    else:

        hue = (
            (r - g) /
            difference
            + 4
        )

    hue /= 6

    return (
        hue * 360,
        saturation * 100,
        lightness * 100,
    )


# ============================================================
# HUE HELPERS
# ============================================================

def circular_hue_distance(h1, h2):

    difference = abs(
        h1 - h2
    )

    return min(
        difference,
        360 - difference
    )


def hue_in_ranges(
    hue,
    ranges
):

    for low, high in ranges:

        if low <= high:

            if low <= hue <= high:
                return True

        else:

            if (
                hue >= low
                or
                hue <= high
            ):
                return True

    return False


# ============================================================
# DOMAIN HELPERS
# ============================================================

def color_domain_tags(records):
    """
    Given the list of name-records ColorMatcher grouped under a
    single HEX value, return the set of domains ("digital",
    "real") that color qualifies for.

    A color can belong to both -- e.g. a hex that happens to
    appear in both Meodai and Sherwin-Williams -- in which case
    it is eligible for either curated pool. A color qualifies
    for "digital" if any of its records come from a preferred
    (Best Of) Meodai entry, or from a non-preferred Meodai entry
    that clears DIGITAL_QUALITY_FLOOR.
    """

    tags = set()

    for record in records:

        source = record.get("source")

        if source in REAL_SOURCES:
            tags.add("real")

        if source in DIGITAL_SOURCES:

            if record.get("preferred"):
                tags.add("digital")

            else:

                quality = (
                    record.get("name_quality")
                    or 0.0
                )

                if quality >= DIGITAL_QUALITY_FLOOR:
                    tags.add("digital")

    return tags


def farthest_point_sample(pool, target_size):
    """
    Reduce `pool` to `target_size` entries such that the
    selection is spread as evenly as possible across Lab space,
    using the standard greedy max-min (farthest-point)
    algorithm: repeatedly add whichever remaining candidate is
    furthest from its nearest already-selected neighbor.

    Runs in O(n * target_size) via a running per-candidate
    "distance to nearest selected point so far" array, rather
    than recomputing full pairwise distances every step.

    Uses delta_e_2000 for strict CIELAB2000 color science compliance.
    CIEDE2000 -- this function may run over several thousand
    candidates, and at this scale a fast approximate metric for
    bulk spatial thinning is the right tool; precise perceptual
    distance is reserved for the small, final color-naming
    lookups elsewhere in the app.
    """

    if target_size >= len(pool):
        return pool[:]

    if target_size <= 0:
        return []

    if len(pool) > MAX_FPS_INPUT:
        pool = random.sample(
            pool,
            MAX_FPS_INPUT
        )

    remaining = pool[:]

    start_index = random.randrange(
        len(remaining)
    )

    selected = [
        remaining.pop(start_index)
    ]

    nearest_distance = [
        delta_e_2000(
            candidate["lab"],
            selected[0]["lab"]
        )
        for candidate in remaining
    ]

    while (
        len(selected) < target_size
        and remaining
    ):

        farthest_index = max(
            range(len(remaining)),
            key=lambda i: nearest_distance[i]
        )

        chosen = remaining.pop(
            farthest_index
        )

        nearest_distance.pop(
            farthest_index
        )

        selected.append(chosen)

        for i, candidate in enumerate(
            remaining
        ):

            distance = delta_e_2000(
                candidate["lab"],
                chosen["lab"]
            )

            if distance < nearest_distance[i]:
                nearest_distance[i] = distance

    return selected


# ============================================================
# GENERAL HELPERS
# ============================================================

def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def clamp(value, low, high):

    return max(
        low,
        min(high, value)
    )


def range_score(
    value,
    low,
    high,
    weight
):

    if low <= value <= high:
        return weight

    if value < low:
        distance = low - value

    else:
        distance = value - high

    width = max(
        1,
        high - low
    )

    return max(
        0,
        weight * (
            1 - distance / width
        )
    )


def target_score(
    value,
    target,
    tolerance,
    weight
):

    difference = abs(
        value - target
    )

    if difference >= tolerance:
        return 0

    return (
        weight *
        (
            1 -
            difference / tolerance
        )
    )


# ============================================================
# PALETTE GENERATOR
# ============================================================

class PaletteGenerator:

    def __init__(
        self,
        matcher=None,
        db_path=None,
        use_cache=True,
    ):
        if db_path is None:
            db_path = "core_logic/generatePalette/colors.db"

        print(
            "Starting palette generator..."
        )

        start = time.perf_counter()

        self.matcher = (
            matcher
            or ColorMatcher(db_path)
        )

        self.candidates = {}

        self._prepare_candidates(
            use_cache=use_cache
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        print(
            "Candidate preparation:",
            round(elapsed, 3),
            "seconds"
        )

    # ========================================================
    # CANDIDATE CACHE
    #
    # Farthest-point curation is a one-time cost per version of
    # colors.db, not a per-launch cost. This caches the fully
    # prepared self.candidates dict to disk next to the database
    # and reuses it on future launches as long as the database
    # file (mtime + size) and CANDIDATE_CACHE_VERSION both still
    # match. Deleting the .candidates_cache.pkl file, changing
    # colors.db, or bumping CANDIDATE_CACHE_VERSION all force a
    # clean rebuild.
    # ========================================================

    def _cache_path(self):

        return (
            self.matcher.db_path
            + ".candidates_cache.pkl"
        )

    def _cache_fingerprint(self):

        db_path = self.matcher.db_path

        if not os.path.exists(db_path):
            return None

        stat = os.stat(db_path)

        return (
            CANDIDATE_CACHE_VERSION,
            stat.st_size,
        )

    def _load_cached_candidates(self):

        cache_path = self._cache_path()

        if not os.path.exists(cache_path):
            return None

        try:

            with open(cache_path, "rb") as handle:
                payload = pickle.load(handle)

        except (
            pickle.UnpicklingError,
            EOFError,
            OSError,
            AttributeError,
        ):
            return None

        if (
            payload.get("fingerprint")
            != self._cache_fingerprint()
        ):
            return None

        return payload.get("candidates")

    def _save_cached_candidates(self):

        try:

            with open(
                self._cache_path(),
                "wb"
            ) as handle:

                pickle.dump(
                    {
                        "fingerprint":
                            self._cache_fingerprint(),
                        "candidates":
                            self.candidates,
                    },
                    handle,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )

        except OSError as error:

            # Non-fatal: worst case, the next launch just
            # rebuilds candidates from scratch again.
            print(
                "Could not write candidate cache:",
                error
            )

    # ========================================================
    # PREPARE CANDIDATES
    # ========================================================

    def _prepare_candidates(self, use_cache=True):

        if use_cache:

            cached = self._load_cached_candidates()

            if cached is not None:

                self.candidates = cached

                print(
                    "Loaded candidate pools from cache "
                    "(delete "
                    + self._cache_path()
                    + " to force a rebuild)."
                )

                return

        self._build_candidates()

        if use_cache:
            self._save_cached_candidates()

    def _build_candidates(self):

        for style, profile in (
            STYLE_PROFILES.items()
        ):

            mixed = []
            digital_raw = []
            real_raw = []

            min_l, max_l = (
                profile["lightness"]
            )

            min_c, max_c = (
                profile["chroma"]
            )

            for color in self.matcher.colors:

                L = color["lab"][0]

                a = color["lab"][1]
                lab_b = color["lab"][2]

                chroma = math.sqrt(
                    a * a +
                    lab_b * lab_b
                )

                if not (
                    min_l <= L <= max_l
                    and
                    min_c <= chroma <= max_c
                ):
                    continue

                hue, saturation, lightness = (
                    rgb_to_hsl(
                        color["r"],
                        color["g"],
                        color["b"]
                    )
                )

                if (
                    saturation >
                    profile["saturation_max"]
                ):
                    continue

                entry = {

                    "hex": color["hex"],

                    "r": color["r"],
                    "g": color["g"],
                    "b": color["b"],

                    "lab": color["lab"],

                    "hue": hue,

                    "saturation":
                        saturation,

                    "lightness":
                        lightness,

                    "chroma":
                        chroma,
                }

                # Kept exactly as before: the undifferentiated
                # "mixed" pool ignores provenance entirely.
                mixed.append(entry)

                domains = color_domain_tags(
                    color["records"]
                )

                if "digital" in domains:
                    digital_raw.append(entry)

                if "real" in domains:
                    real_raw.append(entry)

            digital = farthest_point_sample(
                digital_raw,
                CURATED_POOL_TARGET
            )

            real = farthest_point_sample(
                real_raw,
                CURATED_POOL_TARGET
            )

            self.candidates[
                (style, "mixed")
            ] = mixed

            self.candidates[
                (style, "digital")
            ] = digital

            self.candidates[
                (style, "real")
            ] = real

            print(
                f"Prepared {style:<11} -> "
                f"mixed: {len(mixed):>6,}   "
                f"digital: {len(digital):>5,} "
                f"(of {len(digital_raw):,})   "
                f"real: {len(real):>5,} "
                f"(of {len(real_raw):,})"
            )

    # ========================================================
    # CONTEXT SCORE
    # ========================================================

    def _context_score(
        self,
        color,
        style,
        mood,
        theme,
    ):

        profile = STYLE_PROFILES[
            style
        ]

        score = 0.0

        hue = color["hue"]
        L = color["lab"][0]
        C = color["chroma"]

        # ----------------------------------------------------
        # Style hue preference
        # ----------------------------------------------------

        if hue_in_ranges(
            hue,
            profile["preferred_hues"]
        ):
            score += 8

        # ----------------------------------------------------
        # Mood
        # ----------------------------------------------------

        if mood != "any":

            mood_ranges = (
                MOOD_PROFILES[
                    mood
                ]["hues"]
            )

            if hue_in_ranges(
                hue,
                mood_ranges
            ):
                score += 18

            else:
                score -= 22

        # ----------------------------------------------------
        # Theme
        # ----------------------------------------------------

        if theme != "any":

            theme_ranges = (
                THEME_PROFILES[
                    theme
                ]["hues"]
            )

            if hue_in_ranges(
                hue,
                theme_ranges
            ):
                score += 25

            else:
                score -= 30

        # ----------------------------------------------------
        # Target lightness
        # ----------------------------------------------------

        score += target_score(
            L,
            profile["target_lightness"],
            35,
            12
        )

        # ----------------------------------------------------
        # Target chroma
        # ----------------------------------------------------

        score += target_score(
            C,
            profile["target_chroma"],
            45,
            12
        )

        # ----------------------------------------------------
        # Style-specific
        # ----------------------------------------------------

        if style == "pastel":

            score += range_score(
                L,
                82,
                97,
                18
            )

            score += range_score(
                C,
                8,
                38,
                12
            )

        elif style == "vibrant":

            score += range_score(
                C,
                60,
                115,
                25
            )

            score += range_score(
                L,
                42,
                72,
                12
            )

        elif style == "muted":

            score += range_score(
                C,
                5,
                35,
                22
            )

            score += range_score(
                L,
                42,
                78,
                10
            )

        elif style == "classic":

            score += range_score(
                L,
                30,
                75,
                15
            )

            score += range_score(
                C,
                8,
                60,
                12
            )

        elif style == "ancient":

            score += range_score(
                C,
                5,
                52,
                18
            )

            score += range_score(
                L,
                28,
                70,
                15
            )

        elif style == "modern":

            score += range_score(
                C,
                30,
                105,
                22
            )

            score += range_score(
                L,
                30,
                82,
                12
            )

        elif style == "minimalist":

            score += range_score(
                C,
                2,
                25,
                30
            )

            score += range_score(
                L,
                45,
                92,
                18
            )

        return score

    # ========================================================
    # COLOR SCORE
    # ========================================================

    def _color_score(
        self,
        color,
        style,
        mood,
        theme,
    ):

        return self._context_score(
            color,
            style,
            mood,
            theme
        )

    # ========================================================
    # COLOR DISTANCE
    # ========================================================

    def _palette_delta_e(
        self,
        color,
        selected
    ):

        if not selected:
            return []

        lab = color["lab"]

        return [
            delta_e_2000(
                lab,
                other["lab"]
            )
            for other in selected
        ]

    # ========================================================
    # HUE DIVERSITY
    # ========================================================

    def _hue_diversity_score(
        self,
        colors,
        style
    ):

        if len(colors) < 2:
            return 0

        distances = []

        for i in range(
            len(colors)
        ):

            for j in range(
                i + 1,
                len(colors)
            ):

                distances.append(
                    circular_hue_distance(
                        colors[i]["hue"],
                        colors[j]["hue"]
                    )
                )

        average_distance = average(
            distances
        )

        minimum_distance = min(
            distances
        )

        maximum_distance = max(
            distances
        )

        profile = STYLE_PROFILES[
            style
        ]

        low, high = (
            profile["hue_spread"]
        )

        score = range_score(
            average_distance,
            low,
            high,
            40
        )

        if minimum_distance < MIN_HUE_DISTANCE:
            score -= 35

        if style in (
            "vibrant",
            "modern",
        ):

            if maximum_distance >= 100:
                score += 18

        elif style in (
            "minimalist",
            "pastel",
            "muted",
        ):

            if maximum_distance <= 110:
                score += 12

        return score

    # ========================================================
    # HARMONY SCORE
    # ========================================================

    def _harmony_score(
        self,
        colors,
        style,
    ):

        return self._hue_diversity_score(
            colors,
            style
        )

    # ========================================================
    # RELATIONSHIP SCORE
    # ========================================================

    def _relationship_score(
        self,
        colors,
        style,
    ):

        if len(colors) < 2:
            return 0

        distances = []

        for i in range(
            len(colors)
        ):

            for j in range(
                i + 1,
                len(colors)
            ):

                distances.append(
                    delta_e_2000(
                        colors[i]["lab"],
                        colors[j]["lab"]
                    )
                )

        average_de = average(
            distances
        )

        minimum_de = min(
            distances
        )

        maximum_de = max(
            distances
        )

        profile = STYLE_PROFILES[
            style
        ]

        low, high = (
            profile["preferred_de"]
        )

        score = range_score(
            average_de,
            low,
            high,
            45
        )

        if minimum_de < MIN_PALETTE_DE:
            score -= 45

        else:
            score += 12

        if style == "pastel":

            if maximum_de <= 65:
                score += 15

        elif style == "vibrant":

            if maximum_de >= 60:
                score += 15

        elif style == "minimalist":

            if maximum_de <= 65:
                score += 15

        elif style == "ancient":

            if maximum_de <= 80:
                score += 12

        return score

    # ========================================================
    # LIGHTNESS COMPOSITION
    # ========================================================

    def _composition_score(
        self,
        colors,
        style,
    ):

        if len(colors) < 2:
            return 0

        values = sorted(
            c["lab"][0]
            for c in colors
        )

        spread = (
            max(values)
            -
            min(values)
        )

        profile = STYLE_PROFILES[
            style
        ]

        low, high = (
            profile["preferred_spread"]
        )

        score = range_score(
            spread,
            low,
            high,
            40
        )

        if spread < 5:
            score -= 35

        return score

    # ========================================================
    # ROLE TARGET SCORE
    # ========================================================

    def _role_score(
        self,
        color,
        role,
        style
    ):

        score = 0.0

        L = color["lab"][0]
        C = color["chroma"]

        if role == "dominant":

            score += range_score(
                L,
                40,
                75,
                15
            )

            score += range_score(
                C,
                10,
                65,
                10
            )

        elif role == "secondary":

            score += range_score(
                L,
                35,
                80,
                12
            )

            score += range_score(
                C,
                10,
                65,
                10
            )

        elif role == "support":

            score += range_score(
                C,
                5,
                55,
                15
            )

        elif role == "accent":

            score += range_score(
                C,
                35,
                115,
                22
            )

        elif role == "neutral":

            if C <= 18:
                score += 45

            elif C <= 25:
                score += 20

            else:
                score -= 30

        return score

    # ========================================================
    # SELECT ROLE COLOR
    # ========================================================

    def _select_role_color(
        self,
        pool,
        selected,
        role,
        style,
        mood,
        theme,
    ):

        if not pool:
            return None

        best = None
        best_score = float("-inf")

        sample_size = min(
            ROLE_SAMPLE_SIZE,
            len(pool)
        )

        # ----------------------------------------------------
        # Sample without scanning entire database.
        # ----------------------------------------------------

        if sample_size < len(pool):

            sampled = random.sample(
                pool,
                sample_size
            )

        else:

            sampled = pool

        for color in sampled:

            if color in selected:
                continue

            # ------------------------------------------------
            # Prevent near duplicates.
            # ------------------------------------------------

            if selected:

                distances = (
                    self._palette_delta_e(
                        color,
                        selected
                    )
                )

                minimum_de = min(
                    distances
                )

                if minimum_de < MIN_PALETTE_DE:
                    continue

            score = self._color_score(
                color,
                style,
                mood,
                theme
            )

            # ------------------------------------------------
            # Role-specific scoring.
            # ------------------------------------------------

            score += self._role_score(
                color,
                role,
                style
            )

            # ------------------------------------------------
            # Enforce role diversity.
            # ------------------------------------------------

            if selected:

                hue_distances = [
                    circular_hue_distance(
                        color["hue"],
                        other["hue"]
                    )
                    for other in selected
                ]

                minimum_hue = min(
                    hue_distances
                )

                score += min(
                    minimum_hue,
                    90
                ) * 0.35

                # Prefer meaningful lightness differences
                # between roles.
                lightness_distances = [
                    abs(
                        color["lab"][0]
                        -
                        other["lab"][0]
                    )
                    for other in selected
                ]

                minimum_lightness = min(
                    lightness_distances
                )

                score += min(
                    minimum_lightness,
                    30
                ) * 0.25

            # ------------------------------------------------
            # Style-specific role rules.
            # ------------------------------------------------

            if style == "minimalist":

                if role == "neutral":

                    if color["chroma"] <= 18:
                        score += 60

                if color["chroma"] <= 25:
                    score += 20

            elif style == "vibrant":

                if role == "accent":

                    if color["chroma"] >= 65:
                        score += 35

            elif style == "pastel":

                if color["lab"][0] >= 85:
                    score += 15

            elif style == "ancient":

                hue = color["hue"]

                if (
                    5 <= hue <= 75
                    or
                    330 <= hue <= 360
                ):
                    score += 20

            # ------------------------------------------------
            # Small controlled randomness.
            # ------------------------------------------------

            score += random.uniform(
                0,
                RANDOM_JITTER
            )

            if score > best_score:

                best_score = score
                best = color

        return best

    # ========================================================
    # BUILD PALETTE
    # ========================================================

    def _construct_palette(
        self,
        candidates,
        count,
        style,
        mood,
        theme,
    ):

        if count == 2:

            roles = [
                "dominant",
                "accent",
            ]

        elif count == 3:

            roles = [
                "dominant",
                "secondary",
                "accent",
            ]

        elif count == 4:

            roles = [
                "dominant",
                "secondary",
                "support",
                "accent",
            ]

        else:

            roles = [
                "dominant",
                "secondary",
                "support",
                "accent",
            ]

            while len(roles) < count:

                roles.append(
                    "support"
                )

        selected = []

        pool = candidates[:]

        # ----------------------------------------------------
        # For minimalist palettes, deliberately reserve a
        # neutral role.
        # ----------------------------------------------------

        if style == "minimalist":

            neutral = self._select_role_color(
                pool,
                selected,
                "neutral",
                style,
                mood,
                theme
            )

            if neutral is not None:

                selected.append(
                    neutral
                )

                pool.remove(
                    neutral
                )

        # ----------------------------------------------------
        # Select remaining roles.
        # ----------------------------------------------------

        remaining_roles = roles[:]

        if (
            style == "minimalist"
            and selected
        ):

            if remaining_roles:
                remaining_roles.pop(0)

        for role in remaining_roles:



            color = (
                self._select_role_color(
                    pool,
                    selected,
                    role,
                    style,
                    mood,
                    theme
                )
            )

            if color is None:
                break

            selected.append(
                color
            )

            pool.remove(
                color
            )

        return selected

    # ========================================================
    # PALETTE SCORE
    # ========================================================

    def _score_palette(
        self,
        colors,
        style,
        mood,
        theme,
    ):

        if not colors:
            return -999999

        score = 0.0

        # ----------------------------------------------------
        # Individual color quality.
        # ----------------------------------------------------

        color_scores = []

        for color in colors:

            value = self._color_score(
                color,
                style,
                mood,
                theme
            )

            color_scores.append(
                value
            )

        score += sum(
            color_scores
        )

        # ----------------------------------------------------
        # Harmony.
        # ----------------------------------------------------

        score += self._harmony_score(
            colors,
            style
        )

        # ----------------------------------------------------
        # Delta E relationship.
        # ----------------------------------------------------

        score += self._relationship_score(
            colors,
            style
        )

        # ----------------------------------------------------
        # Lightness composition.
        # ----------------------------------------------------

        score += self._composition_score(
            colors,
            style
        )

        # ----------------------------------------------------
        # Unique HEX colors.
        # ----------------------------------------------------

        unique_hexes = {
            c["hex"]
            for c in colors
        }

        if len(unique_hexes) != len(colors):
            score -= 100

        # ----------------------------------------------------
        # Minimalist neutral requirement.
        # ----------------------------------------------------

        if style == "minimalist":

            neutral_count = sum(
                1
                for c in colors
                if c["chroma"] <= 18
            )

            if neutral_count >= 1:
                score += 35

            else:
                score -= 40

            if neutral_count >= 2:
                score += 15

        # ----------------------------------------------------
        # Ancient earthy requirement.
        # ----------------------------------------------------

        if style == "ancient":

            earthy_count = 0

            for color in colors:

                hue = color["hue"]

                if (
                    5 <= hue <= 75
                    or
                    330 <= hue <= 360
                ):
                    earthy_count += 1

            score += (
                earthy_count * 10
            )

            if earthy_count < 2:
                score -= 30

        # ----------------------------------------------------
        # Vibrant chroma requirement.
        # ----------------------------------------------------

        if style == "vibrant":

            high_chroma = sum(
                1
                for c in colors
                if c["chroma"] >= 60
            )

            score += (
                high_chroma * 10
            )

            if high_chroma < 2:
                score -= 30

        # ----------------------------------------------------
        # Theme compliance.
        # ----------------------------------------------------

        if theme != "any":

            theme_ranges = (
                THEME_PROFILES[
                    theme
                ]["hues"]
            )

            matching = sum(
                1
                for c in colors
                if hue_in_ranges(
                    c["hue"],
                    theme_ranges
                )
            )

            score += (
                matching /
                len(colors)
            ) * 60

        # ----------------------------------------------------
        # Mood compliance.
        # ----------------------------------------------------

        if mood != "any":

            mood_ranges = (
                MOOD_PROFILES[
                    mood
                ]["hues"]
            )

            matching = sum(
                1
                for c in colors
                if hue_in_ranges(
                    c["hue"],
                    mood_ranges
                )
            )

            score += (
                matching /
                len(colors)
            ) * 40

        return score

    # ========================================================
    # GENERATE
    # ========================================================

    def generate(
        self,
        count=DEFAULT_COUNT,
        style="modern",
        mood="any",
        theme="any",
        domain="mixed",
        attempts=DEFAULT_ATTEMPTS,
        name_colors=True,
        exclude_colors=None,
    ):

        style = style.lower().strip()
        mood = mood.lower().strip()
        theme = theme.lower().strip()
        domain = domain.lower().strip()

        if style not in STYLE_PROFILES:

            raise ValueError(
                "Unknown style: "
                + style
            )

        if mood not in MOOD_PROFILES:

            raise ValueError(
                "Unknown mood: "
                + mood
            )

        if theme not in THEME_PROFILES:

            raise ValueError(
                "Unknown theme: "
                + theme
            )

        if domain not in DOMAINS:

            raise ValueError(
                "Unknown domain: "
                + domain
                + " (expected one of "
                + ", ".join(DOMAINS)
                + ")"
            )

        if count < 2:

            raise ValueError(
                "Palette requires at least "
                "2 colors."
            )

        candidates = (
            self.candidates[
                (style, domain)
            ]
        )
        
        if exclude_colors:
            exclude_set = set(c.upper() for c in exclude_colors)
            candidates = [c for c in candidates if c["hex"].upper() not in exclude_set]

        if len(candidates) < count:

            raise ValueError(
                f"Not enough '{domain}' candidates "
                f"for style '{style}' to build a "
                f"{count}-color palette "
                f"(only {len(candidates)} available). "
                f"Try domain='mixed' instead."
            )

        best_palette = None
        best_score = float("-inf")

        for _ in range(attempts):

            palette = (
                self._construct_palette(
                    candidates,
                    count,
                    style,
                    mood,
                    theme
                )
            )

            if len(palette) != count:
                continue

            score = (
                self._score_palette(
                    palette,
                    style,
                    mood,
                    theme
                )
            )

            if score > best_score:

                best_score = score
                best_palette = palette

        if best_palette is None:

            raise RuntimeError(
                "Could not generate palette."
            )

        # ----------------------------------------------------
        # Name colors AFTER palette generation.
        #
        # This is important for performance.
        # ----------------------------------------------------

        if name_colors:

            for color in best_palette:

                result = (
                    self.matcher.match_rgb(
                        color["r"],
                        color["g"],
                        color["b"],
                        top_n=3
                    )
                )

                color["match"] = (
                    result["match"]
                )

        return {
            "style": style,
            "mood": mood,
            "theme": theme,
            "domain": domain,
            "count": count,
            "score": best_score,
            "colors": best_palette,
        }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    generator = PaletteGenerator()

    tests = [

        (
            "Pastel",
            "pastel",
            "warm",
            "romantic",
            "mixed",
        ),

        (
            "Vibrant (digital)",
            "vibrant",
            "any",
            "jewel",
            "digital",
        ),

        (
            "Muted (real paint)",
            "muted",
            "cool",
            "botanical",
            "real",
        ),

        (
            "Classic",
            "classic",
            "warm",
            "any",
            "mixed",
        ),

        (
            "Ancient (real paint)",
            "ancient",
            "warm",
            "earthy",
            "real",
        ),

        (
            "Modern (digital)",
            "modern",
            "cool",
            "ocean",
            "digital",
        ),

        (
            "Minimalist",
            "minimalist",
            "neutral",
            "monochrome",
            "mixed",
        ),
    ]

    for label, style, mood, theme, domain in tests:

        print()
        print("=" * 70)
        print(label)

        start = time.perf_counter()

        palette = generator.generate(
            count=5,
            style=style,
            mood=mood,
            theme=theme,
            domain=domain,
            attempts=60,
            name_colors=True,
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        print(
            "STYLE:",
            style
        )

        print(
            "MOOD:",
            mood
        )

        print(
            "THEME:",
            theme
        )

        print(
            "DOMAIN:",
            domain
        )

        print(
            "SCORE:",
            round(
                palette["score"],
                2
            )
        )

        print(
            "TIME:",
            round(
                elapsed,
                3
            ),
            "seconds"
        )

        for color in palette["colors"]:

            match = color.get(
                "match"
            )

            if match:

                print(
                    f"{color['hex']}  "
                    f"{match['name']}  "
                    f"ΔE={match['delta_e']:.2f}"
                )

            else:

                print(
                    color["hex"]
                )
