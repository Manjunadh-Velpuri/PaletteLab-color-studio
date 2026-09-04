"""
PaletteLab visual palette rendering engine.
Supports 9 distinct high-resolution layouts in Pillow and SVG:
1. Cards (Controlled asymmetrical hero composition with hairline borders & direct adaptive labels)
2. Strips (Full-bleed horizontal columns with harmonic hero band & direct horizontal stacked labels)
3. Poster (Artistic portrait card with harmonic hero band & direct adaptive labels)
4. Design System (Design token swatch specimen grid with hero card & hairline borders)
5. Circles (Controlled asymmetrical composition with hero circle & direct adaptive labels)
6. Editorial (Sharp asymmetrical editorial grid blocks with hairline borders)
7. Honeycomb (Flat-topped tessellation with crisp 3px mortar gaps & direct adaptive labels)
8. Swatch Grid (Continuous uninterrupted cards with direct adaptive labels)
9. Ribbon (Specification sheet with vertical rounded bars & large horizontal stacked labels)

Features:
- Per-swatch adaptive text contrast using relative luminance (pure text on swatch, no background boxes)
- 6-10% white hairline borders on every swatch shape regardless of background
- Strict typographic hierarchy: Inter for color names (100% opacity) + JetBrains Mono for codes (75% opacity)
- Controlled asymmetry across grid, circle, and card layouts
- Soft elevated drop shadows under every swatch shape
- Graceful scaling for palettes from 3 colors to 30 colors
"""

import math
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core_logic.core.color_utils import (
    contrast_text, relative_luminance, rgb_from_hex, hex_from_rgb,
    hsl_from_hex, get_color_labels, get_adaptive_export_bg
)


@lru_cache(maxsize=512)
def get_title_font(size: int) -> ImageFont.ImageFont:
    """Resolve League Spartan font for titles and headers."""
    size = max(12, int(size))
    fonts_dir = Path("static/fonts")
    candidates = [
        fonts_dir / "LeagueSpartan-Bold.ttf",
        fonts_dir / "LeagueSpartan.ttf",
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    return ImageFont.load_default()


@lru_cache(maxsize=512)
def get_display_font(size: int, weight: str = "Medium") -> ImageFont.ImageFont:
    """
    Resolve bundled Inter font family for color names and body text.
    Guarantees resolving Inter-Medium, Inter-SemiBold, Inter-Bold, or Inter-Regular.
    """
    size = max(8, int(size))
    fonts_dir = Path("static/fonts")

    if weight == "Bold":
        fpaths = [fonts_dir / "Inter-Bold.ttf", fonts_dir / "Inter-SemiBold.ttf"]
    elif weight == "SemiBold":
        fpaths = [fonts_dir / "Inter-SemiBold.ttf", fonts_dir / "Inter-Medium.ttf"]
    elif weight == "Regular":
        fpaths = [fonts_dir / "Inter-Regular.ttf", fonts_dir / "Inter-Medium.ttf"]
    else:
        fpaths = [fonts_dir / "Inter-Medium.ttf", fonts_dir / "Inter-Regular.ttf"]

    for fp in fpaths:
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except Exception:
                pass

    pass

    return ImageFont.load_default()


@lru_cache(maxsize=512)
def get_mono_font(size: int) -> ImageFont.ImageFont:
    """
    Resolve bundled JetBrains Mono font for hex values, model conversions, and codes.
    """
    size = max(7, int(size))
    fonts_dir = Path("static/fonts")
    mono_path = fonts_dir / "JetBrainsMono-Medium.ttf"

    if mono_path.exists():
        try:
            return ImageFont.truetype(str(mono_path), size)
        except Exception:
            pass

    pass

    return ImageFont.load_default()


_scratch_img = Image.new("L", (1, 1))
_scratch_draw = ImageDraw.Draw(_scratch_img)


@lru_cache(maxsize=2048)
def fit_font_size(text: str, max_w: float, max_sz: int = 24, min_sz: int = 9,
                  is_mono: bool = False) -> Tuple[ImageFont.ImageFont, int]:
    """Fit font size with memoization so text does not exceed max_w."""
    for sz in range(max_sz, min_sz - 1, -1):
        f = get_mono_font(sz) if is_mono else get_display_font(sz, "Medium")
        bb = _scratch_draw.textbbox((0, 0), text, font=f)
        if (bb[2] - bb[0]) <= max_w:
            return f, sz
    f_min = get_mono_font(min_sz) if is_mono else get_display_font(min_sz, "Medium")
    return f_min, min_sz


def normalize_layout(layout: str) -> str:
    alias_map = {
        # Current Clean 1-2 Word Layout Names (8 Canonical Layouts)
        "pillars": "Pillars",
        "orbs": "Orbs",
        "ribbons": "Ribbons",
        "chips": "Chips",
        "collage": "Collage",
        "honeycomb": "Honeycomb",
        "canvas": "Canvas",
        "blocks": "Blocks",

        # Aliases for 100% Backward Compatibility
        "tiles": "Blocks",
        "cards": "Blocks",
        "modular cards": "Blocks",
        "ribbon": "Pillars",
        "color columns": "Pillars",
        "vertical columns": "Pillars",
        "circles": "Orbs",
        "color discs": "Orbs",
        "strips": "Ribbons",
        "color strips": "Ribbons",
        "linear bands": "Ribbons",
        "design system": "Chips",
        "design tokens": "Chips",
        "editorial": "Collage",
        "editorial mosaic": "Collage",
        "hex matrix": "Honeycomb",
        "poster": "Canvas",
        "studio poster": "Canvas",
        "swatch grid": "Blocks",
    }
    return alias_map.get(str(layout).lower().strip(), "Chips")


class PaletteRenderer:
    def __init__(self, colors: Sequence[str], layout: str = "Chips",
                 label_formats: Optional[Sequence[str]] = None):
        self.colors = list(colors)
        self.layout = normalize_layout(layout)
        self.label_formats = list(label_formats) if label_formats is not None else ["Color Name"]

    @staticmethod
    def get_hero_index(colors: Sequence[str]) -> int:
        """Find the index of the hero color (highest saturation/chroma)."""
        if not colors:
            return 0
        saturations = [hsl_from_hex(c)[1] for c in colors]
        max_s = max(saturations)
        if max_s > 25.0:
            return saturations.index(max_s)
        return 0

    @staticmethod
    def grid(count: int, width: float, height: float, preferred_ratio: float = 1.35) -> Tuple[int, int]:
        if count <= 0:
            return 1, 1

        best = None
        for columns in range(1, count + 1):
            rows = math.ceil(count / columns)
            cell_w = width / columns
            cell_h = height / rows

            ratio = cell_w / max(cell_h, 1.0)
            ratio_penalty = abs(math.log(max(ratio, 0.01) / preferred_ratio))
            empty = columns * rows - count
            score = ratio_penalty + empty * 0.08

            if best is None or score < best[0]:
                best = (score, columns, rows)

        return best[1], best[2]

    # --------------------------------------------------------
    # Direct Adaptive Label Drawing (No background boxes/pills)
    # --------------------------------------------------------
    def draw_direct_labels(self, draw: ImageDraw.ImageDraw,
                           cx: float, cy: float, lines: List[str], swatch_hex: str,
                           max_w: Optional[float] = None, font_size: int = 18) -> None:
        """
        Draw adaptive label text directly on the swatch color (NO backing box/pill):
        - Inter-Medium for Color Name (100% opacity)
        - JetBrains Mono for Code/Hex (75% opacity)
        - Dark text on light swatches, white text on dark swatches (L* >= 60.0 rule)
        """
        if not lines:
            return

        txt_hex = contrast_text(swatch_hex)
        is_light = (txt_hex == "#111111")

        # Pure adaptive text colors
        col_name = (17, 17, 17, 255) if is_light else (255, 255, 255, 255)
        col_code = (45, 45, 45, 205) if is_light else (225, 225, 225, 200)

        limit_w = max_w if max_w else 200.0

        if len(lines) == 1:
            f_name, _ = fit_font_size(lines[0], limit_w, max_sz=font_size, min_sz=8, is_mono=False)
            bbox = draw.textbbox((0, 0), lines[0], font=f_name)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = cx - tw / 2.0 - bbox[0]
            ty = cy - th / 2.0 - bbox[1]
            draw.text((round(tx), round(ty)), lines[0], fill=col_name, font=f_name)
        else:
            f_name, actual_sz = fit_font_size(lines[0], limit_w, max_sz=font_size, min_sz=8, is_mono=False)
            mono_max_sz = max(7, int(actual_sz * 0.84))
            f_mono, _ = fit_font_size(lines[1], limit_w, max_sz=mono_max_sz, min_sz=7, is_mono=True)

            bbox1 = draw.textbbox((0, 0), lines[0], font=f_name)
            tw1, th1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
            bbox2 = draw.textbbox((0, 0), lines[1], font=f_mono)
            tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

            spacing = max(2, int(actual_sz * 0.20))
            total_th = th1 + spacing + th2

            ty_top = cy - total_th / 2.0

            # Line 1: Name
            tx1 = cx - tw1 / 2.0 - bbox1[0]
            ty1 = ty_top - bbox1[1]
            draw.text((round(tx1), round(ty1)), lines[0], fill=col_name, font=f_name)

            # Line 2: Code
            tx2 = cx - tw2 / 2.0 - bbox2[0]
            ty2 = ty_top + th1 + spacing - bbox2[1]
            draw.text((round(tx2), round(ty2)), lines[1], fill=col_code, font=f_mono)

    def draw_vertical_direct_labels(self, image: Image.Image,
                                    cx: float, cy: float, lines: List[str], swatch_hex: str,
                                    max_h: Optional[float] = None, font_size: int = 18) -> None:
        """
        Draw adaptive label text rotated 90 degrees vertically along the column/strip:
        - Reads bottom to top (rotated 90° CCW / 270° CW)
        - Dark text on light swatches, white text on dark swatches (L* >= 60.0 rule)
        - Eliminates text overlap when swatches are narrow vertical pillars or ribbons
        """
        if not lines:
            return

        txt_hex = contrast_text(swatch_hex)
        is_light = (txt_hex == "#111111")

        col_name = (17, 17, 17, 255) if is_light else (255, 255, 255, 255)
        col_code = (45, 45, 45, 205) if is_light else (225, 225, 225, 200)

        limit_h = max_h if max_h else 300.0

        if len(lines) == 1:
            f_name, actual_sz = fit_font_size(lines[0], limit_h, max_sz=font_size, min_sz=8, is_mono=False)
            bbox = _scratch_draw.textbbox((0, 0), lines[0], font=f_name)
            tw = max(1, bbox[2] - bbox[0] + 6)
            th = max(1, bbox[3] - bbox[1] + 6)

            txt_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(txt_img)
            t_draw.text((-bbox[0] + 3, -bbox[1] + 3), lines[0], fill=col_name, font=f_name)

            rotated = txt_img.rotate(90, expand=True, resample=Image.BICUBIC)
            rw, rh = rotated.size
            px = int(cx - rw / 2.0)
            py = int(cy - rh / 2.0)
            image.alpha_composite(rotated, (px, py))
        else:
            f_name, actual_sz = fit_font_size(lines[0], limit_h, max_sz=font_size, min_sz=8, is_mono=False)
            mono_max_sz = max(7, int(actual_sz * 0.84))
            f_mono, _ = fit_font_size(lines[1], limit_h, max_sz=mono_max_sz, min_sz=7, is_mono=True)

            bbox1 = _scratch_draw.textbbox((0, 0), lines[0], font=f_name)
            tw1, th1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
            bbox2 = _scratch_draw.textbbox((0, 0), lines[1], font=f_mono)
            tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

            spacing = max(2, int(actual_sz * 0.22))
            total_w = max(tw1, tw2) + 8
            total_h = th1 + spacing + th2 + 8

            txt_img = Image.new("RGBA", (int(total_w), int(total_h)), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(txt_img)

            tx1 = (total_w - tw1) / 2.0 - bbox1[0]
            ty1 = 4 - bbox1[1]
            t_draw.text((round(tx1), round(ty1)), lines[0], fill=col_name, font=f_name)

            tx2 = (total_w - tw2) / 2.0 - bbox2[0]
            ty2 = 4 + th1 + spacing - bbox2[1]
            t_draw.text((round(tx2), round(ty2)), lines[1], fill=col_code, font=f_mono)

            rotated = txt_img.rotate(90, expand=True, resample=Image.BICUBIC)
            rw, rh = rotated.size
            px = int(cx - rw / 2.0)
            py = int(cy - rh / 2.0)
            image.alpha_composite(rotated, (px, py))

    # --------------------------------------------------------
    # Main Render
    # --------------------------------------------------------
    def render(self, size: Tuple[int, int], background: str, transparent: bool = False) -> Image.Image:
        width, height = size
        image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else background)
        draw = ImageDraw.Draw(image)

        if not self.colors:
            return image if transparent else image.convert("RGB")

        norm = self.layout
        if norm == "Ribbons":
            self.draw_strips(image, draw, width, height)
        elif norm == "Canvas":
            self.draw_poster(image, draw, width, height, transparent)
        elif norm == "Chips":
            self.draw_chips(image, draw, width, height)
        elif norm == "Orbs":
            self.draw_circles(image, draw, width, height)
        elif norm == "Collage":
            self.draw_collage(image, draw, width, height)
        elif norm == "Honeycomb":
            self.draw_honeycomb(image, draw, width, height)
        elif norm == "Blocks":
            self.draw_blocks(image, draw, width, height)
        elif norm == "Pillars":
            self.draw_ribbon(image, draw, width, height)
        else:
            self.draw_chips(image, draw, width, height)

        if not transparent and image.mode == "RGBA":
            return image.convert("RGB")
        return image

    # ========================================================
    # 2. BLOCKS LAYOUT (Rigid Symmetrical Checkerboard Edge-to-Edge Grid)
    # ========================================================
    def compute_blocks_geometry(self, width: float, height: float) -> List[Tuple[float, float, float, float, bool]]:
        """
        Rigid, symmetrical grid of perfectly square/rectangular color swatches.
        Sits flush edge-to-edge with zero gaps (gap=0, radius=0).
        """
        count = len(self.colors)
        if count <= 0:
            return []

        if count == 1:
            return [(0.0, 0.0, float(width), float(height), True)]
        elif count == 2:
            cols, rows = 2, 1
        elif count == 3:
            cols, rows = 3, 1
        elif count == 4:
            cols, rows = 2, 2
        elif count <= 6:
            cols, rows = 3, 2
        elif count <= 8:
            cols, rows = 4, 2
        elif count == 9:
            cols, rows = 3, 3
        elif count <= 12:
            cols, rows = 4, 3
        elif count <= 16:
            cols, rows = 4, 4
        elif count <= 20:
            cols, rows = 5, 4
        elif count <= 25:
            cols, rows = 5, 5
        else:
            cols = math.ceil(math.sqrt(count * 1.25))
            rows = math.ceil(count / cols)

        step_y = height / float(rows)
        full_rows = count // cols
        rem = count % cols

        boxes = []
        for i in range(count):
            r = i // cols
            c = i % cols

            if r == full_rows and rem > 0:
                # Remainder items share the bottom row evenly flush edge-to-edge
                rem_step_x = width / float(rem)
                x0 = c * rem_step_x
                x1 = (c + 1) * rem_step_x if c == rem - 1 else (c + 1) * rem_step_x
                y0 = r * step_y
                y1 = height
            else:
                step_x = width / float(cols)
                x0 = c * step_x
                x1 = (c + 1) * step_x
                y0 = r * step_y
                y1 = (r + 1) * step_y

            boxes.append((x0, y0, x1, y1, False))

        return boxes

    def draw_blocks(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        boxes = self.compute_blocks_geometry(width, height)
        if not boxes:
            return

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for index, (color, (x0, y0, x1, y1, _)) in enumerate(zip(self.colors, boxes)):
            s_draw.rectangle(
                [round(x0), round(y0), round(x1), round(y1)],
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )

        # Outer border
        s_draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255, 45), width=1)

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 5), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        image.alpha_composite(shapes_layer)

        for index, (color, (x0, y0, x1, y1, _)) in enumerate(zip(self.colors, boxes)):
            lines = get_color_labels(color, self.label_formats)
            if lines:
                cw = x1 - x0
                ch = y1 - y0
                font_sz = min(24, max(11, int(min(cw, ch) * 0.14)))
                if len(self.colors) >= 20:
                    font_sz = min(13, max(8, int(min(cw, ch) * 0.18)))

                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                self.draw_direct_labels(draw, cx, cy, lines, color,
                                        max_w=cw * 0.88, font_size=font_sz)

    draw_swatch_grid = draw_blocks

    # ========================================================
    # 3. CHIPS LAYOUT (Hardware Store Physical Paint Sample Chips)
    # ========================================================
    def compute_chips_geometry(self, width: float, height: float) -> List[Tuple[float, float, float, float]]:
        """
        Isolated portrait-oriented paint sample cards arranged to maximize canvas area utilization.
        Dynamically finds optimal grid dimensions (cols, rows) for any canvas aspect ratio.
        """
        count = len(self.colors)
        if count <= 0:
            return []

        pad_x = width * 0.05
        pad_y = height * 0.06
        aw = width - pad_x * 2
        ah = height - pad_y * 2

        if count == 1:
            cw = min(aw * 0.45, ah * 0.50)
            ch = cw * 1.40
            x0 = (width - cw) / 2.0
            y0 = (height - ch) / 2.0
            return [(x0, y0, x0 + cw, y0 + ch)]

        best_score = -1.0
        best_cfg = None

        target_aspect = 0.72  # width / height ratio of portrait paint chip
        canvas_aspect = max(0.1, width / max(1.0, height))

        for cols in range(1, count + 1):
            rows = math.ceil(count / cols)
            gap_x = max(14.0, aw * 0.025)
            gap_y = max(16.0, ah * 0.035)

            slot_w = (aw - gap_x * (cols - 1)) / cols
            slot_h = (ah - gap_y * (rows - 1)) / rows
            if slot_w <= 0 or slot_h <= 0:
                continue

            card_w = min(slot_w, slot_h * target_aspect)
            card_h = card_w / target_aspect

            total_card_area = count * card_w * card_h
            grid_w = cols * card_w + (cols - 1) * gap_x
            grid_h = rows * card_h + (rows - 1) * gap_y

            empty_slots = (cols * rows) - count
            empty_penalty = 1.0 - (empty_slots / (cols * rows)) * 0.22

            grid_aspect = grid_w / max(1.0, grid_h)
            aspect_match = 1.0 - min(0.5, abs(math.log(max(0.1, grid_aspect / canvas_aspect))))

            score = total_card_area * empty_penalty * (1.0 + 0.3 * aspect_match)
            if score > best_score:
                best_score = score
                best_cfg = (cols, rows, card_w, card_h, gap_x, gap_y)

        if not best_cfg:
            cols = math.ceil(math.sqrt(count))
            rows = math.ceil(count / cols)
            card_w = aw / cols
            card_h = ah / rows
            gap_x, gap_y = 6.0, 8.0
        else:
            cols, rows, card_w, card_h, gap_x, gap_y = best_cfg

        positions = []
        full_rows = count // cols
        rem = count % cols

        total_grid_h = rows * card_h + (rows - 1) * gap_y
        grid_start_y = pad_y + (ah - total_grid_h) / 2.0

        for i in range(count):
            r = i // cols
            c = i % cols

            if r == full_rows and rem > 0:
                row_w = rem * card_w + (rem - 1) * gap_x
                row_start_x = pad_x + (aw - row_w) / 2.0
                cx = row_start_x + c * (card_w + gap_x) + card_w / 2.0
            else:
                row_w = cols * card_w + (cols - 1) * gap_x
                row_start_x = pad_x + (aw - row_w) / 2.0
                cx = row_start_x + c * (card_w + gap_x) + card_w / 2.0

            cy = grid_start_y + r * (card_h + gap_y) + card_h / 2.0
            positions.append((cx - card_w / 2.0, cy - card_h / 2.0, cx + card_w / 2.0, cy + card_h / 2.0))

        return positions

    def draw_chips(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        boxes = self.compute_chips_geometry(width, height)
        if not boxes:
            return

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
            cw = x1 - x0
            ch = y1 - y0
            r_card = min(14, max(4, int(cw * 0.07)))
            y_split = y0 + ch * 0.72

            # 1. Base Stark White Card Body
            s_draw.rounded_rectangle(
                [round(x0), round(y0), round(x1), round(y1)],
                radius=r_card,
                fill=(255, 255, 255, 255),
                outline=(220, 222, 228, 240),
                width=1
            )

            # 2. Upper Solid Swatch Color (with rounded top corners)
            top_swatch = Image.new("RGBA", (round(cw), round(ch * 0.72)), (0, 0, 0, 0))
            ts_draw = ImageDraw.Draw(top_swatch)
            ts_draw.rounded_rectangle(
                [0, 0, round(cw), round(ch * 0.72) + r_card],
                radius=r_card,
                fill=color
            )
            # Paste top swatch onto card
            shapes_layer.paste(top_swatch, (round(x0), round(y0)), top_swatch)

            # 3. Subtle Hairline Divider between Swatch and White Label Space
            s_draw.line([(round(x0), round(y_split)), (round(x1), round(y_split))],
                        fill=(220, 222, 228, 255), width=1)

        # Drop shadow under cards
        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 70))
        shadow.paste(shadow_black, (0, 6), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
        image.alpha_composite(shapes_layer)

        # 4. Clean Dark Typography in Bottom White Section
        for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
            cw = x1 - x0
            ch = y1 - y0
            y_split = y0 + ch * 0.72
            white_h = y1 - y_split

            lines = get_color_labels(color, self.label_formats)
            if lines:
                cx = (x0 + x1) / 2.0
                limit_w = cw * 0.90

                col_name = (24, 24, 27, 255)
                col_code = (82, 82, 91, 230)

                font_sz = min(22, max(8, int(white_h * 0.34)))

                if len(lines) == 1:
                    f_name, _ = fit_font_size(lines[0], limit_w, max_sz=font_sz, min_sz=7, is_mono=False)
                    bbox = draw.textbbox((0, 0), lines[0], font=f_name)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    tx = cx - tw / 2.0 - bbox[0]
                    ty = y_split + white_h / 2.0 - th / 2.0 - bbox[1]
                    draw.text((round(tx), round(ty)), lines[0], fill=col_name, font=f_name)
                else:
                    f_name, actual_sz = fit_font_size(lines[0], limit_w, max_sz=font_sz, min_sz=7, is_mono=False)
                    mono_max_sz = max(6, int(actual_sz * 0.84))
                    f_mono, _ = fit_font_size(lines[1], limit_w, max_sz=mono_max_sz, min_sz=6, is_mono=True)

                    bbox1 = draw.textbbox((0, 0), lines[0], font=f_name)
                    tw1, th1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
                    bbox2 = draw.textbbox((0, 0), lines[1], font=f_mono)
                    tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

                    spacing = max(2, int(actual_sz * 0.18))
                    total_th = th1 + spacing + th2
                    ty_top = y_split + (white_h - total_th) / 2.0

                    tx1 = cx - tw1 / 2.0 - bbox1[0]
                    ty1 = ty_top - bbox1[1]
                    draw.text((round(tx1), round(ty1)), lines[0], fill=col_name, font=f_name)

                    tx2 = cx - tw2 / 2.0 - bbox2[0]
                    ty2 = ty_top + th1 + spacing - bbox2[1]
                    draw.text((round(tx2), round(ty2)), lines[1], fill=col_code, font=f_mono)

    draw_design_system = draw_chips

    # ========================================================
    # 4. COLLAGE LAYOUT (Editorial Uneven Interlocking Mosaic Grid)
    # ========================================================
    def compute_collage_geometry(self, width: float, height: float) -> List[Tuple[float, float, float, float]]:
        """
        Editorial magazine mosaic matching the exact reference image!
        Interlocking uneven proportioned rows with flush edges and bottom-right typography.
        """
        count = len(self.colors)
        if count <= 0:
            return []

        if count == 1:
            return [(0.0, 0.0, float(width), float(height))]
        elif count == 2:
            h1 = height * 0.54
            return [
                (0.0, 0.0, float(width), h1),
                (0.0, h1, float(width), float(height)),
            ]
        elif count == 3:
            h1 = height * 0.46
            w_left = width * 0.38
            return [
                (0.0, 0.0, float(width), h1),
                (0.0, h1, w_left, float(height)),
                (w_left, h1, float(width), float(height)),
            ]
        elif count == 4:
            h1 = height * 0.48
            w1 = width * 0.42
            w2 = width * 0.68
            return [
                (0.0, 0.0, w1, h1),
                (w1, 0.0, float(width), h1),
                (0.0, h1, w2, float(height)),
                (w2, h1, float(width), float(height)),
            ]
        elif count == 5:
            h1 = height * 0.46
            w1 = width * 0.56
            w_r1 = width * 0.32
            w_r2 = width * 0.70
            return [
                (0.0, 0.0, w1, h1),
                (w1, 0.0, float(width), h1),
                (0.0, h1, w_r1, float(height)),
                (w_r1, h1, w_r2, float(height)),
                (w_r2, h1, float(width), float(height)),
            ]
        elif count == 6:
            # Exact 100% Match to the Reference Specimen Image!
            # Row 1: Left 45%, Right 55%. Height 36%
            # Row 2: Left 30%, Right 70%. Height 28%
            # Row 3: Left 74%, Right 26%. Height 36%
            h1 = height * 0.36
            h2 = height * 0.64
            w1 = width * 0.45
            w2 = width * 0.30
            w3 = width * 0.74
            return [
                (0.0, 0.0, w1, h1),
                (w1, 0.0, float(width), h1),
                (0.0, h1, w2, h2),
                (w2, h1, float(width), h2),
                (0.0, h2, w3, float(height)),
                (w3, h2, float(width), float(height)),
            ]
        elif count == 7:
            h1 = height * 0.34
            h2 = height * 0.66
            w1 = width * 0.46
            w2 = width * 0.34
            w_b1 = width * 0.30
            w_b2 = width * 0.72
            return [
                (0.0, 0.0, w1, h1),
                (w1, 0.0, float(width), h1),
                (0.0, h1, w2, h2),
                (w2, h1, float(width), h2),
                (0.0, h2, w_b1, float(height)),
                (w_b1, h2, w_b2, float(height)),
                (w_b2, h2, float(width), float(height)),
            ]
        elif count == 8:
            h1 = height * 0.30
            h2 = height * 0.66
            w_t1 = width * 0.30
            w_t2 = width * 0.68
            w_m1 = width * 0.64
            w_b1 = width * 0.28
            w_b2 = width * 0.72
            return [
                (0.0, 0.0, w_t1, h1),
                (w_t1, 0.0, w_t2, h1),
                (w_t2, 0.0, float(width), h1),
                (0.0, h1, w_m1, h2),
                (w_m1, h1, float(width), h2),
                (0.0, h2, w_b1, float(height)),
                (w_b1, h2, w_b2, float(height)),
                (w_b2, h2, float(width), float(height)),
            ]
        else:
            # Multi-row staggered procedural mosaic
            rows = math.ceil(count / 3.0)
            step_y = height / float(rows)
            boxes = []
            cur_idx = 0
            splits_pool = [
                [0.45, 0.55],
                [0.30, 0.70],
                [0.74, 0.26],
                [0.32, 0.38, 0.30],
                [0.55, 0.45],
            ]
            for r in range(rows):
                items_in_row = min(3, count - cur_idx)
                if items_in_row <= 0:
                    break
                y0 = r * step_y
                y1 = float(height) if r == rows - 1 else (r + 1) * step_y

                if items_in_row == 1:
                    boxes.append((0.0, y0, float(width), y1))
                    cur_idx += 1
                elif items_in_row == 2:
                    ratio = splits_pool[r % len(splits_pool)][0]
                    split_x = width * ratio
                    boxes.append((0.0, y0, split_x, y1))
                    boxes.append((split_x, y0, float(width), y1))
                    cur_idx += 2
                else:
                    sp = splits_pool[3] if len(splits_pool) > 3 else [0.33, 0.34, 0.33]
                    x_a = width * sp[0]
                    x_b = width * (sp[0] + sp[1])
                    boxes.append((0.0, y0, x_a, y1))
                    boxes.append((x_a, y0, x_b, y1))
                    boxes.append((x_b, y0, float(width), y1))
                    cur_idx += 3

            return boxes

    def draw_collage(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        boxes = self.compute_collage_geometry(width, height)
        if not boxes:
            return

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
            s_draw.rectangle(
                [round(x0), round(y0), round(x1), round(y1)],
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )

        # Outer border
        s_draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255, 45), width=1)

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 5), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        image.alpha_composite(shapes_layer)

        # Editorial Minimalist Typography in Bottom-Right of each block
        margin_x = max(12, int(width * 0.016))
        margin_y = max(8, int(height * 0.012))

        for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
            lines = get_color_labels(color, self.label_formats)
            if lines:
                cw = x1 - x0
                ch = y1 - y0
                txt_hex = contrast_text(color)
                is_light = (txt_hex == "#111111")

                col_text = (17, 17, 17, 255) if is_light else (255, 255, 255, 255)
                font_sz = min(20, max(9, int(min(cw, ch) * 0.12)))

                f_mono, _ = fit_font_size(lines[-1], cw * 0.80, max_sz=font_sz, min_sz=7, is_mono=True)
                bbox = draw.textbbox((0, 0), lines[-1], font=f_mono)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                tx = x1 - margin_x - tw - bbox[0]
                ty = y1 - margin_y - th - bbox[1]
                draw.text((round(tx), round(ty)), lines[-1], fill=col_text, font=f_mono)

    draw_editorial = draw_collage

    # ========================================================
    # 5. ORBS LAYOUT (Prominent Isolated Circular Matrix)
    # ========================================================
    def circle_asymmetric_geometry(self, width: float, height: float) -> List[Tuple[float, float, float, bool]]:
        """
        Tight circular radial formation with a prominent center orb.
        """
        count = len(self.colors)
        if count <= 0:
            return []

        cx_mid = width / 2.0
        cy_mid = height / 2.0
        max_dim = min(width, height)

        if count == 1:
            return [(cx_mid, cy_mid, max_dim * 0.38, True)]
        elif count == 2:
            r = max_dim * 0.24
            dist = r * 1.05
            return [
                (cx_mid - dist, cy_mid, r, False),
                (cx_mid + dist, cy_mid, r, False),
            ]
        elif count == 3:
            # Triangle formation around center
            r = max_dim * 0.22
            orbit_r = r * 1.15
            positions = []
            for i in range(3):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / 3.0)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r, False))
            return positions
        elif count == 4:
            # 1 center orb + 3 orbiting orbs
            r_center = max_dim * 0.21
            r_orbit = max_dim * 0.20
            orbit_r = max_dim * 0.28
            positions = [(cx_mid, cy_mid, r_center, True)]
            for i in range(3):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / 3.0)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r_orbit, False))
            return positions
        elif count == 5:
            # 1 center orb + 4 cardinal/diagonal orbiting orbs
            r_center = max_dim * 0.20
            r_orbit = max_dim * 0.18
            orbit_r = max_dim * 0.30
            positions = [(cx_mid, cy_mid, r_center, True)]
            for i in range(4):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / 4.0)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r_orbit, False))
            return positions
        elif count == 6:
            # 1 center orb + 5 orbiting orbs
            r_center = max_dim * 0.19
            r_orbit = max_dim * 0.165
            orbit_r = max_dim * 0.31
            positions = [(cx_mid, cy_mid, r_center, True)]
            for i in range(5):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / 5.0)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r_orbit, False))
            return positions
        elif count == 7:
            # 1 center orb + 6 orbiting orbs (flower formation)
            r = max_dim * 0.16
            orbit_r = r * 2.02
            positions = [(cx_mid, cy_mid, r, True)]
            for i in range(6):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / 6.0)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r, False))
            return positions
        elif count <= 10:
            # 1 center orb + (count - 1) orbiting orbs
            k = count - 1
            r_center = max_dim * 0.17
            r_orbit = max_dim * (0.15 - (count - 7) * 0.01)
            orbit_r = max_dim * 0.33
            positions = [(cx_mid, cy_mid, r_center, True)]
            for i in range(k):
                angle = -math.pi / 2.0 + i * (2.0 * math.pi / k)
                cx = cx_mid + orbit_r * math.cos(angle)
                cy = cy_mid + orbit_r * math.sin(angle)
                positions.append((cx, cy, r_orbit, False))
            return positions
        else:
            # Grid arrangement for large counts
            pad_x = width * 0.04
            pad_y = height * 0.04
            aw = width - pad_x * 2
            ah = height - pad_y * 2
            cols = math.ceil(math.sqrt(count * 1.1))
            rows = math.ceil(count / cols)
            step_x = aw / cols
            step_y = ah / rows
            r = min(step_x * 0.46, step_y * 0.46)
            positions = []
            full_rows = count // cols
            rem = count % cols
            for i in range(count):
                row = i // cols
                col = i % cols
                if row == full_rows and rem > 0:
                    row_w = rem * step_x
                    row_start_x = pad_x + (aw - row_w) / 2.0
                    cx = row_start_x + col * step_x + step_x / 2.0
                else:
                    cx = pad_x + col * step_x + step_x / 2.0
                cy = pad_y + row * step_y + step_y / 2.0
                positions.append((cx, cy, r, False))
            return positions

    def draw_circles(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        positions = self.circle_asymmetric_geometry(width, height)
        if not positions:
            return

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for color, (cx, cy, r, is_hero) in zip(self.colors, positions):
            s_draw.ellipse(
                [round(cx - r), round(cy - r), round(cx + r), round(cy + r)],
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 5), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        image.alpha_composite(shapes_layer)

        for color, (cx, cy, r, is_hero) in zip(self.colors, positions):
            lines = get_color_labels(color, self.label_formats)
            if lines:
                font_sz = min(24, max(10, int(r * 0.26)))
                if len(self.colors) >= 20:
                    font_sz = min(12, max(8, int(r * 0.35)))

                self.draw_direct_labels(draw, cx, cy, lines, color,
                                        max_w=r * 1.70, font_size=font_sz)
    # ========================================================
    def draw_strips(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        count = len(self.colors)
        if count == 0:
            return

        gap = max(2, round(min(width, height) * 0.004))
        hero_idx = self.get_hero_index(self.colors)

        if count > 1:
            hero_weight = 1.45
            total_weight = (count - 1) + hero_weight
            weights = [(hero_weight if i == hero_idx else 1.0) / total_weight for i in range(count)]
        else:
            weights = [1.0]

        usable_w = width - gap * (count - 1)
        current_x = 0.0

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for index, (color, w) in enumerate(zip(self.colors, weights)):
            strip_w = usable_w * w
            x0 = current_x
            x1 = current_x + strip_w

            s_draw.rectangle(
                [round(x0), 0, round(x1), height],
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )
            current_x += strip_w + gap

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 4), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
        image.alpha_composite(shapes_layer)

        current_x = 0.0
        for index, (color, w) in enumerate(zip(self.colors, weights)):
            strip_w = usable_w * w
            x0 = current_x
            x1 = current_x + strip_w
            lines = get_color_labels(color, self.label_formats)
            if lines:
                cx = (x0 + x1) / 2.0
                cy = height * 0.65
                font_sz = min(22, max(10, int(strip_w * 0.24)))
                if count >= 16:
                    font_sz = min(15, max(8, int(strip_w * 0.32)))
                self.draw_vertical_direct_labels(image, cx, cy, lines, color,
                                                 max_h=height * 0.65, font_size=font_sz)
            current_x += strip_w + gap

    # ========================================================
    # 7. CANVAS LAYOUT (Harmonic Portrait Poster with Direct Labels)
    # ========================================================
    def draw_poster(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int, transparent: bool = False) -> None:
        count = len(self.colors)
        if count == 0:
            return

        hero_idx = self.get_hero_index(self.colors)
        if count > 1:
            hero_w = 1.35
            total_w = (count - 1) + hero_w
            weights = [(hero_w if i == hero_idx else 1.0) / total_w for i in range(count)]
        else:
            weights = [1.0]

        current_y = 0.0
        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for i, (color, w) in enumerate(zip(self.colors, weights)):
            band_h = height * w
            band_y0 = current_y
            band_y1 = height if i == count - 1 else current_y + band_h

            s_draw.rectangle(
                [0, round(band_y0), width, round(band_y1)],
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )
            current_y += band_h

        s_draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255, 45), width=1)

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 6), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
        image.alpha_composite(shapes_layer)

        current_y = 0.0
        for i, (color, w) in enumerate(zip(self.colors, weights)):
            band_h = height * w
            band_y0 = current_y
            band_y1 = height if i == count - 1 else current_y + band_h

            lines = get_color_labels(color, self.label_formats)
            if lines:
                font_sz = min(25, max(12, int(min(width, band_h) * (0.18 if i == hero_idx else 0.15))))
                if count >= 20:
                    font_sz = min(13, max(8, int(band_h * 0.38)))

                cy = (band_y0 + band_y1) / 2.0
                cx = width * 0.28
                self.draw_direct_labels(draw, cx, cy, lines, color,
                                        max_w=width * 0.50, font_size=font_sz)

            current_y += band_h

    # ========================================================
    # 8. HONEYCOMB LAYOUT (Clustered Flat-Topped Tessellation)
    # ========================================================
    def honeycomb_geometry(self, width: float, height: float):
        count = len(self.colors)
        if count <= 0:
            return []

        best = None
        for columns in range(1, count + 1):
            rows = math.ceil(count / columns)
            w_factor = 2.0 + 1.5 * (columns - 1)
            h_factor = math.sqrt(3) * rows + (math.sqrt(3) / 2.0 if columns > 1 else 0)

            radius_x = (width * 0.94) / w_factor
            radius_y = (height * 0.94) / h_factor
            radius = min(radius_x, radius_y)

            empty_slots = columns * rows - count
            aspect_ratio = (w_factor / max(1.0, h_factor))
            canvas_aspect = width / max(1.0, height)
            aspect_penalty = abs(math.log(max(0.1, aspect_ratio) / max(0.1, canvas_aspect)))

            score = radius - (empty_slots * 0.12 * radius) - (aspect_penalty * 0.10 * radius)

            candidate = (score, radius, columns, rows)
            if best is None or candidate[0] > best[0]:
                best = candidate

        _, radius, columns, rows = best
        radius *= 0.96

        dx = 1.5 * radius
        dy = math.sqrt(3) * radius

        total_width = 2 * radius + (columns - 1) * dx
        total_height = rows * dy + (dy / 2.0 if columns > 1 else 0)

        start_x = (width - total_width) / 2.0 + radius
        start_y = (height - total_height) / 2.0 + radius * math.sqrt(3) / 2.0

        tile_r = radius - 3.0

        positions = []
        for index in range(count):
            row, column = divmod(index, columns)
            cx = start_x + column * dx
            cy = start_y + row * dy + (dy / 2.0 if column % 2 else 0)

            points = []
            for point_index in range(6):
                angle = math.radians(60 * point_index)
                points.append((
                    cx + tile_r * math.cos(angle),
                    cy + tile_r * math.sin(angle),
                ))

            positions.append((points, cx, cy, tile_r))

        return positions

    def draw_honeycomb(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        positions = self.honeycomb_geometry(width, height)
        if not positions:
            return

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for color, (points, cx, cy, r) in zip(self.colors, positions):
            s_draw.polygon(points, fill=color, outline=(255, 255, 255, 22))

        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 5), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        image.alpha_composite(shapes_layer)

        for color, (points, cx, cy, r) in zip(self.colors, positions):
            lines = get_color_labels(color, self.label_formats)
            if lines:
                font_sz = min(24, max(11, int(r * 0.26)))
                if len(self.colors) >= 20:
                    font_sz = min(12, max(8, int(r * 0.35)))

                self.draw_direct_labels(draw, cx, cy, lines, color,
                                        max_w=r * 1.65, font_size=font_sz)

    # ========================================================
    # 9. RIBBON LAYOUT (Vertical Bars with Large Horizontal Text)
    # ========================================================
    def draw_ribbon(self, image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        count = len(self.colors)
        if count == 0:
            return

        ribbon_top = height * 0.05
        ribbon_bottom = height * 0.95
        ribbon_h = ribbon_bottom - ribbon_top

        margin_x = width * 0.04
        gap = max(6, int(width * 0.012))
        avail_w = width - margin_x * 2

        hero_idx = self.get_hero_index(self.colors)
        if count > 1:
            hero_w = 1.40
            total_w = (count - 1) + hero_w
            weights = [(hero_w if i == hero_idx else 1.0) / total_w for i in range(count)]
        else:
            weights = [1.0]

        usable_w = avail_w - gap * (count - 1)
        current_x = margin_x

        shapes_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shapes_layer)

        for index, (color, w) in enumerate(zip(self.colors, weights)):
            bar_w = usable_w * w
            x0 = current_x
            x1 = current_x + bar_w
            radius = int(bar_w * 0.16)

            s_draw.rounded_rectangle(
                [round(x0), round(ribbon_top), round(x1), round(ribbon_bottom)],
                radius=radius,
                fill=color,
                outline=(255, 255, 255, 22),
                width=1
            )
            current_x += bar_w + gap

        # Drop shadow
        alpha_mask = shapes_layer.split()[3]
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_black = Image.new("RGBA", (width, height), (0, 0, 0, 60))
        shadow.paste(shadow_black, (0, 5), mask=alpha_mask)
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        image.alpha_composite(shapes_layer)

        # Rotated 90 degrees vertical stacked typography in lower-middle of each column
        current_x = margin_x
        for index, (color, w) in enumerate(zip(self.colors, weights)):
            bar_w = usable_w * w
            x0 = current_x
            x1 = current_x + bar_w
            lines = get_color_labels(color, self.label_formats)
            if lines:
                cx = (x0 + x1) / 2.0
                cy = ribbon_bottom - max(60.0, ribbon_h * 0.28)
                font_sz = min(22, max(10, int(bar_w * 0.24)))
                if count >= 16:
                    font_sz = min(15, max(8, int(bar_w * 0.32)))

                self.draw_vertical_direct_labels(image, cx, cy, lines, color,
                                                 max_h=ribbon_h * 0.60, font_size=font_sz)

            current_x += bar_w + gap

    @staticmethod
    def draw_centered_text_single(draw: ImageDraw.ImageDraw, box: Tuple[float, float, float, float],
                                  text: str, fill: str, font: ImageFont.ImageFont) -> None:
        x0, y0, x1, y1 = box
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        draw.text((cx - tw / 2.0 - bbox[0], cy - th / 2.0 - bbox[1]), text, fill=fill, font=font)

    # ========================================================
    # SVG VECTOR EXPORT (Adaptive Direct Labels, Hairlines, Drop Shadows)
    # ========================================================
    def render_svg(self, size: Tuple[int, int], background: str) -> str:
        width, height = size
        output = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">',
            '<defs>',
            '<style>',
            "@import url('https://fonts.googleapis.com/css2?family=League+Spartan:wght@700;800&amp;family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500&amp;display=swap');",
            "text { font-family: 'Inter', 'Calibri', 'Helvetica Neue', 'Helvetica', sans-serif; }",
            ".svg-mono { font-family: 'JetBrains Mono', monospace; }",
            ".svg-title { font-family: 'League Spartan', sans-serif; font-weight: 800; letter-spacing: 4px; }",
            ".svg-subtitle { font-family: 'League Spartan', sans-serif; font-weight: 700; letter-spacing: 2px; }",
            '</style>',
            '<filter id="shape-shadow" x="-8%" y="-8%" width="116%" height="116%">',
            '<feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#000000" flood-opacity="0.25"/>',
            '</filter>',
            '</defs>',
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{background}"/>'
        ]

        if not self.colors:
            output.append("</svg>")
            return "".join(output)

        count = len(self.colors)
        norm = self.layout

        if norm == "Blocks":
            boxes = self.compute_blocks_geometry(width, height)
            for index, (color, (x0, y0, x1, y1, _)) in enumerate(zip(self.colors, boxes)):
                cw = x1 - x0
                ch = y1 - y0
                c1 = contrast_text(color)
                c2 = "rgba(17,17,17,0.85)" if c1 == "#111111" else "rgba(240,240,240,0.85)"

                output.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{cw:.2f}" height="{ch:.2f}" '
                    f'fill="{color}" stroke="rgba(255,255,255,0.10)" stroke-width="1"/>'
                )

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    font_sz = min(22.0, max(11.0, min(cw, ch) * 0.12))
                    cx = (x0 + x1) / 2.0
                    cy = (y0 + y1) / 2.0

                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                        )
                    else:
                        gap = font_sz * 0.70
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy - gap * 0.5:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{cy + gap * 1.1:.2f}" font-size="{font_sz * 0.82:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c2}">{lines[1]}</text>'
                        )

        elif norm == "Chips":
            boxes = self.compute_chips_geometry(width, height)
            for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
                cw = x1 - x0
                ch = y1 - y0
                r_card = min(14.0, max(6.0, cw * 0.08))
                y_split = y0 + ch * 0.72
                white_h = y1 - y_split

                # White card base
                output.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{cw:.2f}" height="{ch:.2f}" '
                    f'rx="{r_card:.2f}" fill="#FFFFFF" stroke="rgba(220,222,228,0.9)" filter="url(#shape-shadow)"/>'
                )

                # Upper color swatch
                output.append(
                    f'<path d="M {x0:.2f} {y_split:.2f} L {x0:.2f} {y0 + r_card:.2f} '
                    f'Q {x0:.2f} {y0:.2f} {x0 + r_card:.2f} {y0:.2f} '
                    f'L {x1 - r_card:.2f} {y0:.2f} '
                    f'Q {x1:.2f} {y0:.2f} {x1:.2f} {y0 + r_card:.2f} '
                    f'L {x1:.2f} {y_split:.2f} Z" fill="{color}"/>'
                )

                # Line divider
                output.append(f'<line x1="{x0:.2f}" y1="{y_split:.2f}" x2="{x1:.2f}" y2="{y_split:.2f}" stroke="rgba(220,222,228,0.9)" stroke-width="1"/>')

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    cx = (x0 + x1) / 2.0
                    font_sz = min(18.0, max(9.0, cw * 0.11))

                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.55:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="#18181B">{lines[0]}</text>'
                        )
                    else:
                        output.append(
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.40:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="#18181B">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.76:.2f}" font-size="{font_sz * 0.84:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="#52525B">{lines[1]}</text>'
                        )

        elif norm == "Collage":
            boxes = self.compute_collage_geometry(width, height)
            margin_x = max(14.0, width * 0.018)
            margin_y = max(12.0, height * 0.016)

            for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
                cw = x1 - x0
                ch = y1 - y0
                c_name = contrast_text(color)
                c_code = "rgba(17,17,17,0.85)" if c_name == "#111111" else "rgba(240,240,240,0.85)"

                output.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{cw:.2f}" height="{ch:.2f}" '
                    f'fill="{color}" stroke="rgba(255,255,255,0.10)" stroke-width="1"/>'
                )

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    font_sz = min(18.0, max(10.0, min(cw, ch) * 0.11))
                    tx = x1 - margin_x
                    ty = y1 - margin_y
                    
                    if len(lines) == 1:
                        output.append(
                            f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="end" fill="{c_name}">{lines[0]}</text>'
                        )
                    else:
                        line_gap = font_sz * 1.25
                        output.append(
                            f'<text x="{tx:.2f}" y="{ty - line_gap:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="end" fill="{c_name}">{lines[0]}</text>'
                            f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="{font_sz * 0.84:.2f}" font-weight="500" class="svg-mono" text-anchor="end" fill="{c_code}">{lines[1]}</text>'
                        )

        elif norm == "Orbs":
            positions = self.circle_asymmetric_geometry(width, height)
            for color, (cx, cy, r, is_hero) in zip(self.colors, positions):
                output.append(
                    f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{color}" '
                    f'stroke="rgba(255,255,255,0.10)" stroke-width="1" filter="url(#shape-shadow)"/>'
                )
                lines = get_color_labels(color, self.label_formats)
                if lines:
                    c1 = contrast_text(color)
                    c2 = "rgba(17,17,17,0.85)" if c1 == "#111111" else "rgba(240,240,240,0.85)"
                    font_sz = min(22.0, max(10.0, r * 0.22))

                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                        )
                    else:
                        gap = font_sz * 0.70
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy - gap * 0.5:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{cy + gap * 1.1:.2f}" font-size="{font_sz * 0.82:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c2}">{lines[1]}</text>'
                        )

        elif norm == "Honeycomb":
            positions = self.honeycomb_geometry(width, height)
            for color, (points, cx, cy, r) in zip(self.colors, positions):
                pts_str = " ".join([f"{px:.2f},{py:.2f}" for px, py in points])
                output.append(f'<polygon points="{pts_str}" fill="{color}" stroke="rgba(255,255,255,0.10)" filter="url(#shape-shadow)"/>')

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    c1 = contrast_text(color)
                    c2 = "rgba(17,17,17,0.85)" if c1 == "#111111" else "rgba(240,240,240,0.85)"
                    font_sz = min(22.0, max(10.0, r * 0.22))

                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                        )
                    else:
                        gap = font_sz * 0.70
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy - gap * 0.5:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c1}">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{cy + gap * 1.1:.2f}" font-size="{font_sz * 0.82:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c2}">{lines[1]}</text>'
                        )

        elif norm == "Pillars":
            count = len(self.colors)
            margin_x = width * 0.04
            gap = max(4.0, width * 0.012)
            avail_w = width - margin_x * 2
            hero_idx = self.get_hero_index(self.colors)
            hero_w = 1.40 if count > 1 else 1.0
            total_w = (count - 1) + hero_w if count > 1 else 1.0
            usable_w = avail_w - gap * (count - 1)
            cur_x = margin_x

            for index, color in enumerate(self.colors):
                w = (hero_w if index == hero_idx else 1.0) / total_w
                bar_w = usable_w * w
                radius = min(24.0, bar_w * 0.16)
                c_name = contrast_text(color)
                c_code = "rgba(17,17,17,0.85)" if c_name == "#111111" else "rgba(240,240,240,0.85)"

                output.append(
                    f'<rect x="{cur_x:.2f}" y="{height * 0.05:.2f}" width="{bar_w:.2f}" height="{height * 0.90:.2f}" '
                    f'rx="{radius:.2f}" fill="{color}" stroke="rgba(255,255,255,0.10)" filter="url(#shape-shadow)"/>'
                )

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    font_sz = min(22.0, max(10.0, bar_w * 0.24))
                    cx = cur_x + bar_w / 2.0
                    cy = height * 0.95 - (height * 0.90) * 0.28
                    if len(lines) == 1:
                        output.append(
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                        )
                    else:
                        output.append(
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy - 4:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy + font_sz * 0.84 + 2:.2f}" font-size="{font_sz * 0.84:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c_code}">{lines[1]}</text>'
                        )
                cur_x += bar_w + gap

        elif norm == "Canvas":
            # Canvas / Studio Poster layout: horizontal full-width harmonic bands
            hero_idx = self.get_hero_index(self.colors)
            if count > 1:
                hero_w = 1.35
                total_w = (count - 1) + hero_w
                weights = [(hero_w if i == hero_idx else 1.0) / total_w for i in range(count)]
            else:
                weights = [1.0]

            cur_y = 0.0
            for index, (color, w) in enumerate(zip(self.colors, weights)):
                band_h = height * w
                band_y0 = cur_y
                band_y1 = height if index == count - 1 else cur_y + band_h
                h_actual = band_y1 - band_y0

                c_name = contrast_text(color)
                c_code = "rgba(17,17,17,0.85)" if c_name == "#111111" else "rgba(240,240,240,0.85)"

                output.append(
                    f'<rect x="0" y="{band_y0:.2f}" width="{width}" height="{h_actual:.2f}" '
                    f'fill="{color}" stroke="rgba(255,255,255,0.10)"/>'
                )

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    font_sz = min(26.0, max(12.0, min(width, h_actual) * (0.18 if index == hero_idx else 0.15)))
                    if count >= 20:
                        font_sz = min(13.0, max(8.0, h_actual * 0.38))
                    
                    cx = width * 0.28
                    cy = (band_y0 + band_y1) / 2.0

                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                        )
                    else:
                        gap = font_sz * 0.70
                        output.append(
                            f'<text x="{cx:.2f}" y="{cy - gap * 0.5:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{cy + gap * 1.1:.2f}" font-size="{font_sz * 0.82:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c_code}">{lines[1]}</text>'
                        )

                cur_y += band_h

        elif norm == "Ribbons":
            # Ribbons layout: vertical columns with gap
            gap = max(2.0, min(width, height) * 0.004)
            usable = width - gap * (count - 1)
            strip_width = usable / count

            for index, color in enumerate(self.colors):
                x = index * (strip_width + gap)
                c_name = contrast_text(color)
                c_code = "rgba(17,17,17,0.85)" if c_name == "#111111" else "rgba(240,240,240,0.85)"
                output.append(f'<rect x="{x:.2f}" y="0" width="{strip_width:.2f}" height="{height}" fill="{color}" stroke="rgba(255,255,255,0.10)"/>')

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    font_sz = min(22.0, max(10.0, strip_width * 0.24))
                    cx = x + strip_width / 2.0
                    cy = height * 0.65
                    if len(lines) == 1:
                        output.append(
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy + font_sz * 0.35:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                        )
                    else:
                        output.append(
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy - 4:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="{c_name}">{lines[0]}</text>'
                            f'<text transform="rotate(-90, {cx:.2f}, {cy:.2f})" x="{cx:.2f}" y="{cy + font_sz * 0.84 + 2:.2f}" font-size="{font_sz * 0.84:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="{c_code}">{lines[1]}</text>'
                        )

        else:
            # General fallback to Chips
            boxes = self.compute_chips_geometry(width, height)
            for index, (color, (x0, y0, x1, y1)) in enumerate(zip(self.colors, boxes)):
                cw = x1 - x0
                ch = y1 - y0
                r_card = min(14.0, max(6.0, cw * 0.08))
                y_split = y0 + ch * 0.72
                white_h = y1 - y_split

                output.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{cw:.2f}" height="{ch:.2f}" '
                    f'rx="{r_card:.2f}" fill="#FFFFFF" stroke="rgba(220,222,228,0.9)" filter="url(#shape-shadow)"/>'
                )
                output.append(
                    f'<path d="M {x0:.2f} {y_split:.2f} L {x0:.2f} {y0 + r_card:.2f} '
                    f'Q {x0:.2f} {y0:.2f} {x0 + r_card:.2f} {y0:.2f} '
                    f'L {x1 - r_card:.2f} {y0:.2f} '
                    f'Q {x1:.2f} {y0:.2f} {x1:.2f} {y0 + r_card:.2f} '
                    f'L {x1:.2f} {y_split:.2f} Z" fill="{color}"/>'
                )
                output.append(f'<line x1="{x0:.2f}" y1="{y_split:.2f}" x2="{x1:.2f}" y2="{y_split:.2f}" stroke="rgba(220,222,228,0.9)" stroke-width="1"/>')

                lines = get_color_labels(color, self.label_formats)
                if lines:
                    cx = (x0 + x1) / 2.0
                    font_sz = min(18.0, max(9.0, cw * 0.11))
                    if len(lines) == 1:
                        output.append(
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.55:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="#18181B">{lines[0]}</text>'
                        )
                    else:
                        output.append(
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.40:.2f}" font-size="{font_sz:.2f}" font-weight="600" text-anchor="middle" fill="#18181B">{lines[0]}</text>'
                            f'<text x="{cx:.2f}" y="{y_split + white_h * 0.76:.2f}" font-size="{font_sz * 0.84:.2f}" font-weight="500" class="svg-mono" text-anchor="middle" fill="#52525B">{lines[1]}</text>'
                        )

        output.append("</svg>")
        return "".join(output)
