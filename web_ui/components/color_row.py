from fasthtml.common import *
from core_logic.core.color_utils import (
    rgb_from_hex, hsl_from_hex, hsv_from_hex, cmyk_from_hex, lab_from_hex
)

def format_color_for_display(hex_val: str, model: str) -> str:
    """Format the hex color into its original recognized model format."""
    if model == "RGB":
        r, g, b = rgb_from_hex(hex_val)
        return f"rgb({r},{g},{b})"
    elif model == "HSL":
        h, s, l = hsl_from_hex(hex_val)
        return f"hsl({round(h)},{round(s)}%,{round(l)}%)"
    elif model == "HSV":
        h, s, v = hsv_from_hex(hex_val)
        return f"hsv({round(h)},{round(s)}%,{round(v)}%)"
    elif model == "CMYK":
        c, m, y, k = cmyk_from_hex(hex_val)
        return f"cmyk({round(c)}%,{round(m)}%,{round(y)}%,{round(k)}%)"
    elif model == "LAB":
        l, a, b = lab_from_hex(hex_val)
        return f"lab({round(l)},{round(a)},{round(b)})"
    return hex_val

def ColorRow(hex_val: str, name: str, index: int = 0, current_offset: int = 0, base_hex: str = None, is_enabled: bool = True, model: str = "HEX"):
    """Returns an HTMX element representing a color row with selection checkbox, live tooltip slider and reset button."""
    if base_hex is None:
        base_hex = hex_val

    # Selection checkbox (enables/disables inclusion in palette rendering and conversion table)
    enable_check = Input(
        type="checkbox",
        checked=is_enabled,
        cls="color-select-check",
        title="Include / Exclude from palette & conversion",
        style="cursor: pointer; width: 14px; height: 14px; flex: 0 0 auto; margin: 0 2px;",
        hx_post=f"/api/toggle-color-select?index={index}",
        hx_target="#color-list-container",
        hx_swap="outerHTML"
    )

    # Minimalist shade slider with live tooltip number, center thumb indicator, and CIELCH live sync
    shade_slider = Div(
        Input(
            type="range", 
            min="-100", max="100", step="1", value=str(current_offset),
            name="offset",
            cls="shade-slider",
            oninput="""
            const val = parseInt(this.value);
            const badge = this.parentElement.querySelector('.slider-badge');
            if (badge) {
                badge.textContent = (val > 0 ? '+' : '') + val;
                badge.style.opacity = '1';
                badge.style.left = (50 + val * 0.42) + '%';
            }
            """,
            onmousedown="const b = this.parentElement.querySelector('.slider-badge'); if (b) b.style.opacity = '1';",
            onmouseup="const b = this.parentElement.querySelector('.slider-badge'); if (b) b.style.opacity = '0';",
            ontouchstart="const b = this.parentElement.querySelector('.slider-badge'); if (b) b.style.opacity = '1';",
            ontouchend="const b = this.parentElement.querySelector('.slider-badge'); if (b) b.style.opacity = '0';",
            hx_post=f"/api/shade?index={index}",
            hx_trigger="change",
            hx_target="#color-list-container",
            hx_swap="outerHTML"
        ),
        # Center anchor tick (0 mark)
        Div(
            style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 2px; height: 7px; background: var(--border-color); border-radius: 1px; pointer-events: none; opacity: 0.85; z-index: 1;"
        ),
        Div(
            (f"+{current_offset}" if current_offset > 0 else str(current_offset)),
            cls="slider-badge",
            style=f"opacity: 0; position: absolute; top: -16px; left: {50 + current_offset * 0.42}%; transform: translateX(-50%); font-size: 10px; font-weight: 700; font-family: 'JetBrains Mono', monospace; background: var(--panel-bg); color: var(--text-main); padding: 1px 4px; border-radius: 3px; border: 1px solid var(--border-color); pointer-events: none; transition: opacity 0.15s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.15); z-index: 10;"
        ),
        style="position: relative; display: flex; align-items: center; width: 75px; flex: 0 0 75px; margin: 0 2px;"
    )
    
    # Reset button (reverts slider to 0 and color to base_hex)
    reset_btn = Button(
        "↺", type="button", cls="btn reset-shade-btn",
        title="Reset to original color (0)",
        style="padding: 1px 4px; font-size: 11px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; line-height: 1; flex: 0 0 auto;",
        hx_post=f"/api/shade-reset?index={index}",
        hx_target="#color-list-container",
        hx_swap="outerHTML"
    )

    # Move buttons
    move_up_btn = Button(
        "▲", type="button", cls="btn",
        style="padding: 2px 4px; font-size: 10px; border: none; background: transparent; color: var(--text-muted); cursor: pointer;",
        hx_post=f"/api/move-up?index={index}", hx_target="#color-list-container", hx_swap="outerHTML"
    )
    move_down_btn = Button(
        "▼", type="button", cls="btn",
        style="padding: 2px 4px; font-size: 10px; border: none; background: transparent; color: var(--text-muted); cursor: pointer;",
        hx_post=f"/api/move-down?index={index}", hx_target="#color-list-container", hx_swap="outerHTML"
    )

    # Delete button
    delete_btn = Button(
        "✕", type="button", cls="btn", 
        style="padding: 4px 6px; border: none; background: transparent; color: var(--text-muted); cursor: pointer;",
        hx_post=f"/api/delete?index={index}", hx_target="#color-list-container", hx_swap="outerHTML"
    )

    row_opacity = "1" if is_enabled else "0.45"
    display_code = format_color_for_display(hex_val, model)

    return Div(
        enable_check,
        Div(style=f"background-color: {hex_val};", cls="color-swatch"),
        Div(
            Div(display_code, cls="color-hex", style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"),
            Div(name, cls="color-name", style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"),
            Div(model, style="font-size: 9px; font-weight: 700; color: var(--text-muted); margin-top: 2px; text-align: left;"),
            cls="color-info",
            style="flex-grow: 1; min-width: 0; overflow: hidden;"
        ),
        shade_slider,
        reset_btn,
        Div(
            move_up_btn, move_down_btn,
            style="display: flex; flex-direction: column; gap: 2px; flex: 0 0 auto;"
        ),
        delete_btn,
        cls="color-row",
        style=f"opacity: {row_opacity}; transition: opacity 0.2s ease;",
        **{"data-index": str(index), "data-hex": hex_val}
    )
