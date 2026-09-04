"""
PaletteLab color math, extraction, and utility functions.
Includes comprehensive multi-color-space conversions (RGB, HSL, HSV, CMYK, LAB <-> HEX),
curated color naming database with LAB perceptual nearest-neighbor matching,
WCAG relative luminance and contrast calculations, and string formatters.
"""

import colorsys
import math
import re
from typing import List, Tuple, Sequence

# ============================================================
# HEX EXTRACTION
# ============================================================

HEX_RE = re.compile(
    r"(?<![0-9A-Fa-f])#([0-9A-Fa-f]{6})(?![0-9A-Fa-f])"
)


def normalize_hex(value: str) -> str:
    """Normalize a hex string to standard #RRGGBB uppercase format."""
    clean = value.lstrip("#").strip()
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    return "#" + clean.upper()


def extract_hexes(text: str) -> List[str]:
    """
    Extract valid six-digit HEX colors from arbitrary text.
    Preserves exact order and removes duplicate extracted values.
    """
    found: List[str] = []
    for match in HEX_RE.finditer(text):
        value = normalize_hex(match.group(1))
        if value not in found:
            found.append(value)
    return found


# ============================================================
# FORWARD COLOR CONVERSIONS (HEX -> OTHER)
# ============================================================

def rgb_from_hex(value: str) -> Tuple[int, int, int]:
    """Convert #RRGGBB hex string to (R, G, B) integer tuple (0-255)."""
    val = normalize_hex(value)
    return (
        int(val[1:3], 16),
        int(val[3:5], 16),
        int(val[5:7], 16),
    )


def hsl_from_hex(value: str) -> Tuple[float, float, float]:
    """Convert #RRGGBB to (H: 0-360, S: 0-100, L: 0-100)."""
    r, g, b = rgb_from_hex(value)
    h, l, s = colorsys.rgb_to_hls(
        r / 255.0,
        g / 255.0,
        b / 255.0,
    )
    return (
        h * 360.0,
        s * 100.0,
        l * 100.0,
    )


def hsv_from_hex(value: str) -> Tuple[float, float, float]:
    """Convert #RRGGBB to (H: 0-360, S: 0-100, V: 0-100)."""
    r, g, b = rgb_from_hex(value)
    h, s, v = colorsys.rgb_to_hsv(
        r / 255.0,
        g / 255.0,
        b / 255.0,
    )
    return (
        h * 360.0,
        s * 100.0,
        v * 100.0,
    )


def cmyk_from_hex(value: str) -> Tuple[float, float, float, float]:
    """Convert #RRGGBB to (C: 0-100, M: 0-100, Y: 0-100, K: 0-100)."""
    r, g, b = rgb_from_hex(value)
    rf = r / 255.0
    gf = g / 255.0
    bf = b / 255.0

    k = 1.0 - max(rf, gf, bf)
    if k >= 0.999999:
        return 0.0, 0.0, 0.0, 100.0

    c = (1.0 - rf - k) / (1.0 - k)
    m = (1.0 - gf - k) / (1.0 - k)
    y = (1.0 - bf - k) / (1.0 - k)

    return (
        c * 100.0,
        m * 100.0,
        y * 100.0,
        k * 100.0,
    )


def lab_from_hex(value: str) -> Tuple[float, float, float]:
    """Convert #RRGGBB to CIE L*a*b* values."""
    r, g, b = rgb_from_hex(value)

    def linear(c: float) -> float:
        c /= 255.0
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r_lin = linear(r)
    g_lin = linear(g)
    b_lin = linear(b)

    x = (
        r_lin * 0.4124564
        + g_lin * 0.3575761
        + b_lin * 0.1804375
    ) / 0.95047

    y = (
        r_lin * 0.2126729
        + g_lin * 0.7151522
        + b_lin * 0.0721750
    )

    z = (
        r_lin * 0.0193339
        + g_lin * 0.1191920
        + b_lin * 0.9503041
    ) / 1.08883

    def f(t: float) -> float:
        d = 6.0 / 29.0
        if t > d ** 3:
            return t ** (1.0 / 3.0)
        return (t / (3.0 * d * d)) + (4.0 / 29.0)

    fx = f(x)
    fy = f(y)
    fz = f(z)

    return (
        116.0 * fy - 16.0,
        500.0 * (fx - fy),
        200.0 * (fy - fz),
    )


# ============================================================
# REVERSE COLOR CONVERSIONS (OTHER -> HEX)
# ============================================================

def hex_from_rgb(rgb: Tuple[float, float, float]) -> str:
    """Convert (R, G, B) tuple (0-255) to #RRGGBB hex string."""
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, round(rgb[0]))),
        max(0, min(255, round(rgb[1]))),
        max(0, min(255, round(rgb[2]))),
    )


def hex_from_hsl(h: float, s: float, l: float) -> str:
    """Convert HSL (H: 0-360, S: 0-100, L: 0-100) to #RRGGBB."""
    h_norm = (h % 360.0) / 360.0
    s_norm = max(0.0, min(100.0, s)) / 100.0
    l_norm = max(0.0, min(100.0, l)) / 100.0

    r, g, b = colorsys.hls_to_rgb(h_norm, l_norm, s_norm)
    return hex_from_rgb((r * 255.0, g * 255.0, b * 255.0))


def hex_from_hsv(h: float, s: float, v: float) -> str:
    """Convert HSV (H: 0-360, S: 0-100, V: 0-100) to #RRGGBB."""
    h_norm = (h % 360.0) / 360.0
    s_norm = max(0.0, min(100.0, s)) / 100.0
    v_norm = max(0.0, min(100.0, v)) / 100.0

    r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
    return hex_from_rgb((r * 255.0, g * 255.0, b * 255.0))


def hex_from_cmyk(c: float, m: float, y: float, k: float) -> str:
    """Convert CMYK (0-100%) to #RRGGBB."""
    cf = max(0.0, min(100.0, c)) / 100.0
    mf = max(0.0, min(100.0, m)) / 100.0
    yf = max(0.0, min(100.0, y)) / 100.0
    kf = max(0.0, min(100.0, k)) / 100.0

    r = 255.0 * (1.0 - cf) * (1.0 - kf)
    g = 255.0 * (1.0 - mf) * (1.0 - kf)
    b = 255.0 * (1.0 - yf) * (1.0 - kf)
    return hex_from_rgb((r, g, b))


def hex_from_lab(l: float, a: float, b: float) -> str:
    """Convert CIE L*a*b* (L: 0-100, a: -128..127, b: -128..127) to #RRGGBB."""
    fy = (l + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    d = 6.0 / 29.0

    def f_inv(t: float) -> float:
        if t > d:
            return t ** 3
        return 3.0 * (d ** 2) * (t - 4.0 / 29.0)

    x = 0.95047 * f_inv(fx)
    y = 1.00000 * f_inv(fy)
    z = 1.08883 * f_inv(fz)

    r_lin = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g_lin = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    b_lin = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

    def gamma(c: float) -> float:
        if c <= 0.031308:
            return 12.92 * c
        return 1.055 * (max(0.0, c) ** (1.0 / 2.4)) - 0.055

    r = max(0.0, min(1.0, gamma(r_lin))) * 255.0
    g = max(0.0, min(1.0, gamma(g_lin))) * 255.0
    b = max(0.0, min(1.0, gamma(b_lin))) * 255.0

    return hex_from_rgb((r, g, b))


# ============================================================
# CURATED COLOR NAMING DATABASE & MATCHING
# ============================================================

from functools import lru_cache

_GLOBAL_COLOR_MATCHER = None

@lru_cache(maxsize=8192)
def get_color_name(hex_color: str) -> str:
    """Find the closest human-friendly color name using ColorMatcher (32k+ colors)."""
    global _GLOBAL_COLOR_MATCHER
    if _GLOBAL_COLOR_MATCHER is None:
        from core_logic.generatePalette.color_matcher import ColorMatcher
        _GLOBAL_COLOR_MATCHER = ColorMatcher()

    norm_hex = normalize_hex(hex_color)
    if not norm_hex:
        return "Custom Color"

    # Fast O(1) exact match lookup
    if _GLOBAL_COLOR_MATCHER and norm_hex in _GLOBAL_COLOR_MATCHER.hex_index:
        rec = _GLOBAL_COLOR_MATCHER.hex_index[norm_hex]
        if rec and rec.get("records"):
            return rec["records"][0]["name"]

    try:
        result = _GLOBAL_COLOR_MATCHER.match_hex(norm_hex, top_n=1)
        if result and result.get("match"):
            return result["match"]["name"]
    except Exception:
        pass

    return "Custom Color"


# ============================================================
# CIELCH CONVERSIONS & PERCEPTUAL SHADE ENGINE
# ============================================================

def lab_to_lch(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to CIE L*C*h (Lightness, Chroma, Hue in degrees)."""
    l, a, b = lab
    c = math.sqrt(a * a + b * b)
    h_rad = math.atan2(b, a)
    h_deg = math.degrees(h_rad) % 360.0
    return (l, c, h_deg)

def lch_to_lab(lch: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert CIE L*C*h to CIE L*a*b*."""
    l, c, h_deg = lch
    h_rad = math.radians(h_deg)
    a = c * math.cos(h_rad)
    b = c * math.sin(h_rad)
    return (l, a, b)

def lch_from_hex(hex_str: str) -> Tuple[float, float, float]:
    """Convert #RRGGBB hex string to CIELCH."""
    lab = lab_from_hex(hex_str)
    return lab_to_lch(lab)

def lab_to_rgb_raw(l: float, a: float, b: float) -> Tuple[float, float, float]:
    """Convert LAB to linear/gamma RGB before clamping."""
    fy = (l + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    d = 6.0 / 29.0

    def f_inv(t: float) -> float:
        if t > d:
            return t ** 3
        return 3.0 * (d ** 2) * (t - 4.0 / 29.0)

    x = 0.95047 * f_inv(fx)
    y = 1.00000 * f_inv(fy)
    z = 1.08883 * f_inv(fz)

    r_lin = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g_lin = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    b_lin = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

    def gamma(c: float) -> float:
        if c <= 0.031308:
            return 12.92 * c
        return 1.055 * (max(0.0, c) ** (1.0 / 2.4)) - 0.055

    r = gamma(r_lin) * 255.0
    g = gamma(g_lin) * 255.0
    b = gamma(b_lin) * 255.0
    return (r, g, b)

def hex_from_lch_gamut(l: float, c: float, h: float) -> str:
    """
    Convert CIELCH to standard sRGB Hex with strict Gamut Mapping:
    Keeps mutated L and H locked, and iteratively reduces C (Chroma)
    until (r, g, b) fits perfectly within the 0-255 web gamut.
    """
    cur_c = max(0.0, c)
    step = 0.5
    for _ in range(80):
        lab = lch_to_lab((l, cur_c, h))
        r, g, b = lab_to_rgb_raw(*lab)
        if 0.0 <= r <= 255.0 and 0.0 <= g <= 255.0 and 0.0 <= b <= 255.0:
            return hex_from_rgb((round(r), round(g), round(b)))
        cur_c = max(0.0, cur_c - step)
        if cur_c <= 0:
            break
            
    lab = lch_to_lab((l, 0.0, h))
    r, g, b = lab_to_rgb_raw(*lab)
    return hex_from_rgb((round(max(0, min(255, r))), round(max(0, min(255, g))), round(max(0, min(255, b)))))

def apply_shade(base_hex: str, delta: float) -> str:
    """
    CIELCH Perceptual Shade Engine with strict mathematical boundaries:
    - Delta input: -100 to +100 (or float normalized from -1.0 to 1.0).
    1. Fixed symmetric lightness offset: base_L + (delta * 38.0), clamped to [10.0, 92.0].
    2. Chroma preservation / decay floor.
    3. Micro temperature hue shift: base_H + (delta * 8.0).
    4. Out-of-gamut safe chroma reduction.
    """
    # Normalize delta to -100..+100 scale
    if -1.0 <= delta <= 1.0 and delta != 0:
        delta = delta * 100.0

    if delta == 0.0:
        return normalize_hex(base_hex)

    orig_l, orig_c, orig_h = lch_from_hex(base_hex)
    d = delta / 100.0

    # 1. Symmetric Lightness offset (allows visible steps even on very light or dark base)
    target_l = orig_l + (d * 38.0)
    mutated_l = max(10.0, min(92.0, target_l))

    # 2. Chroma Protection Floor
    is_original_gray = orig_c < 25.0
    original_c_floor = orig_c if is_original_gray else max(25.0, orig_c)

    if is_original_gray:
        mutated_c = orig_c
    else:
        chroma_decay = 1.0 - (abs(d) * 0.12)
        mutated_c = max(20.0, original_c_floor * chroma_decay)

    # 3. Temperature Hue Shift
    mutated_h = (orig_h + (d * 8.0)) % 360.0

    # 4. Out-of-gamut conversion
    return hex_from_lch_gamut(mutated_l, mutated_c, mutated_h)


def relative_luminance(hex_color: str) -> float:
    """Calculate standard WCAG relative luminance (0.0 to 1.0)."""
    r, g, b = rgb_from_hex(hex_color)

    def linear(c: float) -> float:
        c /= 255.0
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * linear(r)
        + 0.7152 * linear(g)
        + 0.0722 * linear(b)
    )


def wcag_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG 2.1 contrast ratio between two hex colors (1.0 to 21.0)."""
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_text(hex_color: str) -> str:
    """
    Per-Swatch Text Color using strict perceptual Lightness L*:
    Text Color = #111111 if L* >= 60.0 else #FFFFFF.
    """
    l_star, _, _ = lch_from_hex(hex_color)
    return "#111111" if l_star >= 60.0 else "#FFFFFF"


def get_adaptive_export_bg(colors: List[str]) -> str:
    """
    Select an elegant neutral background with a strong bias towards light, airy, and calm.
    Defaults to light ivory/pearl tones (#FAF9F6, #F8F9FA, #F5F6F8, #F3F4F6, #EFECE6),
    and selects a soft calm slate (#1E222B, #232730) only when the palette consists mostly
    of pale/white colors that need dark contrast.
    """
    if not colors:
        return "#FAF9F6"

    avg_lum = sum(relative_luminance(c) for c in colors) / len(colors)
    light_count = sum(1 for c in colors if relative_luminance(c) > 0.55)

    # If predominantly pale/light, use soft calm dark slate for readability
    if light_count >= len(colors) * 0.6 or avg_lum > 0.58:
        dark_candidates = ["#1E222B", "#232730", "#252932"]
        return max(dark_candidates, key=lambda bg: min(wcag_contrast_ratio(c, bg) for c in colors))

    # Otherwise, default to airy, calm light ivory/pearl/neutral
    light_candidates = ["#FAF9F6", "#F8F9FA", "#F5F6F8", "#F3F4F6", "#EFECE6"]
    return max(light_candidates, key=lambda bg: min(wcag_contrast_ratio(c, bg) for c in colors))


def get_light_tint_rgb(hex_color: str, target_lightness: float = 90.5, max_sat: float = 30.0) -> Tuple[int, int, int]:
    """
    Convert any palette hex color to a refined, soft light tint.
    Keeps original hue, tempers saturation (12-30%), and sets lightness to luxury pastel levels (88-93%).
    """
    h, s, l = hsl_from_hex(hex_color)
    adj_s = min(max_sat, max(12.0, s * 0.45))
    adj_l = target_lightness
    r, g, b = colorsys.hls_to_rgb(h / 360.0, adj_l / 100.0, adj_s / 100.0)
    return (
        max(0, min(255, int(round(r * 255.0)))),
        max(0, min(255, int(round(g * 255.0)))),
        max(0, min(255, int(round(b * 255.0)))),
    )


def get_three_part_bg_tints(colors: Sequence[str]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Select 3 distinct colors from the extracted palette and return 3 soft light pastel tints
    for the diagonal 3-stop ultra-thin luxury background gradient.
    """
    if not colors:
        c1 = get_light_tint_rgb("#F5F3EF", 92.0, 10.0)
        c2 = get_light_tint_rgb("#EAE6DF", 90.0, 10.0)
        c3 = get_light_tint_rgb("#DFD9CF", 88.0, 10.0)
        return c1, c2, c3

    n = len(colors)
    if n == 1:
        c1 = get_light_tint_rgb(colors[0], 92.5)
        c2 = get_light_tint_rgb(colors[0], 89.5)
        c3 = get_light_tint_rgb(colors[0], 87.0)
    elif n == 2:
        c1 = get_light_tint_rgb(colors[0], 92.0)
        c2 = get_light_tint_rgb(colors[1], 89.5)
        c3 = get_light_tint_rgb(colors[0], 87.0)
    else:
        idx1 = 0
        idx2 = n // 2
        idx3 = n - 1
        c1 = get_light_tint_rgb(colors[idx1], 92.5)
        c2 = get_light_tint_rgb(colors[idx2], 89.5)
        c3 = get_light_tint_rgb(colors[idx3], 87.0)

    return c1, c2, c3


# ============================================================
# STRING FORMATTERS & MULTI-LABEL RESOLVER
# ============================================================

def format_rgb(value: str) -> str:
    r, g, b = rgb_from_hex(value)
    return f"RGB({r}, {g}, {b})"


def format_hsl(value: str) -> str:
    h, s, l = hsl_from_hex(value)
    return f"HSL({h:.0f}, {s:.0f}%, {l:.0f}%)"


def format_hsv(value: str) -> str:
    h, s, v = hsv_from_hex(value)
    return f"HSV({h:.0f}, {s:.0f}%, {v:.0f}%)"


def format_cmyk(value: str) -> str:
    c, m, y, k = cmyk_from_hex(value)
    return f"CMYK({c:.0f}, {m:.0f}, {y:.0f}, {k:.0f})"


def format_lab(value: str) -> str:
    l, a, b = lab_from_hex(value)
    return f"LAB({l:.1f}, {a:.1f}, {b:.1f})"


def get_formatted_color(hex_color: str, fmt_name: str) -> str:
    """Resolve single label formatted value."""
    fmt = fmt_name.strip().upper()
    if fmt in ("NAME", "COLOR NAME", "COLOUR NAME"):
        return get_color_name(hex_color)
    elif fmt == "HEX":
        return normalize_hex(hex_color)
    elif fmt == "RGB":
        return format_rgb(hex_color)
    elif fmt == "HSL":
        return format_hsl(hex_color)
    elif fmt == "HSV":
        return format_hsv(hex_color)
    elif fmt == "CMYK":
        return format_cmyk(hex_color)
    elif fmt == "LAB":
        return format_lab(hex_color)
    return normalize_hex(hex_color)


def get_color_labels(hex_color: str, formats: Sequence[str]) -> List[str]:
    """
    Return up to 2 string label lines based on active selected formats list.
    If no formats selected, returns empty list [].
    """
    if not formats:
        return []

    resolved: List[str] = []
    for fmt in formats[:2]:
        val = get_formatted_color(hex_color, fmt)
        if val not in resolved:
            resolved.append(val)

    return resolved

