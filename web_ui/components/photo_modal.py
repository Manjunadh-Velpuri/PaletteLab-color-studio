"""
Interactive Photo Color Extraction Modal Component.
Displays loaded photo with circular color pins over sampled locations,
real-time color count adjustment (3-12), live swatch chip preview tray,
pin dragging, click-to-add, and double-click to delete.
"""

import json
from fasthtml.common import *

def PhotoExtractModal(img_b64: str, initial_colors: list, filename: str = "photo.jpg"):
    js_logic = f"""
    (function() {{
        const imgB64 = "data:image/png;base64,{img_b64}";
        let initialData = {json.dumps(initial_colors)};
        let numColors = initialData.length || 6;
        
        const canvas = document.getElementById('photo-modal-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const countValLbl = document.getElementById('photo-count-val');
        const chipContainer = document.getElementById('photo-chip-list');
        const extractBtn = document.getElementById('photo-extract-submit-btn');

        const img = new Image();
        img.src = imgB64;

        let points = []; // [{{hex: string, rel_x: float, rel_y: float}}]
        let draggingIdx = null;

        img.onload = function() {{
            // Calculate fit inside canvas box (max width 580, max height 320)
            const maxW = 580;
            const maxH = 300;
            let w = img.width;
            let h = img.height;
            const ratio = Math.min(maxW / w, maxH / h, 1.0);
            canvas.width = Math.round(w * ratio);
            canvas.height = Math.round(h * ratio);

            // Populate initial points
            points = initialData.map(p => ({{
                hex: p.hex,
                rel_x: p.rel_x,
                rel_y: p.rel_y
            }}));

            drawCanvas();
            updateUI();
        }};

        function samplePixelHex(x, y) {{
            x = Math.max(0, Math.min(canvas.width - 1, Math.round(x)));
            y = Math.max(0, Math.min(canvas.height - 1, Math.round(y)));
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            return "#" + (1 << 24 | pixel[0] << 16 | pixel[1] << 8 | pixel[2]).toString(16).slice(1).toUpperCase();
        }}

        function drawCanvas() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            // Resample all point hexes directly from the rendered image canvas
            const w = canvas.width;
            const h = canvas.height;
            points.forEach(p => {{
                p.hex = samplePixelHex(p.rel_x * w, p.rel_y * h);
            }});

            // Draw pins
            points.forEach((p, idx) => {{
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const isDragging = (draggingIdx === idx);

                // If dragging, draw a 3x magnified loupe lens above the cursor
                if (isDragging) {{
                    const loupeR = 24;
                    const loupeY = py - 36;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(px, loupeY, loupeR, 0, Math.PI * 2);
                    ctx.clip();
                    // Draw 3x zoomed image crop
                    const zoomSize = 16;
                    ctx.drawImage(canvas, px - zoomSize / 2, py - zoomSize / 2, zoomSize, zoomSize, px - loupeR, loupeY - loupeR, loupeR * 2, loupeR * 2);
                    ctx.restore();

                    // Loupe ring
                    ctx.beginPath();
                    ctx.arc(px, loupeY, loupeR, 0, Math.PI * 2);
                    ctx.lineWidth = 3;
                    ctx.strokeStyle = '#FFFFFF';
                    ctx.stroke();
                    ctx.lineWidth = 1;
                    ctx.strokeStyle = 'rgba(0,0,0,0.6)';
                    ctx.stroke();

                    // Center crosshair inside loupe
                    ctx.beginPath();
                    ctx.arc(px, loupeY, 2, 0, Math.PI * 2);
                    ctx.fillStyle = '#FF0000';
                    ctx.fill();
                }}

                // Outer black shadow ring
                ctx.beginPath();
                ctx.arc(px, py, 11, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(0,0,0,0.7)';
                ctx.lineWidth = 3;
                ctx.stroke();

                // White outer ring with color fill
                ctx.beginPath();
                ctx.arc(px, py, 9, 0, Math.PI * 2);
                ctx.fillStyle = p.hex;
                ctx.fill();
                ctx.strokeStyle = '#FFFFFF';
                ctx.lineWidth = 2;
                ctx.stroke();

                // Center contrast dot
                ctx.beginPath();
                ctx.arc(px, py, 2, 0, Math.PI * 2);
                ctx.fillStyle = '#FFFFFF';
                ctx.fill();
            }});
        }}

        function updateUI() {{
            countValLbl.textContent = points.length.toString();
            extractBtn.textContent = points.length > 0 ? `Extract ${{points.length}} Colors` : 'Extract Colors';

            chipContainer.innerHTML = '';
            points.forEach((p, idx) => {{
                const chip = document.createElement('div');
                chip.style.display = 'flex';
                chip.style.alignItems = 'center';
                chip.style.justifyContent = 'space-between';
                chip.style.padding = '6px 12px';
                chip.style.backgroundColor = 'var(--bg-main, #222)';
                chip.style.border = '1px solid var(--border-color, #444)';
                chip.style.borderRadius = '6px';
                chip.style.gap = '12px';

                const left = document.createElement('div');
                left.style.display = 'flex';
                left.style.alignItems = 'center';
                left.style.gap = '10px';

                const swatch = document.createElement('div');
                swatch.style.width = '24px';
                swatch.style.height = '24px';
                swatch.style.borderRadius = '4px';
                swatch.style.backgroundColor = p.hex;
                swatch.style.border = '1px solid rgba(255,255,255,0.2)';

                const lbl = document.createElement('span');
                lbl.textContent = p.hex;
                lbl.style.fontFamily = 'monospace';
                lbl.style.fontWeight = '700';
                lbl.style.fontSize = '14px';

                left.appendChild(swatch);
                left.appendChild(lbl);

                const delBtn = document.createElement('button');
                delBtn.textContent = '✕';
                delBtn.style.background = 'transparent';
                delBtn.style.border = 'none';
                delBtn.style.color = '#ef4444';
                delBtn.style.cursor = 'pointer';
                delBtn.style.fontSize = '14px';
                delBtn.style.fontWeight = 'bold';
                delBtn.onclick = () => {{
                    points.splice(idx, 1);
                    drawCanvas();
                    updateUI();
                }};

                chip.appendChild(left);
                chip.appendChild(delBtn);
                chipContainer.appendChild(chip);
            }});

            const hexes = points.map(p => p.hex);
            const hiddenInput = document.getElementById('photo-colors-input');
            if (hiddenInput) {{
                hiddenInput.value = JSON.stringify(hexes);
            }}
            extractBtn.setAttribute('hx-vals', JSON.stringify({{ "colors": hexes }}));
            if (window.htmx) htmx.process(extractBtn);
        }}

        function getCanvasCoords(e) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / (rect.width || 1);
            const scaleY = canvas.height / (rect.height || 1);
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            return {{
                x: Math.max(0, Math.min(canvas.width, x)),
                y: Math.max(0, Math.min(canvas.height, y))
            }};
        }}

        canvas.ondragstart = function(e) {{
            e.preventDefault();
            return false;
        }};

        canvas.onmousedown = function(e) {{
            e.preventDefault();
            e.stopPropagation();
            const coords = getCanvasCoords(e);
            const x = coords.x;
            const y = coords.y;
            const w = canvas.width;
            const h = canvas.height;

            let clickedIdx = null;
            let minDist = Infinity;
            points.forEach((p, idx) => {{
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const dist = Math.hypot(px - x, py - y);
                if (dist <= 22 && dist < minDist) {{
                    minDist = dist;
                    clickedIdx = idx;
                }}
            }});

            if (clickedIdx !== null) {{
                draggingIdx = clickedIdx;
            }} else {{
                const rel_x = x / w;
                const rel_y = y / h;
                const hex = samplePixelHex(x, y);
                points.push({{ hex, rel_x, rel_y }});
                draggingIdx = points.length - 1;
            }}
            drawCanvas();
            updateUI();
        }};

        canvas.ondblclick = function(e) {{
            e.preventDefault();
            e.stopPropagation();
            const coords = getCanvasCoords(e);
            const x = coords.x;
            const y = coords.y;
            const w = canvas.width;
            const h = canvas.height;

            let targetIdx = null;
            let minDist = Infinity;
            points.forEach((p, idx) => {{
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const dist = Math.hypot(px - x, py - y);
                if (dist <= 24 && dist < minDist) {{
                    minDist = dist;
                    targetIdx = idx;
                }}
            }});

            if (targetIdx !== null) {{
                points.splice(targetIdx, 1);
                draggingIdx = null;
                drawCanvas();
                updateUI();
            }}
        }};

        window.addEventListener('mousemove', function(e) {{
            if (draggingIdx === null) return;
            const coords = getCanvasCoords(e);
            const rel_x = coords.x / canvas.width;
            const rel_y = coords.y / canvas.height;
            points[draggingIdx].rel_x = rel_x;
            points[draggingIdx].rel_y = rel_y;
            points[draggingIdx].hex = samplePixelHex(coords.x, coords.y);
            drawCanvas();
            updateUI();
        }});

        window.addEventListener('mouseup', function() {{
            if (draggingIdx !== null) {{
                draggingIdx = null;
                drawCanvas();
            }}
        }});

        window._photoDecCount = function() {{
            if (points.length > 0) {{
                points.pop();
                drawCanvas();
                updateUI();
            }}
        }};

        window._photoIncCount = function() {{
            if (points.length < 16) {{
                const rel_x = Math.random() * 0.8 + 0.1;
                const rel_y = Math.random() * 0.8 + 0.1;
                const hex = samplePixelHex(rel_x * canvas.width, rel_y * canvas.height);
                points.push({{ hex, rel_x, rel_y }});
                drawCanvas();
                updateUI();
            }}
        }};
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
