"""
Interactive Color Model Conversions Table Component for PaletteLab Web.
Faithfully supports:
- Dynamic per-row color matching background with high contrast text.
- Full row/column selection system:
  - Column checkboxes in header to toggle entire column selection.
  - Per-cell checkboxes for individual format/color selection.
  - Color Name, HEX, RGB, HSL, HSV, CMYK, LAB color model support.
  - Copy Selected button formatting: each color's selected conversions in a single row, next color in next row.
"""

from fasthtml.common import *
from core_logic.core.color_utils import (
    get_color_name, format_rgb, format_hsl, format_hsv, format_cmyk, format_lab,
    rgb_from_hex, relative_luminance, contrast_text
)

def ConversionTable(colors: list):
    if not colors:
        return Div(
            Div("No colors to convert. Add or extract colors first.", cls="canvas-placeholder"),
            cls="canvas-body",
            id="canvas-body",
            hx_swap_oob="true"
        )
    
    table_rows = []
    for i, c_hex in enumerate(colors):
        name = get_color_name(c_hex)
        rgb = format_rgb(c_hex)
        hsl = format_hsl(c_hex)
        hsv = format_hsv(c_hex)
        cmyk = format_cmyk(c_hex)
        lab = format_lab(c_hex)
        
        # Dynamic solid color row matching the swatch, with high contrast text
        text_color = contrast_text(c_hex)
        row_bg = c_hex
        sub_color = "rgba(17, 17, 17, 0.82)" if text_color == "#111111" else "rgba(255, 255, 255, 0.82)"
        
        row = Tr(
            # 1. Color Swatch & HEX
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-hex", checked=True, **{"data-col": "hex", "data-val": c_hex}, onchange="onCellCheckChange()"),
                    Div(style=f"background-color: {c_hex}; width: 22px; height: 22px; border-radius: 4px; border: 2px solid {'#111111' if text_color == '#111111' else '#FFFFFF'}; flex: 0 0 auto; box-shadow: 0 1px 3px rgba(0,0,0,0.25);"),
                    Span(c_hex, style=f"font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 13px; color: {text_color};"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; font-weight: 600; background-color: {row_bg} !important;"
            ),
            # 2. Color Name
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-name", checked=True, **{"data-col": "name", "data-val": name}, onchange="onCellCheckChange()"),
                    Span(name, style=f"font-size: 13px; font-weight: 700; color: {text_color}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            # 3. RGB
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-rgb", checked=True, **{"data-col": "rgb", "data-val": rgb}, onchange="onCellCheckChange()"),
                    Code(rgb, style=f"font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {sub_color}; background: transparent;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            # 4. HSL
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-hsl", checked=True, **{"data-col": "hsl", "data-val": hsl}, onchange="onCellCheckChange()"),
                    Code(hsl, style=f"font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {sub_color}; background: transparent;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            # 5. HSV
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-hsv", checked=True, **{"data-col": "hsv", "data-val": hsv}, onchange="onCellCheckChange()"),
                    Code(hsv, style=f"font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {sub_color}; background: transparent;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            # 6. CMYK
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-cmyk", checked=True, **{"data-col": "cmyk", "data-val": cmyk}, onchange="onCellCheckChange()"),
                    Code(cmyk, style=f"font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {sub_color}; background: transparent;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            # 7. LAB
            Td(
                Div(
                    Input(type="checkbox", cls="conv-cell-check col-lab", checked=True, **{"data-col": "lab", "data-val": lab}, onchange="onCellCheckChange()"),
                    Code(lab, style=f"font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {sub_color}; background: transparent;"),
                    style="display: flex; gap: 8px; align-items: center;"
                ),
                style=f"padding: 10px 12px; background-color: {row_bg} !important;"
            ),
            cls="conversion-row",
            style=f"background-color: {row_bg} !important; border-bottom: 1px solid rgba(255,255,255,0.18); transition: filter 0.15s;"
        )
        table_rows.append(row)

    table_widget = Div(
        Div(
            # Top title and Copy button
            Div(
                H3("COLOR MODEL CONVERSIONS", style="font-size: 13px; font-weight: 800; letter-spacing: 0.8px; margin: 0; color: var(--text-main);"),
                Button("Copy Selected Conversions", type="button", cls="btn primary", id="copy-conversions-btn", onclick="copyConversionTable()", style="padding: 6px 14px; font-size: 11px; font-weight: 700;"),
                style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--border-color); background: var(--bg-main);"
            ),
            # Scrollable Table Container
            Div(
                Table(
                    Thead(
                        Tr(
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('hex', this.checked)"), " HEX", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('name', this.checked)"), " Name", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('rgb', this.checked)"), " RGB", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('hsl', this.checked)"), " HSL", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('hsv', this.checked)"), " HSV", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('cmyk', this.checked)"), " CMYK", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            Th(
                                Label(Input(type="checkbox", cls="col-header-check", checked=True, onchange="toggleColumnCheck('lab', this.checked)"), " LAB", style="display: flex; gap: 6px; align-items: center; cursor: pointer; color: var(--text-main) !important; font-weight: 700;"),
                                style="text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 700; color: var(--text-main) !important; background-color: var(--panel-bg) !important; border-bottom: 2px solid var(--border-color);"
                            ),
                            style="background-color: var(--panel-bg) !important;"
                        )
                    ),
                    Tbody(*table_rows),
                    style="width: 100%; border-collapse: collapse;"
                ),
                style="overflow-y: auto; flex-grow: 1; min-height: 0;"
            ),
            style="width: 100%; height: 100%; display: flex; flex-direction: column; background: var(--panel-bg); border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm);"
        ),
        style="width: 100%; height: 100%; padding: 12px; display: flex; flex-direction: column; overflow: hidden;"
    )

    return Div(
        table_widget,
        cls="canvas-body",
        id="canvas-body",
        hx_swap_oob="true"
    )
