"""
Theme loader and dynamic CSS generator for PaletteLab Web.
Reads themes directly from static/themes.json in consistent order:
"Palette Name, Background, Frame (Card), Border / Line, Accent (Button), Text"
"""

import json
import os
import re
import colorsys

THEMES_JSON_PATH = "static/themes.json"

def slugify(text: str) -> str:
    """Convert theme name to clean CSS class slug."""
    text = re.sub(r'\(.*?\)', '', text)  # remove parenthetical note like (Light)
    text = text.strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def load_themes_data():
    """
    Load themes from themes.json, stripping top comments.
    Order of fields in each theme tuple:
    0: Palette Name
    1: Background
    2: Frame (Card)
    3: Border / Line
    4: Accent (Button)
    5: Text
    """
    if not os.path.exists(THEMES_JSON_PATH):
        return []
    
    with open(THEMES_JSON_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Strip any leading C-style or JS comments
    content = re.sub(r'//.*?\n', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL).strip()
    
    return json.loads(content)

def get_theme_list():
    """Returns list of categories with (slug, name, bg, frame, border, accent, text)."""
    categories = load_themes_data()
    result = []
    for cat in categories:
        cat_name = cat.get("category", "")
        theme_items = []
        for item in cat.get("themes", []):
            name, bg, frame, border, accent, text = item
            slug = slugify(name)
            theme_items.append({
                "slug": slug,
                "name": name,
                "bg": bg,
                "frame": frame,
                "border": border,
                "accent": accent,
                "text": text
            })
        result.append({"category": cat_name, "themes": theme_items})
    return result

def hex_to_rgb(hex_str: str):
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)

def is_light_color(hex_str: str) -> bool:
    r, g, b = hex_to_rgb(hex_str)
    # Relative luminance
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return lum > 0.45

def generate_theme_css() -> str:
    """Generate all CSS rules for all themes directly from static/themes.json."""
    theme_categories = get_theme_list()
    css_blocks = []
    
    for cat in theme_categories:
        for t in cat["themes"]:
            slug = t["slug"]
            name = t["name"]
            bg = t["bg"]
            frame = t["frame"]
            border = t["border"]
            accent = t["accent"]
            text = t["text"]
            
            is_light = is_light_color(bg)
            scheme = "light" if is_light else "dark"
            
            # Compute slider tokens (constant for all light themes, constant for all dark themes)
            if is_light:
                slider_track = "rgba(0, 0, 0, 0.16)"
                slider_thumb = "#374151"
                slider_thumb_border = "#FFFFFF"
            else:
                slider_track = "rgba(255, 255, 255, 0.20)"
                slider_thumb = "#E0E0E0"
                slider_thumb_border = "#111111"
            
            css_block = f"""
.theme-{slug} {{
    color-scheme: {scheme};
    --bg-main: {bg};
    --panel-bg: {frame};
    --border-color: {border};
    --accent-red: {accent};
    --accent-red-hover: {accent};
    --accent-text: {accent_text};
    --text-main: {text};
    --text-muted: {muted};
    --slider-track: {slider_track};
    --slider-thumb: {slider_thumb};
    --slider-thumb-border: {slider_thumb_border};
}}"""
            css_blocks.append(css_block)
            
    return "\n".join(css_blocks)
