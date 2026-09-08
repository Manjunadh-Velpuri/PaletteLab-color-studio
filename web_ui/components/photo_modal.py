"""
Interactive Photo Color Extraction Modal Component.
Displays loaded photo with circular color pins over sampled locations,
real-time color count adjustment (3-12), live swatch chip preview tray,
pin dragging, click-to-add, and double-click to delete.
"""

import json
from fasthtml.common import *

def PhotoExtractModal(img_b64: str, initial_colors: list, filename: str = "photo.jpg"):
    data_json = json.dumps(initial_colors)
    js_logic = f"""
    (function() {{
        const b64 = "data:image/jpeg;base64,{img_b64}";
        const data = {data_json};
        if (window.initPhotoModalCanvas) {{
            window.initPhotoModalCanvas(b64, data);
        }} else {{
            setTimeout(function() {{
                if (window.initPhotoModalCanvas) window.initPhotoModalCanvas(b64, data);
            }}, 50);
        }}
    }})();
    """

    return Div(
        Div(
            Div(
                H2("EXTRACT PALETTE FROM PHOTO", style="font-size: 15px; font-weight: 800; letter-spacing: 0.8px; margin: 0; color: var(--text-main) !important;"),
                Div(filename, style="font-size: 12px; color: var(--text-muted, #888);"),
                Button("✕", type="button", onclick="window.closeModal()", style="background: transparent; border: none; font-size: 16px; font-weight: bold; cursor: pointer; color: var(--text-main) !important;"),
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;"
            ),
            # Photo Canvas (Fixed aspect box)
            Div(
                Canvas(id="photo-modal-canvas", style="border-radius: 8px; cursor: crosshair; display: block; border: 1px solid var(--border-color, #444); max-width: 100%; max-height: 240px; margin: 0 auto;"),
                style="display: flex; justify-content: center; align-items: center; background: #0a0a0a; border-radius: 8px; padding: 6px; margin-bottom: 12px; height: 250px; flex-shrink: 0;"
            ),
            # Stepper & Count Controls
            Div(
                Div("Color Count:", style="font-size: 13px; font-weight: 700; color: var(--text-main) !important;"),
                Button("−", type="button", cls="btn", onclick="_photoDecCount()", style="width: 30px; height: 30px; font-size: 18px; font-weight: 800; padding: 0; display: flex; align-items: center; justify-content: center;"),
                Div(str(len(initial_colors)), id="photo-count-val", style="width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; background: var(--bg-main); color: var(--text-main); border: 1px solid var(--border-color); border-radius: 6px;"),
                Button("+", type="button", cls="btn", onclick="_photoIncCount()", style="width: 30px; height: 30px; font-size: 18px; font-weight: 800; padding: 0; display: flex; align-items: center; justify-content: center;"),
                Div(style="flex-grow: 1;"),
                Div("Click: add · Drag: move · Dbl-click: remove", style="font-size: 11px; color: var(--text-muted, #888);"),
                style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-shrink: 0;"
            ),
            # Chips Tray Area (Fixed height scrollable area)
            Div(
                Div(id="photo-chip-list", style="display: flex; flex-direction: column; gap: 6px; height: 130px; overflow-y: auto; padding-right: 6px;"),
                style="margin-bottom: 14px; flex: 1 1 auto; min-height: 130px;"
            ),
            # Form with hidden colors input for 100% reliable submission
            Form(
                Input(type="hidden", id="photo-colors-input", name="colors", value="[]"),
                Div(
                    Button("Cancel", type="button", cls="btn", onclick="window.closeModal()", style="padding: 8px 18px;"),
                    Div(style="flex-grow: 1;"),
                    Button(
                        f"Extract {len(initial_colors)} Colors", 
                        id="photo-extract-submit-btn", 
                        type="submit", 
                        cls="btn primary", 
                        style="padding: 8px 24px;"
                    ),
                    style="display: flex; align-items: center;"
                ),
                hx_post="/api/add-colors-bulk",
                hx_target="#color-list-container",
                hx_swap="outerHTML"
            ),
            Script(js_logic),
            cls="modal-content",
            style="background: var(--panel-bg) !important; color: var(--text-main) !important; padding: 20px; border-radius: 14px; width: 640px; height: 560px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column; border: 1px solid var(--border-color) !important; box-shadow: 0 16px 48px rgba(0,0,0,0.5);"
        ),
        id="modal-container",
        cls="modal-backdrop",
        style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 1000;"
    )
