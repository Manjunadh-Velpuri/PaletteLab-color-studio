"""
2D Color Spectrum Add Colors Modal Component.
Supports HSV-based 2D spectrum, point dropping, dragging, double-click removal, quick harmony presets, and scrollable chip tray.
"""

from fasthtml.common import *

def ColorPickerModal():
    js_logic = """
    (function() {
        const canvas = document.getElementById('spectrum-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const countLbl = document.getElementById('dropped-count-lbl');
        const chipContainer = document.getElementById('spectrum-chip-list');
        const addBtn = document.getElementById('add-spectrum-colors-btn');
        
        let points = []; // [{hex: string, rel_x: float, rel_y: float}]
        let draggingIdx = null;

        // HSV to RGB conversion matching standalone app
        function hsvToRgb(h, s, v) {
            let r, g, b;
            let i = Math.floor(h * 6);
            let f = h * 6 - i;
            let p = v * (1 - s);
            let q = v * (1 - f * s);
            let t = v * (1 - (1 - f) * s);
            switch (i % 6) {
                case 0: r = v; g = t; b = p; break;
                case 1: r = q; g = v; b = p; break;
                case 2: r = p; g = v; b = t; break;
                case 3: r = p; g = q; b = v; break;
                case 4: r = t; g = p; b = v; break;
                case 5: r = v; g = p; b = q; break;
            }
            return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
        }

        function colorAtRel(rel_x, rel_y) {
            rel_x = Math.max(0, Math.min(1, rel_x));
            rel_y = Math.max(0, Math.min(1, rel_y));
            const hue = rel_x;
            let sat, val;
            if (rel_y <= 0.5) {
                sat = 0.15 + rel_y * 1.70;
                val = 1.0;
            } else {
                sat = 1.0;
                val = 1.0 - (rel_y - 0.5) * 1.70;
            }
            sat = Math.max(0, Math.min(1, sat));
            val = Math.max(0, Math.min(1, val));
            const [r, g, b] = hsvToRgb(hue, sat, val);
            return "#" + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1).toUpperCase();
        }

        function drawSpectrum() {
            const w = canvas.width;
            const h = canvas.height;
            const imgData = ctx.createImageData(w, h);
            const data = imgData.data;

            for (let y = 0; y < h; y++) {
                const rel_y = y / h;
                for (let x = 0; x < w; x++) {
                    const rel_x = x / w;
                    const hue = rel_x;
                    let sat, val;
                    if (rel_y <= 0.5) {
                        sat = 0.15 + rel_y * 1.70;
                        val = 1.0;
                    } else {
                        sat = 1.0;
                        val = 1.0 - (rel_y - 0.5) * 1.70;
                    }
                    sat = Math.max(0, Math.min(1, sat));
                    val = Math.max(0, Math.min(1, val));
                    const [r, g, b] = hsvToRgb(hue, sat, val);
                    const idx = (y * w + x) * 4;
                    data[idx] = r;
                    data[idx + 1] = g;
                    data[idx + 2] = b;
                    data[idx + 3] = 255;
                }
            }
            ctx.putImageData(imgData, 0, 0);

            // Draw markers
            points.forEach((p, idx) => {
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const isDragging = (draggingIdx === idx);

                // If dragging, draw a 3x magnified loupe lens above the cursor
                if (isDragging) {
                    const loupeR = 24;
                    const loupeY = py - 36;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(px, loupeY, loupeR, 0, Math.PI * 2);
                    ctx.clip();
                    // Draw 3x zoomed spectrum crop
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
                }

                // Outer dark shadow
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
            });
        }

        function updateUI() {
            countLbl.textContent = `Dropped Points (${points.length}):`;
            addBtn.textContent = points.length > 0 ? `Add ${points.length} Colors` : 'Add Colors';
            
            // Render chips
            chipContainer.innerHTML = '';
            points.forEach((p, idx) => {
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
                delBtn.onclick = () => {
                    points.splice(idx, 1);
                    drawSpectrum();
                    updateUI();
                };

                chip.appendChild(left);
                chip.appendChild(delBtn);
                chipContainer.appendChild(chip);
            });

            // Update hidden form input & HTMX post vals
            const hexes = points.map(p => p.hex);
            const hiddenInput = document.getElementById('spectrum-colors-input');
            if (hiddenInput) {
                hiddenInput.value = JSON.stringify(hexes);
            }
            addBtn.setAttribute('hx-vals', JSON.stringify({ "colors": hexes }));
            if (window.htmx) htmx.process(addBtn);
        }

        function getCanvasCoords(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / (rect.width || 1);
            const scaleY = canvas.height / (rect.height || 1);
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            return {
                x: Math.max(0, Math.min(canvas.width, x)),
                y: Math.max(0, Math.min(canvas.height, y))
            };
        }

        canvas.ondragstart = function(e) {
            e.preventDefault();
            return false;
        };

        canvas.onmousedown = function(e) {
            e.preventDefault();
            e.stopPropagation();
            const coords = getCanvasCoords(e);
            const x = coords.x;
            const y = coords.y;
            const w = canvas.width;
            const h = canvas.height;

            // Check if clicked near an existing point
            let clickedIdx = null;
            let minDist = Infinity;
            points.forEach((p, idx) => {
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const dist = Math.hypot(px - x, py - y);
                if (dist <= 22 && dist < minDist) {
                    minDist = dist;
                    clickedIdx = idx;
                }
            });

            if (clickedIdx !== null) {
                draggingIdx = clickedIdx;
            } else {
                const rel_x = x / w;
                const rel_y = y / h;
                const hex = colorAtRel(rel_x, rel_y);
                points.push({ hex, rel_x, rel_y });
                draggingIdx = points.length - 1;
            }
            drawSpectrum();
            updateUI();
        };

        canvas.ondblclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            const coords = getCanvasCoords(e);
            const x = coords.x;
            const y = coords.y;
            const w = canvas.width;
            const h = canvas.height;

            let targetIdx = null;
            let minDist = Infinity;
            points.forEach((p, idx) => {
                const px = p.rel_x * w;
                const py = p.rel_y * h;
                const dist = Math.hypot(px - x, py - y);
                if (dist <= 24 && dist < minDist) {
                    minDist = dist;
                    targetIdx = idx;
                }
            });

            if (targetIdx !== null) {
                points.splice(targetIdx, 1);
                draggingIdx = null;
                drawSpectrum();
                updateUI();
            }
        };

        window.addEventListener('mousemove', function(e) {
            if (draggingIdx === null) return;
            const coords = getCanvasCoords(e);
            const rel_x = coords.x / canvas.width;
            const rel_y = coords.y / canvas.height;
            points[draggingIdx].rel_x = rel_x;
            points[draggingIdx].rel_y = rel_y;
            points[draggingIdx].hex = colorAtRel(rel_x, rel_y);
            drawSpectrum();
            updateUI();
        });

        window.addEventListener('mouseup', function() {
            if (draggingIdx !== null) {
                draggingIdx = null;
                drawSpectrum();
            }
        });

        // Presets logic
        window._addPresetColors = function(type) {
            let newHues = [];
            if (type === 'vibrant') {
                newHues = [
                    { rel_x: 0.05, rel_y: 0.45 },
                    { rel_x: 0.35, rel_y: 0.48 },
                    { rel_x: 0.60, rel_y: 0.52 },
                    { rel_x: 0.85, rel_y: 0.46 }
                ];
            } else if (type === 'pastel') {
                newHues = [
                    { rel_x: 0.10, rel_y: 0.15 },
                    { rel_x: 0.40, rel_y: 0.18 },
                    { rel_x: 0.65, rel_y: 0.16 },
                    { rel_x: 0.90, rel_y: 0.14 }
                ];
            } else if (type === 'muted') {
                newHues = [
                    { rel_x: 0.08, rel_y: 0.72 },
                    { rel_x: 0.38, rel_y: 0.76 },
                    { rel_x: 0.58, rel_y: 0.70 },
                    { rel_x: 0.82, rel_y: 0.75 }
                ];
            }
            newHues.forEach(pt => {
                pt.hex = colorAtRel(pt.rel_x, pt.rel_y);
                points.push(pt);
            });
            drawSpectrum();
            updateUI();
        };

        window._clearSpectrumPoints = function() {
            points = [];
            drawSpectrum();
            updateUI();
        };

        // Initial render
        drawSpectrum();
        updateUI();
    })();
    """

    return Div(
        Div(
            Div(
                H2("ADD COLORS — COLOR SPECTRUM", style="font-size: 15px; font-weight: 800; letter-spacing: 0.8px; margin: 0; color: var(--text-main) !important;"),
                Button("✕", type="button", onclick="window.closeModal()", style="background: transparent; border: none; font-size: 16px; font-weight: bold; cursor: pointer; color: var(--text-main) !important;"),
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;"
            ),
            Div(
                Canvas(id="spectrum-canvas", width=580, height=220, style="width: 100%; max-height: 200px; border-radius: 8px; cursor: crosshair; display: block; border: 1px solid var(--border-color, #444);"),
                style="margin-bottom: 10px; height: 200px; flex-shrink: 0;"
            ),
            # Quick Presets Row
            Div(
                Div("Quick Presets:", style="font-size: 12px; font-weight: 700; color: var(--text-muted, #888);"),
                Button("+ 4 Vibrant", type="button", cls="btn", onclick="_addPresetColors('vibrant')", style="padding: 4px 10px; font-size: 12px;"),
                Button("+ 4 Pastel", type="button", cls="btn", onclick="_addPresetColors('pastel')", style="padding: 4px 10px; font-size: 12px;"),
                Button("+ 4 Muted", type="button", cls="btn", onclick="_addPresetColors('muted')", style="padding: 4px 10px; font-size: 12px;"),
                Div(style="flex-grow: 1;"),
                Button("Clear All", type="button", cls="btn", onclick="_clearSpectrumPoints()", style="padding: 4px 10px; font-size: 12px; color: #f87171;"),
                style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-shrink: 0;"
            ),
            # Dropped Points Header & List (Fixed height scrollable area)
            Div(
                Div("Dropped Points (0):", id="dropped-count-lbl", style="font-size: 13px; font-weight: 700; color: var(--text-main) !important; margin-bottom: 6px; flex-shrink: 0;"),
                Div(id="spectrum-chip-list", style="display: flex; flex-direction: column; gap: 6px; height: 130px; overflow-y: auto; padding-right: 6px;"),
                style="margin-bottom: 14px; flex: 1 1 auto; min-height: 130px;"
            ),
            # Form with hidden colors input for 100% reliable submission
            Form(
                Input(type="hidden", id="spectrum-colors-input", name="colors", value="[]"),
                Div(
                    Button("Cancel", type="button", cls="btn", onclick="window.closeModal()", style="padding: 8px 18px;"),
                    Div(style="flex-grow: 1;"),
                    Button(
                        "Add Colors", 
                        id="add-spectrum-colors-btn", 
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
