"""
FastHTML Serverless Entry Point for PaletteLab Web
Ultra-fast SVG live canvas rendering (<10ms), dynamic OOB updates, session persistence, Conversion Table workspace.
"""
from fasthtml.common import *
import sys
import os
import io
import json
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

# Ensure core_logic is resolvable
sys.path.append(".")

from core_logic.core.color_utils import normalize_hex, get_color_name, relative_luminance, hsl_from_hex, apply_shade
from core_logic.parsers import PARSERS
from core_logic.core.renderer import PaletteRenderer
from core_logic.core.exporter import render_export_image, maximin_ciede2000_background

from web_ui.components.layout import Layout
from web_ui.components.color_row import ColorRow
from web_ui.components.color_picker_modal import ColorPickerModal
from web_ui.components.photo_modal import PhotoExtractModal
from web_ui.components.conversion_table import ConversionTable

# App configuration with session middleware
app, rt = fast_app(
    secret_key=os.environ.get("SECRET_KEY", "dev-secret-key-palettelab-12345"),
    hdrs=(
        Link(rel="stylesheet", href="/static/css/glass_theme.css?v=2.0"),
        Script(src="/static/js/interactions.js?v=2.0")
    )
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

def get_sorted_colors(colors: list, sort_mode: str) -> list:
    """Sort colors based on the selected mode."""
    if not colors:
        return []
    res = list(colors)
    if sort_mode == "Luminance_Desc":
        res.sort(key=lambda c: relative_luminance(c), reverse=True)
    elif sort_mode == "Luminance_Asc":
        res.sort(key=lambda c: relative_luminance(c))
    elif sort_mode == "Hue":
        res.sort(key=lambda c: hsl_from_hex(c)[0])
    elif sort_mode == "Saturation":
        res.sort(key=lambda c: hsl_from_hex(c)[1], reverse=True)
    return res

def get_active_colors(session):
    """Return only the colors that are currently checked/enabled by the user."""
    colors = session.get("colors", [])
    enabled = session.get("color_enabled", [])
    while len(enabled) < len(colors):
        enabled.append(True)
    session["color_enabled"] = enabled
    return [c for c, is_on in zip(colors, enabled) if is_on]

def render_color_list(session):
    """Render the sidebar scrollable list of recognized colors with base, offset, and selection persistence."""
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    enabled = session.get("color_enabled", [])
    models = session.get("color_models", [])
    
    # Keep base_colors, offsets, and enabled synchronized with colors length
    while len(base_colors) < len(colors):
        base_colors.append(colors[len(base_colors)])
    if len(base_colors) > len(colors):
        base_colors = base_colors[:len(colors)]
    session["base_colors"] = base_colors
    
    while len(offsets) < len(colors):
        offsets.append(0)
    if len(offsets) > len(colors):
        offsets = offsets[:len(colors)]
    session["color_offsets"] = offsets

    while len(enabled) < len(colors):
        enabled.append(True)
    if len(enabled) > len(colors):
        enabled = enabled[:len(colors)]
    session["color_enabled"] = enabled

    while len(models) < len(colors):
        models.append("HEX")
    if len(models) > len(colors):
        models = models[:len(colors)]
    session["color_models"] = models

    if not colors:
        return Div(
            "No colors recognized yet.", 
            id="color-list-container", 
            style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;"
        )
    
    rows = []
    for i, clean_hex in enumerate(colors):
        name = get_color_name(clean_hex)
        b_hex = base_colors[i] if i < len(base_colors) else clean_hex
        off = offsets[i] if i < len(offsets) else 0
        is_on = enabled[i] if i < len(enabled) else True
        c_model = models[i] if i < len(models) else "HEX"
        rows.append(ColorRow(clean_hex, name, index=i, current_offset=off, base_hex=b_hex, is_enabled=is_on, model=c_model))
    return Div(*rows, id="color-list-container", cls="color-list")

def get_status_bar(session):
    """Generate dynamic status bar text and OOB swap div."""
    colors = session.get("colors", [])
    active_colors = get_active_colors(session)
    mode = session.get("workspace_mode", "Palette")
    layout = session.get("layout", "Chips")
    sort = session.get("sort", "Original")
    labels = session.get("labels", ["Color Name", "HEX"])
    labels_str = " + ".join(labels) if labels else "None"
    
    status_text = f"{len(active_colors)} active · {len(colors)} recognized · {mode} ({layout}) · {sort} · [{labels_str}]"
    return Div(status_text, cls="status-bar", id="status-bar", hx_swap_oob="true")

def render_canvas(session):
    """Render the live palette preview canvas (or conversion table if Mode: Convert) for active colors."""
    active_colors = get_active_colors(session)
    mode = session.get("workspace_mode", "Palette")
    
    if not active_colors:
        return Div(
            Div("Your palette will appear here (select colors to display)", cls="canvas-placeholder"), 
            cls="canvas-body", 
            id="canvas-body", 
            hx_swap_oob="true"
        )
    
    sort_mode = session.get("sort", "Original")
    sorted_colors = get_sorted_colors(active_colors, sort_mode)
    
    # If in Convert mode, render the Conversion Table
    if mode == "Convert":
        return ConversionTable(sorted_colors)
        
    # Otherwise render the visual vector SVG palette
    layout = session.get("layout", "Chips")
    labels = session.get("labels", ["Color Name", "HEX"])
    auto_bg = session.get("auto_bg", False)
    
    try:
        renderer = PaletteRenderer(sorted_colors, layout=layout, label_formats=labels)
        if auto_bg:
            bg = maximin_ciede2000_background(sorted_colors)
        else:
            bg = "#FCFBF9"
        svg_xml = renderer.render_svg((1400, 900), background=bg)
        
        return Div(
            NotStr(svg_xml),
            cls="canvas-body", 
            id="canvas-body", 
            hx_swap_oob="true"
        )
    except Exception as e:
        print(f"Render error: {e}")
        return Div(
            Div(f"Render error: {e}", cls="canvas-placeholder"),
            cls="canvas-body", 
            id="canvas-body", 
            hx_swap_oob="true"
        )

# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------

@rt("/")
def get(session, request):
    colors = session.get("colors", [])
    canvas_div = render_canvas(session)
    canvas_div.attrs.pop("hx_swap_oob", None)
    
    mode = session.get("workspace_mode", "Palette")
    layout = session.get("layout", "Chips")
    sort = session.get("sort", "Original")
    labels = session.get("labels", ["Color Name", "HEX"])
    labels_str = " + ".join(labels) if labels else "None"
    status_text = f"{len(colors)} active · {len(colors)} recognized · {mode} ({layout}) · {sort} · [{labels_str}]"
    
    return Title("PaletteLab"), Layout(render_color_list(session), canvas_div, status_text, mode, layout, sort, labels)

@rt("/api/extract", methods=["POST"])
async def extract(session, request):
    form = await request.form()
    text_input = form.get("text_input", "")
    enabled_formats = form.getlist("formats") or ["HEX"]
    
    if not text_input or not text_input.strip():
        return render_color_list(session), render_canvas(session), get_status_bar(session)
    
    extracted_hexes = []
    extracted_models = []
    for fmt in enabled_formats:
        parser = PARSERS.get(fmt)
        if parser:
            try:
                results = parser(text_input)
                for h in results:
                    clean = normalize_hex(h)
                    if clean and clean not in extracted_hexes:
                        extracted_hexes.append(clean)
                        extracted_models.append(fmt)
            except Exception as e:
                print(f"Parser {fmt} error: {e}")
                
    if extracted_hexes:
        colors = session.get("colors", [])
        base_colors = session.get("base_colors", [])
        offsets = session.get("color_offsets", [])
        enabled = session.get("color_enabled", [])
        models = session.get("color_models", [])
        for h, m in zip(extracted_hexes, extracted_models):
            if h not in colors:
                colors.append(h)
                base_colors.append(h)
                offsets.append(0)
                enabled.append(True)
                models.append(m)
        session["colors"] = colors
        session["base_colors"] = base_colors
        session["color_offsets"] = offsets
        session["color_enabled"] = enabled
        session["color_models"] = models
    
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/clear", methods=["POST"])
def clear(session):
    session["colors"] = []
    session["base_colors"] = []
    session["color_offsets"] = []
    session["color_enabled"] = []
    session["color_models"] = []
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/delete", methods=["POST"])
def delete_color(session, index: int):
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    enabled = session.get("color_enabled", [])
    models = session.get("color_models", [])
    if 0 <= index < len(colors):
        colors.pop(index)
        if index < len(base_colors): base_colors.pop(index)
        if index < len(offsets): offsets.pop(index)
        if index < len(enabled): enabled.pop(index)
        if index < len(models): models.pop(index)
        session["colors"] = colors
        session["base_colors"] = base_colors
        session["color_offsets"] = offsets
        session["color_enabled"] = enabled
        session["color_models"] = models
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/shade", methods=["POST"])
def shade_color(session, index: int, offset: float):
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    
    while len(base_colors) < len(colors):
        base_colors.append(colors[len(base_colors)])
    while len(offsets) < len(colors):
        offsets.append(0)
        
    if 0 <= index < len(colors):
        base = base_colors[index]
        new_hex = apply_shade(base, float(offset))
        colors[index] = new_hex
        offsets[index] = int(float(offset) * 100 if -1.0 <= float(offset) <= 1.0 and float(offset) != 0 else float(offset))
        session["colors"] = colors
        session["base_colors"] = base_colors
        session["color_offsets"] = offsets
        
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/shade-reset", methods=["POST"])
def shade_reset(session, index: int):
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    
    if 0 <= index < len(colors) and index < len(base_colors):
        colors[index] = base_colors[index]
        if index < len(offsets):
            offsets[index] = 0
        session["colors"] = colors
        session["color_offsets"] = offsets
        
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/move-up", methods=["POST"])
def move_up(session, index: int):
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    enabled = session.get("color_enabled", [])
    models = session.get("color_models", [])
    if 0 < index < len(colors):
        colors[index - 1], colors[index] = colors[index], colors[index - 1]
        if index < len(base_colors):
            base_colors[index - 1], base_colors[index] = base_colors[index], base_colors[index - 1]
        if index < len(offsets):
            offsets[index - 1], offsets[index] = offsets[index], offsets[index - 1]
        if index < len(enabled):
            enabled[index - 1], enabled[index] = enabled[index], enabled[index - 1]
        if index < len(models):
            models[index - 1], models[index] = models[index], models[index - 1]
        session["colors"] = colors
        session["base_colors"] = base_colors
        session["color_offsets"] = offsets
        session["color_enabled"] = enabled
        session["color_models"] = models
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/move-down", methods=["POST"])
def move_down(session, index: int):
    colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    enabled = session.get("color_enabled", [])
    models = session.get("color_models", [])
    if 0 <= index < len(colors) - 1:
        colors[index + 1], colors[index] = colors[index], colors[index + 1]
        if index + 1 < len(base_colors):
            base_colors[index + 1], base_colors[index] = base_colors[index], base_colors[index + 1]
        if index + 1 < len(offsets):
            offsets[index + 1], offsets[index] = offsets[index], offsets[index + 1]
        if index + 1 < len(enabled):
            enabled[index + 1], enabled[index] = enabled[index], enabled[index + 1]
        if index + 1 < len(models):
            models[index + 1], models[index] = models[index], models[index + 1]
        session["colors"] = colors
        session["base_colors"] = base_colors
        session["color_offsets"] = offsets
        session["color_enabled"] = enabled
        session["color_models"] = models
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/random", methods=["POST"])
def random_palette(session):
    import random
    
    try:
        from core_logic.generatePalette.palette_generator import PaletteGenerator
        styles = ["pastel", "vibrant", "muted", "classic", "ancient", "modern", "minimalist"]
        themes = ["any", "earthy", "ocean", "botanical", "romantic", "sunset", "jewel"]
        moods = ["any", "warm", "cool", "neutral"]
        
        chosen_style = random.choice(styles)
        chosen_theme = random.choice(themes)
        chosen_mood = random.choice(moods)
        
        gen = PaletteGenerator()
        palette = gen.generate(count=5, style=chosen_style, theme=chosen_theme, mood=chosen_mood, domain="mixed")
        colors = [c["hex"] for c in palette["colors"]]
    except Exception as e:
        print(f"PaletteGenerator fallback: {e}")
        from core_logic.core.color_utils import hex_from_hsl
        base_h = random.randint(0, 360)
        s = random.randint(45, 85)
        l = random.randint(40, 75)
        colors = [hex_from_hsl((base_h + i * 40) % 360, s, l) for i in range(5)]
        
    session["colors"] = colors
    session["base_colors"] = list(colors)
    session["color_offsets"] = [0] * len(colors)
    session["color_enabled"] = [True] * len(colors)
    session["color_models"] = ["RANDOM"] * len(colors)
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/add-color-modal", methods=["POST"])
def add_color_modal():
    modal_content = ColorPickerModal()
    return modal_content

@rt("/api/extract-photo", methods=["POST"])
async def extract_photo(request):
    try:
        form = await request.form()
        photo = form.get("photo")
        if not photo or not hasattr(photo, 'filename') or not photo.filename:
            return Div(id="modal-container", hx_swap_oob="true")
            
        content = await photo.read()
        import base64
        from PIL import Image
        from core_logic.extraction.photo_extractor import extract_palette_with_positions
        
        img = Image.open(io.BytesIO(content)).convert("RGB")
        extracted = extract_palette_with_positions(img, num_colors=6)
        
        # Downsample preview image to max 800px so base64 payload is compact (<80KB)
        w, h = img.size
        max_dim = 800
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img_preview = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        else:
            img_preview = img
            
        buf = io.BytesIO()
        img_preview.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        modal_content = PhotoExtractModal(img_b64, extracted, filename=photo.filename)
        return modal_content
    except Exception as e:
        print(f"Error in extract_photo: {e}")
        return Div(
            Div(
                Div(
                    H3("Photo Extraction Error", style="margin: 0 0 10px 0; color: #ef4444; font-size: 16px;"),
                    P(f"Could not process image: {str(e)}", style="margin: 0 0 16px 0; font-size: 13px; color: var(--text-main);"),
                    Button("Close", type="button", cls="btn", onclick="window.closeModal()"),
                    style="background: var(--panel-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border-color); max-width: 400px; text-align: center;"
                ),
                style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 1000;"
            ),
            id="modal-container"
        )

@rt("/api/add-colors-bulk", methods=["POST"])
async def add_colors_bulk(session, request):
    form = await request.form()
    colors_str = form.get("colors")
    try:
        colors = json.loads(colors_str.replace("'", '"')) if isinstance(colors_str, str) else colors_str
    except Exception:
        colors = []
        
    session_colors = session.get("colors", [])
    base_colors = session.get("base_colors", [])
    offsets = session.get("color_offsets", [])
    enabled = session.get("color_enabled", [])
    models = session.get("color_models", [])
    for h in colors:
        clean_hex = normalize_hex(h)
        if clean_hex and clean_hex not in session_colors:
            session_colors.append(clean_hex)
            base_colors.append(clean_hex)
            offsets.append(0)
            enabled.append(True)
            models.append("HEX")
    session["colors"] = session_colors
    session["base_colors"] = base_colors
    session["color_offsets"] = offsets
    session["color_enabled"] = enabled
    session["color_models"] = models
    
    # Return updated color list, updated canvas, updated status bar, and clear modal-container OOB
    return (
        render_color_list(session), 
        render_canvas(session), 
        get_status_bar(session),
        Div(id="modal-container", hx_swap_oob="true")
    )

@rt("/api/toggle-color-select", methods=["POST"])
def toggle_color_select(session, index: int):
    colors = session.get("colors", [])
    enabled = session.get("color_enabled", [])
    while len(enabled) < len(colors):
        enabled.append(True)
    if 0 <= index < len(enabled):
        enabled[index] = not enabled[index]
    session["color_enabled"] = enabled
    return render_color_list(session), render_canvas(session), get_status_bar(session)

@rt("/api/update-canvas-settings", methods=["POST"])
async def update_canvas_settings(session, request):
    form = await request.form()
    if "mode" in form:
        session["workspace_mode"] = form.get("mode")
    if "layout" in form:
        session["layout"] = form.get("layout")
    if "sort" in form:
        session["sort"] = form.get("sort")
    
    # Always update labels list from form (or empty if user unchecked all)
    session["labels"] = form.getlist("labels")
    
    if "auto_bg" in form:
        session["auto_bg"] = form.get("auto_bg") == "true"
        
    return render_canvas(session), get_status_bar(session)

@rt("/api/export/png", methods=["GET"])
def export_png(session):
    import time
    colors = get_active_colors(session)
    if not colors:
        return Response(content=b"", media_type="image/png")
        
    layout = session.get("layout", "Chips")
    sort_mode = session.get("sort", "Original")
    labels = session.get("labels", ["Color Name", "HEX"])
    auto_bg = session.get("auto_bg", False)
    
    sorted_colors = get_sorted_colors(colors, sort_mode)
    
    img = render_export_image(sorted_colors, layout=layout, label_formats=labels, auto_background=auto_bg)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG", dpi=(300, 300))
    
    # Format palette_DDHHMMSS
    timestamp = time.strftime("%d%H%M%S")
    filename = f"palette_{timestamp}.png"
    
    return Response(
        content=buffered.getvalue(), 
        media_type="image/png", 
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@rt("/api/export/svg", methods=["GET"])
def export_svg(session):
    import time
    colors = get_active_colors(session)
    if not colors:
        return Response(content=b"", media_type="image/svg+xml")
        
    layout = session.get("layout", "Chips")
    sort_mode = session.get("sort", "Original")
    labels = session.get("labels", ["Color Name", "HEX"])
    auto_bg = session.get("auto_bg", False)
    
    sorted_colors = get_sorted_colors(colors, sort_mode)
    
    renderer = PaletteRenderer(sorted_colors, layout=layout, label_formats=labels)
    if auto_bg:
        bg = maximin_ciede2000_background(sorted_colors)
    else:
        bg = "#FCFBF9"
    svg_data = renderer.render_svg((1400, 1750), background=bg)
    
    # Format palette_DDHHMMSS
    timestamp = time.strftime("%d%H%M%S")
    filename = f"palette_{timestamp}.svg"
    
    return Response(
        content=svg_data.encode('utf-8'), 
        media_type="image/svg+xml", 
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
app = app
if __name__ == "__main__":
    serve()
