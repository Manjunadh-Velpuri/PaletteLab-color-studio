"""
PaletteLab Web UI Dashboard Layout Component.
"""

from fasthtml.common import *
import os
from web_ui.theme_loader import get_theme_list

def Icon(name, size=16, cls=""):
    try:
        path = os.path.join('static', 'icons', f"{name}.svg")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                svg = f.read()
                svg = svg.replace('<svg ', f'<svg width="{size}" height="{size}" class="{cls}" ')
                return NotStr(svg)
    except Exception:
        pass
    return ""

def TopBar():
    theme_categories = get_theme_list()
    optgroups = []
    for cat in theme_categories:
        options = [Option(t["name"], value=t["slug"]) for t in cat["themes"]]
        optgroups.append(Optgroup(*options, label=cat["category"]))
    
    return Div(
        Div(
            H1("PALETTE LAB", cls="logo"),
            Div("Extract · Refine · Compose", cls="subtitle"),
            style="display: flex; flex-direction: column;"
        ),
        Div(
            Select(
                *optgroups,
                cls="canvas-select", 
                id="theme-selector", 
                style="width: 220px; font-size: 12px;"
            ),
            Button(Icon('sun', 16), type="button", cls="btn mode-toggle-btn", id="theme-light-btn", title="Light Mode", style="padding: 6px 10px; display: flex; align-items: center; justify-content: center;"),
            Button(Icon('moon', 16), type="button", cls="btn mode-toggle-btn", id="theme-dark-btn", title="Dark Mode", style="padding: 6px 10px; display: flex; align-items: center; justify-content: center;"),
            cls="top-bar-right"
        ),
        cls="top-bar"
    )



def InputSection():
    formats = ["HEX", "RGB", "HSL", "HSV", "CMYK", "LAB"]
    checkboxes = [
        Label(Input(type="checkbox", checked=(f == "HEX"), name="formats", value=f), f" {f}")
        for f in formats
    ]
    
    return Div(
        Form(
            Div(
                Textarea(
                    name="text_input", 
                    id="raw-text-input",
                    placeholder="Paste text containing #HEX, RGB, HSL, HSV, CMYK, or LAB colors here...", 
                    rows=3
                ),
                Div(
                    Span("Parse Formats:", style="font-weight: 700; color: var(--text-muted); margin-right: 4px; font-size: 11px;"),
                    *checkboxes, 
                    cls="format-checkboxes"
                ),
                cls="text-area-container"
            ),
            hx_post="/api/extract",
            hx_target="#color-list-container",
            hx_swap="outerHTML",
            id="extract-form",
            style="flex-grow: 1; display: flex;"
        ),
        Div(
            Button(Icon('magic-wand', size=13), " Extract Ctrl+Enter", type="submit", form="extract-form", cls="btn primary"),
            Button(Icon('reload', size=13), " Random Palette", type="button", cls="btn", hx_post="/api/random", hx_target="#color-list-container", hx_swap="outerHTML"),
            Button(
                Icon('plus', size=13), " 2D Add Color", type="button", hx_post="/api/add-color-modal", hx_target="#modal-container", hx_swap="outerHTML",
                cls="btn"
            ),
            Label(
                Icon('image', size=13), " Photo Extract",
                Input(
                    type="file", 
                    accept="image/*", 
                    name="photo", 
                    id="photo-file-input",
                    onclick="this.value=null;",
                    onchange="if(window.handlePhotoUpload) window.handlePhotoUpload(this);",
                    style="position: absolute; opacity: 0; width: 0; height: 0;"
                ),
                cls="btn", style="cursor: pointer; position: relative;"
            ),
            cls="action-buttons"
        ),
        cls="input-section"
    )

def Sidebar(color_list_component=None):
    if color_list_component is None:
        color_list_component = Div("No colors recognized yet.", id="color-list-container", style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;")
        
    return Div(
        Div("RECOGNIZED COLORS", cls="sidebar-header"),
        color_list_component,
        Div(
            Button(Icon('copy', 14), " Copy HEX", type="button", cls="btn", id="copy-hex-btn", onclick="copyAllHexes()", style="display: flex; gap: 6px; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;"),
            Button(Icon('trash', 14), " Clear", type="button", cls="btn", hx_post="/api/clear", hx_target="#color-list-container", hx_swap="outerHTML", style="display: flex; gap: 6px; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #f87171;"),
            cls="sidebar-footer"
        ),
        cls="sidebar"
    )

def CanvasArea(canvas_component=None):
    if canvas_component is None:
        canvas_component = Div(
            Div("Your palette will appear here", cls="canvas-placeholder"),
            cls="canvas-body", 
            id="canvas-body"
        )
        
    layout_options = [
        Option("Chips", value="Chips", selected=True),
        Option("Pillars", value="Pillars"),
        Option("Orbs", value="Orbs"),
        Option("Ribbons", value="Ribbons"),
        Option("Collage", value="Collage"),
        Option("Honeycomb", value="Honeycomb"),
        Option("Canvas", value="Canvas"),
        Option("Blocks", value="Blocks")
    ]

    sort_options = [
        Option("Sort: Original", value="Original", selected=True),
        Option("Sort: Luminance (High → Low)", value="Luminance_Desc"),
        Option("Sort: Luminance (Low → High)", value="Luminance_Asc"),
        Option("Sort: Hue (Rainbow)", value="Hue"),
        Option("Sort: Saturation", value="Saturation")
    ]

    variant_options = [
        Option("Mode: Palette", value="Palette", selected=True),
        Option("Mode: Convert", value="Convert")
    ]

    label_checkboxes = [
        Label(Input(type="checkbox", checked=True, name="labels", value="Color Name", onchange="updateCanvasSettings()"), " Color Name"),
        Label(Input(type="checkbox", checked=True, name="labels", value="HEX", onchange="updateCanvasSettings()"), " HEX"),
        Label(Input(type="checkbox", name="labels", value="RGB", onchange="updateCanvasSettings()"), " RGB"),
        Label(Input(type="checkbox", name="labels", value="HSL", onchange="updateCanvasSettings()"), " HSL"),
        Label(Input(type="checkbox", name="labels", value="HSV", onchange="updateCanvasSettings()"), " HSV"),
        Label(Input(type="checkbox", name="labels", value="CMYK", onchange="updateCanvasSettings()"), " CMYK"),
        Label(Input(type="checkbox", name="labels", value="LAB", onchange="updateCanvasSettings()"), " LAB"),
    ]
        
    return Div(
        # Toolbar Row 1
        Div(
            Div(
                Select(*variant_options, id="workspace-mode-select", cls="canvas-select", style="width: 140px;", onchange="updateCanvasSettings()"),
                Select(*layout_options, id="layout-select", cls="canvas-select", style="width: 145px;", onchange="updateCanvasSettings()"),
                Select(*sort_options, id="sort-select", cls="canvas-select", style="width: 215px;", onchange="updateCanvasSettings()"),
                Button(Icon('reload', 14), type="button", cls="btn", title="Refresh palette preview", onclick="updateCanvasSettings()", style="padding: 6px 10px; display: flex; align-items: center; justify-content: center;"),
                Div("⭐ Pro-tip: PNG export is more beautiful than this UI display!", cls="canvas-protip"),
                cls="canvas-tools-left"
            ),
            Div(
                A(Icon('download', 14), " Save PNG", href="/api/export/png", id="save-png-btn", target="_blank", cls="btn primary", style="display: flex; gap: 6px; align-items: center; text-decoration: none; padding: 6px 14px; font-size: 12px; font-weight: 700;"),
                A(Icon('download', 14), " Save SVG", href="/api/export/svg", id="save-svg-btn", target="_blank", cls="btn primary", style="display: flex; gap: 6px; align-items: center; text-decoration: none; padding: 6px 14px; font-size: 12px; font-weight: 700;"),
                cls="canvas-tools-right"
            ),
            cls="canvas-toolbar"
        ),
        # Toolbar Row 2: Display Labels Checkboxes
        Div(
            Span("Display Labels (Max 2):", style="font-weight: 700; color: var(--text-muted); margin-right: 6px; font-size: 12px;"),
            *label_checkboxes,
            cls="canvas-display-options",
            id="display-labels-container"
        ),
        # Canvas Live SVG/PNG Body
        canvas_component,
        # Footer
        Div(
            Div("⭐ Pro tip: PNG export is more beautiful than this UI display!", style="font-size: 11px; color: var(--text-muted); font-weight: 500;"),
            Div(
                Label(Input(type="checkbox", id="auto-bg-check", onchange="updateCanvasSettings()"), " Auto background"),
                style="display: flex; gap: 14px; font-size: 12px; font-weight: 500;"
            ),
            cls="canvas-footer"
        ),
        cls="canvas-area"
    )

def Layout(color_list_component=None, canvas_component=None, status_text="0 active · 0 recognized · Palette (Chips) · Original · [Color Name + HEX]"):
    return Div(
        TopBar(),
        InputSection(),
        Div(
            Sidebar(color_list_component),
            CanvasArea(canvas_component),
            cls="workspace"
        ),
        Div(status_text, cls="status-bar", id="status-bar"),
        Div(id="modal-container"),
        cls="dashboard"
    )
