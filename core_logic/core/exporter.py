"""
PaletteLab artwork exporter with calm adaptive backgrounds, light/airy default aesthetic,
minimalist studio elevation, and >=72% dominant palette area coverage.
"""

from datetime import datetime
from pathlib import Path
from typing import Sequence, Tuple, Optional
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

from core_logic.core.color_utils import (
    contrast_text, relative_luminance, rgb_from_hex, hex_from_rgb, hsl_from_hex,
    get_three_part_bg_tints, lab_from_hex, hex_from_lab
)
from core_logic.generatePalette.color_matcher import delta_e_2000
from core_logic.core.renderer import (
    PaletteRenderer, get_title_font, get_display_font, get_mono_font
)


def get_palette_dimensions(count: int) -> Tuple[int, int]:
    """Generates standard luxury 4:5 portrait dimensions for high-res export."""
    return 1400, 1750


def get_github_icon(size: int = 24, fill_color: str = "#141722") -> Optional[Image.Image]:
    """Load and render GitHub icon to rasterized PIL Image with given fill color using pure Pillow."""
    icon_path = Path("static/icons/github.png")
    if not icon_path.exists():
        icon_path = Path(__file__).resolve().parent.parent.parent / "static" / "icons" / "github.png"
    
    if icon_path.exists():
        try:
            base_icon = Image.open(icon_path).convert("RGBA")
            resized = base_icon.resize((size, size), Image.Resampling.LANCZOS)
            r, g, b = rgb_from_hex(fill_color)
            tinted = Image.new("RGBA", (size, size), (r, g, b, 255))
            tinted.putalpha(resized.split()[3])
            return tinted
        except Exception as e:
            print(f"Error loading github icon via Pillow: {e}")

    # Fallback to PySide6 if available
    svg_data = f"""<svg viewBox="0 0 24 24" width="{size}" height="{size}">
<path fill="{fill_color}" fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
</svg>"""
    try:
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtCore import QByteArray, Qt
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        qimg = QImage(size, size, QImage.Format_RGBA8888)
        qimg.fill(Qt.transparent)
        painter = QPainter(qimg)
        renderer.render(painter)
        painter.end()
        return Image.frombytes("RGBA", (size, size), bytes(qimg.constBits())).copy()
    except Exception:
        pass
    return None


def get_export_directory() -> Path:
    """Ensure and return the exports/ folder in the project directory."""
    base = Path(".")
    folder = base / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_timestamped_path(extension: str) -> Path:
    """Generate unique timestamped filepath inside exports/ folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return get_export_directory() / f"palette_{timestamp}.{extension}"




def get_wcag_text_contrast(bg_hex: str) -> str:
    """
    To guarantee strict WCAG accessibility compliance for your palette labels,
    calculate Relative Luminance and flip threshold at 0.179.
    """
    lum = relative_luminance(bg_hex)
    return "#000000" if lum > 0.179 else "#FFFFFF"

def maximin_ciede2000_background(colors: Sequence[str]) -> str:
    """
    Maximin Optimization using CIEDE2000 to dynamically calculate the absolute
    perfect solid background for each individual palette.
    Neutral Axis: a=0, b=0. Steps L from 0 to 100.
    """
    if not colors:
        return "#FFFFFF"
        
    palette_labs = [lab_from_hex(c) for c in colors]
    best_l = 100.0
    best_min_de = -1.0
    
    # Sweep Neutral Axis (L from 15 to 95 in increments of 1.0)
    for l_val in range(15, 96):
        bg_lab = (float(l_val), 0.0, 0.0)
        
        # Identify the Weakest Link (lowest delta E)
        current_min_de = min(delta_e_2000(bg_lab, p_lab) for p_lab in palette_labs)
        
        # Maximize the Minimum (Maximin)
        if current_min_de > best_min_de:
            best_min_de = current_min_de
            best_l = float(l_val)
            
    return hex_from_lab(best_l, 0.0, 0.0)

def render_export_image(colors: Sequence[str], layout: str,
                        label_formats: Optional[Sequence[str]] = None,
                        bg_color: Optional[str] = None,
                        auto_background: bool = True) -> Image.Image:
    """
    Render design poster export:
    1. Perfect solid background from Maximin optimization or White
    2. Hero-sized palette artwork occupying >= 72% of canvas area
    3. Direct adaptive label text without background boxes
    4. Hairline 8% white borders on every swatch shape
    5. Soft elevated drop shadows under every shape
    6. League Spartan Title & Subtitle: 'PALETTE LAB BY [Icon]/ENDLESSBRAIN'
    7. Clean bottom brand mark badge
    """
    width, height = get_palette_dimensions(len(colors))
    count = len(colors)

    if count == 0:
        return Image.new("RGB", (width, height), "#FFFFFF")

    # 1. Background generation
    if auto_background:
        final_bg = maximin_ciede2000_background(colors)
    else:
        final_bg = "#FFFFFF"

    bg_image = Image.new("RGB", (width, height), final_bg)
    bg_draw = ImageDraw.Draw(bg_image)

    # 2. Header Typography colors (Dynamic based on WCAG contrast)
    col_title = get_wcag_text_contrast(final_bg)
    # Subtitle is just a slightly translucent version of the main text color
    r, g, b = rgb_from_hex(col_title)
    col_sub = (r, g, b, int(255 * 0.65))

    title_font = get_title_font(int(height * 0.024))
    sub_font = get_title_font(int(height * 0.0115))

    title_text = "P A L E T T E   L A B"
    title_y = int(height * 0.032)

    PaletteRenderer.draw_centered_text_single(
        bg_draw,
        (0, title_y, width, title_y + 32),
        title_text,
        col_title,
        title_font
    )

    # 3. Subtitle with GitHub icon: B Y  [Icon]/ E N D L E S S B R A I N
    sub_y = title_y + int(height * 0.028)
    part1 = "BY  "
    part2 = "/Manjunadh-Velpuri"

    bbox1 = bg_draw.textbbox((0, 0), part1, font=sub_font)
    tw1 = bbox1[2] - bbox1[0]
    th1 = bbox1[3] - bbox1[1]

    bbox2 = bg_draw.textbbox((0, 0), part2, font=sub_font)
    tw2 = bbox2[2] - bbox2[0]

    icon_sz = max(18, int(height * 0.015))
    gh_icon = get_github_icon(icon_sz, col_title)
    margin_icon = 6 if gh_icon else 0

    total_sub_w = tw1 + (icon_sz + margin_icon * 2 if gh_icon else 0) + tw2
    sub_x = (width - total_sub_w) / 2.0

    # Draw Part 1 ("B Y  ")
    bg_draw.text((sub_x, sub_y - bbox1[1]), part1, fill=col_sub, font=sub_font)

    # Draw GitHub Icon
    cur_x = sub_x + tw1
    if gh_icon:
        cur_x += margin_icon
        icon_y = int(sub_y + (th1 - icon_sz) / 2.0)
        bg_image.paste(gh_icon, (int(cur_x), icon_y), gh_icon)
        cur_x += icon_sz + margin_icon

    # Draw Part 2 ("/ MANJUNADH-VELPURI")
    bg_draw.text((cur_x, sub_y - bbox2[1]), part2, fill=col_sub, font=sub_font)

    # 4. Hero Sized Floating Palette Artwork (Occupying >= 72% of total image area)
    art_top = int(height * 0.092)
    art_bottom = int(height * 0.908)
    art_h = art_bottom - art_top
    art_w = int(width * 0.89)
    art_x = int((width - art_w) / 2.0)

    # Render inner layout to transparent RGBA layer
    renderer = PaletteRenderer(colors, layout, label_formats=label_formats)
    artwork = renderer.render((art_w, art_h), bg_color or "#FAF9F6", transparent=True)

    # Subtle elevation drop shadow for the whole composition
    margin_shadow = 40
    shadow_canvas = Image.new("RGBA", (art_w + margin_shadow * 2, art_h + margin_shadow * 2), (0, 0, 0, 0))
    alpha_mask = artwork.split()[3]

    shadow_opacity = 40
    black_fill = Image.new("RGBA", (art_w, art_h), (0, 0, 0, shadow_opacity))
    shadow_canvas.paste(black_fill, (margin_shadow, margin_shadow), mask=alpha_mask)
    shadow_blurred = shadow_canvas.filter(ImageFilter.GaussianBlur(16))

    bg_image.paste(
        shadow_blurred,
        (art_x - margin_shadow, art_top - margin_shadow + 10),
        shadow_blurred
    )

    # Composite artwork on top
    bg_image.paste(artwork, (art_x, art_top), artwork)

    # 5. Clean Bottom Brand Mark Badge
    badge_sz = int(height * 0.034)
    badge_x0 = int((width - badge_sz) / 2.0)
    badge_y0 = int(height * 0.935)
    badge_x1 = badge_x0 + badge_sz
    badge_y1 = badge_y0 + badge_sz

    bg_draw.rectangle((badge_x0, badge_y0, badge_x1, badge_y1), outline=col_title, width=2)
    badge_font = get_title_font(int(badge_sz * 0.28))
    bg_draw.text((badge_x0 + badge_sz * 0.22, badge_y0 + badge_sz * 0.15), "P", fill=col_title, font=badge_font)
    bg_draw.text((badge_x0 + badge_sz * 0.58, badge_y0 + badge_sz * 0.15), "L", fill=col_title, font=badge_font)
    bg_draw.text((badge_x0 + badge_sz * 0.22, badge_y0 + badge_sz * 0.55), "A", fill=col_title, font=badge_font)
    bg_draw.text((badge_x0 + badge_sz * 0.58, badge_y0 + badge_sz * 0.55), "B", fill=col_title, font=badge_font)

    return bg_image


def save_palette_png(colors: Sequence[str], layout: str,
                     label_formats: Optional[Sequence[str]] = None,
                     bg_color: Optional[str] = None,
                     auto_background: bool = True) -> Path:
    """Save palette as high-res PNG poster into exports/ folder and return path."""
    image = render_export_image(colors, layout, label_formats=label_formats, bg_color=bg_color, auto_background=auto_background)
    path = get_timestamped_path("png")
    image.save(
        path,
        "PNG",
        optimize=True,
        compress_level=9,
        dpi=(300, 300),
    )
    return path


def save_palette_svg(colors: Sequence[str], layout: str,
                     label_formats: Optional[Sequence[str]] = None,
                     bg_color: Optional[str] = None,
                     auto_background: bool = True) -> Path:
    """Save palette as vector SVG file into exports/ folder."""
    if auto_background:
        bg_color = maximin_ciede2000_background(colors)
    else:
        bg_color = "#FFFFFF"

    width, height = get_palette_dimensions(len(colors))
    renderer = PaletteRenderer(colors, layout, label_formats=label_formats)
    svg_data = renderer.render_svg((width, height), bg_color)
    path = get_timestamped_path("svg")
    path.write_text(svg_data, encoding="utf-8")
    return path


def open_file_in_os(path: Path) -> None:
    """Open the exported file in the default operating system image viewer."""
    try:
        import platform
        import subprocess
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as e:
        print(f"Failed to launch OS file viewer: {e}")
