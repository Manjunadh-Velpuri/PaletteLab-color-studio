/*
Interactions logic for PaletteLab Web
Includes Dynamic Theme Engine (defaulting to Taupe Minimalist, persisted in Cookie + LocalStorage),
Clipboard operations, Conversion Table selection and copying, Canvas live settings sync, and shortcuts.
*/

document.addEventListener('DOMContentLoaded', () => {
    console.log("PaletteLab Web Interactions Initialized");

    // ----------------------------------------
    // 1. Dynamic Theme Engine
    // ----------------------------------------
    const DEFAULT_LIGHT = 'theme-monochrome-pro';
    const DEFAULT_DARK = 'theme-vercel-dark';

    const getCookie = (name) => {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    };

    // Load from cookie or localStorage or fallback to Taupe Minimalist
    const savedTheme = getCookie('palettelab-theme') || localStorage.getItem('palettelab-theme') || DEFAULT_LIGHT;
    applyTheme(savedTheme);

    function applyTheme(themeName) {
        if (!themeName.startsWith('theme-')) {
            themeName = 'theme-' + themeName;
        }

        // Apply class to document.body
        const themeClasses = Array.from(document.body.classList).filter(c => c.startsWith('theme-'));
        themeClasses.forEach(c => document.body.classList.remove(c));
        document.body.classList.add(themeName);

        // Also sync theme selector dropdown if present
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = themeName.replace('theme-', '');
        }

        // Persist to cookie (1 year) and localStorage
        document.cookie = `palettelab-theme=${themeName};path=/;max-age=31536000;SameSite=Lax`;
        localStorage.setItem('palettelab-theme', themeName);

        // Highlight Active Light / Dark Mode Button
        const isDark = getComputedStyle(document.body).getPropertyValue('color-scheme').trim() === 'dark'
            || themeName.includes('dark') || themeName.includes('night') || themeName.includes('dimmed') || themeName.includes('onyx') || themeName.includes('mocha') || themeName.includes('pecan') || themeName.includes('olive') || themeName.includes('slate') || themeName.includes('charcoal');

        const btnLight = document.getElementById('theme-light-btn');
        const btnDark = document.getElementById('theme-dark-btn');
        if (btnLight && btnDark) {
            if (isDark) {
                btnDark.classList.add('active');
                btnLight.classList.remove('active');
            } else {
                btnLight.classList.add('active');
                btnDark.classList.remove('active');
            }
        }
    }

    window.applyTheme = applyTheme;

    // Connect top bar theme dropdown and sun/moon buttons
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector) {
        themeSelector.addEventListener('change', (e) => {
            applyTheme(e.target.value);
        });
    }

    const btnLight = document.getElementById('theme-light-btn');
    if (btnLight) {
        btnLight.addEventListener('click', () => {
            applyTheme(DEFAULT_LIGHT);
        });
    }

    const btnDark = document.getElementById('theme-dark-btn');
    if (btnDark) {
        btnDark.addEventListener('click', () => {
            applyTheme(DEFAULT_DARK);
        });
    }

    // ----------------------------------------
    // 2. Keyboard Shortcut: Ctrl+Enter to Extract
    // ----------------------------------------
    const textInput = document.getElementById('raw-text-input');
    const extractForm = document.getElementById('extract-form');
    if (textInput && extractForm) {
        textInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                if (window.htmx) {
                    htmx.trigger(extractForm, 'submit');
                } else {
                    extractForm.submit();
                }
            }
        });
    }

    // ----------------------------------------
    // 3. Enforce Max 2 Checked Labels Rule
    // ----------------------------------------
    const labelsContainer = document.getElementById('display-labels-container');
    if (labelsContainer) {
        labelsContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                const checkedBoxes = Array.from(labelsContainer.querySelectorAll('input[type="checkbox"]:checked'));
                if (checkedBoxes.length > 2) {
                    const toUncheck = checkedBoxes.find(cb => cb !== e.target);
                    if (toUncheck) toUncheck.checked = false;
                }
                updateCanvasSettings();
            }
        });
    }

    // ----------------------------------------
    // 4. Global HTMX Loading Indicator
    // ----------------------------------------
    document.body.addEventListener('htmx:beforeRequest', () => {
        document.body.classList.add('is-loading');
    });
    document.body.addEventListener('htmx:afterRequest', () => {
        document.body.classList.remove('is-loading');
    });
});

// ----------------------------------------
// Copy All HEX to Clipboard
// ----------------------------------------
window.copyAllHexes = function () {
    const listContainer = document.getElementById('color-list-container');
    const copyBtn = document.getElementById('copy-hex-btn');
    if (!listContainer) return;

    const hexElements = listContainer.querySelectorAll('.color-hex');
    const hexes = Array.from(hexElements).map(el => el.textContent.trim());

    if (hexes.length === 0) {
        if (copyBtn) {
            const originalText = copyBtn.innerHTML;
            copyBtn.textContent = 'No colors!';
            setTimeout(() => { copyBtn.innerHTML = originalText; }, 1500);
        }
        return;
    }

    const textToCopy = hexes.join('\n');
    navigator.clipboard.writeText(textToCopy).then(() => {
        if (copyBtn) {
            const originalText = copyBtn.innerHTML;
            copyBtn.textContent = '✓ Copied!';
            setTimeout(() => { copyBtn.innerHTML = originalText; }, 1500);
        }
        if (window.showToast) {
            window.showToast(`✓ Copied ${hexes.length} HEX colors to clipboard!`, 'success', 3000);
        }
    }).catch(err => {
        console.error('Failed to copy: ', err);
        if (window.showToast) {
            window.showToast('Failed to copy to clipboard', 'error', 3000);
        }
    });
};

// ----------------------------------------
// Conversion Table Column Selection Toggles
// ----------------------------------------
window.toggleColumnCheck = function (colKey, isChecked) {
    const table = document.querySelector('.canvas-body table');
    if (!table) return;
    const checkboxes = table.querySelectorAll(`.conv-cell-check.col-${colKey}`);
    checkboxes.forEach(cb => {
        cb.checked = isChecked;
    });
};

window.onCellCheckChange = function () {
    // Check if any column header needs sync
    const table = document.querySelector('.canvas-body table');
    if (!table) return;
    const cols = ['hex', 'name', 'rgb', 'hsl', 'hsv', 'cmyk', 'lab'];
    cols.forEach(colKey => {
        const headerCheck = table.querySelector(`thead th:nth-child(${cols.indexOf(colKey) + 1}) input[type="checkbox"]`);
        const cellChecks = Array.from(table.querySelectorAll(`.conv-cell-check.col-${colKey}`));
        if (headerCheck && cellChecks.length > 0) {
            const allChecked = cellChecks.every(cb => cb.checked);
            headerCheck.checked = allChecked;
        }
    });
};

// ----------------------------------------
// Copy Conversion Table to Clipboard
// Formats: Every selected conversion for a specific color in single row (space/tab separated),
// and next color on next row.
// ----------------------------------------
window.copyConversionTable = function () {
    const table = document.querySelector('.canvas-body table');
    const copyBtn = document.getElementById('copy-conversions-btn');
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tbody tr.conversion-row'));
    if (rows.length === 0) return;

    const outputRows = [];

    rows.forEach(tr => {
        const selectedValuesInRow = [];
        const checkedBoxes = Array.from(tr.querySelectorAll('input.conv-cell-check:checked'));
        checkedBoxes.forEach(cb => {
            const val = cb.getAttribute('data-val') || '';
            if (val) {
                selectedValuesInRow.push(val);
            }
        });

        if (selectedValuesInRow.length > 0) {
            outputRows.push(selectedValuesInRow.join('\t'));
        }
    });

    if (outputRows.length === 0) {
        if (copyBtn) {
            const orig = copyBtn.textContent;
            copyBtn.textContent = 'No items selected!';
            setTimeout(() => { copyBtn.textContent = orig; }, 1500);
        }
        return;
    }

    const textToCopy = outputRows.join('\n');
    navigator.clipboard.writeText(textToCopy).then(() => {
        if (copyBtn) {
            const orig = copyBtn.textContent;
            copyBtn.textContent = '✓ Copied Selected!';
            setTimeout(() => { copyBtn.textContent = orig; }, 1500);
        }
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
};

// ----------------------------------------
// Sync Canvas Settings with Server via HTMX
// ----------------------------------------
window.updateCanvasSettings = function () {
    const mode = document.getElementById('workspace-mode-select')?.value || 'Palette';
    const layout = document.getElementById('layout-select')?.value || 'Chips';
    const sort = document.getElementById('sort-select')?.value || 'Original';
    const autoBg = document.getElementById('auto-bg-check')?.checked ? 'true' : 'false';

    const labelsContainer = document.getElementById('display-labels-container');
    const checkedLabels = labelsContainer
        ? Array.from(labelsContainer.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value)
        : ['Color Name', 'HEX'];

    if (window.htmx) {
        htmx.ajax('POST', '/api/update-canvas-settings', {
            target: '#canvas-body',
            swap: 'outerHTML',
            values: {
                mode: mode,
                layout: layout,
                sort: sort,
                labels: checkedLabels,
                auto_bg: autoBg
            }
        });
    }
};

// ----------------------------------------
// Close Modal Helper
// ----------------------------------------
window.closeModal = function () {
    const modal = document.getElementById('modal-container');
    if (modal) {
        modal.innerHTML = '';
        modal.removeAttribute('style');
        modal.style.display = 'none';
    }
};

// ----------------------------------------
// Theme-Aligned Toast Notification Engine
// ----------------------------------------
window.showToast = function (message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast-item';

    let iconHtml = '';
    if (type === 'success') {
        iconHtml = '<div class="toast-icon toast-success"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M11.4669 3.72684C11.7458 3.42231 12.2205 3.39766 12.525 3.67657C12.8296 3.95548 12.8542 4.43019 12.5753 4.73471L6.32531 11.5622C6.18267 11.7182 5.97985 11.808 5.76639 11.8085C5.55293 11.8091 5.34951 11.7203 5.20579 11.5652L2.45579 8.5985C2.17511 8.29548 2.19725 7.82069 2.50027 7.54001C2.80329 7.25934 3.27808 7.28148 3.55876 7.5845L5.75924 9.96025L11.4669 3.72684Z" fill="currentColor"/></svg></div>';
    } else if (type === 'error') {
        iconHtml = '<div class="toast-icon toast-error"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1C3.91015 1 1 3.91015 1 7.5C1 11.0899 3.91015 14 7.5 14C11.0899 14 14 11.0899 14 7.5C14 3.91015 11.0899 1 7.5 1ZM7.5 4C7.77614 4 8 4.22386 8 4.5V8.5C8 8.77614 7.77614 9 7.5 9C7.22386 9 7 8.77614 7 8.5V4.5C7 4.22386 7 4 7.5 4ZM8 10.5C8 10.7761 7.77614 11 7.5 11C7.22386 11 7 10.7761 7 10.5C7 10.2239 7.22386 10 7.5 10C7.77614 10 8 10.2239 8 10.5Z" fill="currentColor"/></svg></div>';
    } else if (type === 'loading') {
        iconHtml = '<div class="toast-icon toast-loading"><div class="toast-spinner"></div></div>';
    } else {
        iconHtml = '<div class="toast-icon toast-info"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1C3.91015 1 1 3.91015 1 7.5C1 11.0899 3.91015 14 7.5 14C11.0899 14 14 11.0899 14 7.5C14 3.91015 11.0899 1 7.5 1ZM7.5 3C7.91421 3 8.25 3.33579 8.25 3.75C8.25 4.16421 7.91421 4.5 7.5 4.5C7.08579 4.5 6.75 4.16421 6.75 3.75C6.75 3.33579 7.08579 3 7.5 3ZM7 6C7 5.72386 7.22386 5.5 7.5 5.5C7.77614 5.5 8 5.72386 8 6V11C8 11.2761 7.77614 11.5 7.5 11.5C7.22386 11.5 7 11.2761 7 11V6Z" fill="currentColor"/></svg></div>';
    }

    toast.innerHTML = `
        ${iconHtml}
        <div class="toast-message">${message}</div>
        <button type="button" class="toast-close" title="Dismiss">✕</button>
    `;

    const closeBtn = toast.querySelector('.toast-close');
    let timer = null;
    const dismiss = () => {
        if (timer) clearTimeout(timer);
        toast.classList.remove('toast-visible');
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    };

    closeBtn.onclick = dismiss;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add('toast-visible');
    });

    if (duration > 0) {
        timer = setTimeout(dismiss, duration);
    }

    return {
        element: toast,
        dismiss: dismiss,
        update: (newMessage, newType = 'info', newDuration = 3000) => {
            if (timer) clearTimeout(timer);
            let newIcon = '';
            if (newType === 'success') {
                newIcon = '<div class="toast-icon toast-success"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M11.4669 3.72684C11.7458 3.42231 12.2205 3.39766 12.525 3.67657C12.8296 3.95548 12.8542 4.43019 12.5753 4.73471L6.32531 11.5622C6.18267 11.7182 5.97985 11.808 5.76639 11.8085C5.55293 11.8091 5.34951 11.7203 5.20579 11.5652L2.45579 8.5985C2.17511 8.29548 2.19725 7.82069 2.50027 7.54001C2.80329 7.25934 3.27808 7.28148 3.55876 7.5845L5.75924 9.96025L11.4669 3.72684Z" fill="currentColor"/></svg></div>';
            } else if (newType === 'error') {
                newIcon = '<div class="toast-icon toast-error"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1C3.91015 1 1 3.91015 1 7.5C1 11.0899 3.91015 14 7.5 14C11.0899 14 14 11.0899 14 7.5C14 3.91015 11.0899 1 7.5 1ZM7.5 4C7.77614 4 8 4.22386 8 4.5V8.5C8 8.77614 7.77614 9 7.5 9C7.22386 9 7 8.77614 7 8.5V4.5C7 4.22386 7 4 7.5 4ZM8 10.5C8 10.7761 7.77614 11 7.5 11C7.22386 11 7 10.7761 7 10.5C7 10.2239 7.22386 10 7.5 10C7.77614 10 8 10.2239 8 10.5Z" fill="currentColor"/></svg></div>';
            } else if (newType === 'loading') {
                newIcon = '<div class="toast-icon toast-loading"><div class="toast-spinner"></div></div>';
            } else {
                newIcon = '<div class="toast-icon toast-info"><svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1C3.91015 1 1 3.91015 1 7.5C1 11.0899 3.91015 14 7.5 14C11.0899 14 14 11.0899 14 7.5C14 3.91015 11.0899 1 7.5 1ZM7.5 3C7.91421 3 8.25 3.33579 8.25 3.75C8.25 4.16421 7.91421 4.5 7.5 4.5C7.08579 4.5 6.75 4.16421 6.75 3.75C6.75 3.33579 7.08579 3 7.5 3ZM7 6C7 5.72386 7.22386 5.5 7.5 5.5C7.77614 5.5 8 5.72386 8 6V11C8 11.2761 7.77614 11.5 7.5 11.5C7.22386 11.5 7 11.2761 7 11V6Z" fill="currentColor"/></svg></div>';
            }
            const iconEl = toast.querySelector('.toast-icon');
            if (iconEl) iconEl.outerHTML = newIcon;
            const msgEl = toast.querySelector('.toast-message');
            if (msgEl) msgEl.textContent = newMessage;
            if (newDuration > 0) {
                timer = setTimeout(dismiss, newDuration);
            }
        }
    };
};

// ----------------------------------------
// HTMX Global Toast Feedback Listeners
// ----------------------------------------
let activeHtmxToast = null;
document.addEventListener('htmx:beforeRequest', (evt) => {
    const path = evt.detail.requestConfig?.path || '';
    if (path === '/api/random') {
        activeHtmxToast = window.showToast('Generating balanced palette...', 'loading', 0);
    } else if (path === '/api/extract') {
        activeHtmxToast = window.showToast('Extracting colors from text...', 'loading', 0);
    } else if (path === '/api/clear') {
        window.showToast('Workspace palette cleared', 'info', 2500);
    } else if (path === '/api/add-colors-bulk') {
        activeHtmxToast = window.showToast('Adding extracted colors to palette...', 'loading', 0);
    }
});

document.addEventListener('htmx:afterRequest', (evt) => {
    const path = evt.detail.requestConfig?.path || '';
    const successful = evt.detail.successful;

    if (activeHtmxToast) {
        if (successful) {
            if (path === '/api/random') {
                activeHtmxToast.update('✨ New palette generated!', 'success', 3000);
            } else if (path === '/api/extract') {
                activeHtmxToast.update('✓ Colors extracted successfully!', 'success', 3000);
            } else if (path === '/api/add-colors-bulk') {
                activeHtmxToast.update('✓ Photo colors added to workspace!', 'success', 3000);
            } else {
                activeHtmxToast.dismiss();
            }
        } else {
            activeHtmxToast.update('Action could not be completed', 'error', 3500);
        }
        activeHtmxToast = null;
    }
});

document.addEventListener('htmx:responseError', () => {
    if (activeHtmxToast) {
        activeHtmxToast.update('Server request failed. Please retry.', 'error', 3500);
        activeHtmxToast = null;
    }
});

// Toast feedback for Export clicks
document.addEventListener('click', (e) => {
    const target = e.target.closest('a');
    if (target && target.href) {
        if (target.href.includes('/api/export/png')) {
            window.showToast('Generating 300 DPI high-resolution PNG export...', 'loading', 3500);
        } else if (target.href.includes('/api/export/svg')) {
            window.showToast('Exporting clean vector SVG palette...', 'loading', 2500);
        }
    }
});

// ----------------------------------------
// Photo Modal Canvas Engine (Fail-safe with Pre-attached onload)
// ----------------------------------------
window.initPhotoModalCanvas = function (imgB64, initialData) {
    const canvas = document.getElementById('photo-modal-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const countValLbl = document.getElementById('photo-count-val');
    const chipContainer = document.getElementById('photo-chip-list');
    const extractBtn = document.getElementById('photo-extract-submit-btn');

    let points = []; // [{hex: string, rel_x: float, rel_y: float}]
    let draggingIdx = null;

    const img = new Image();

    // CRITICAL: img.onload MUST be assigned BEFORE setting img.src!
    img.onload = function () {
        const maxW = 580;
        const maxH = 300;
        let w = img.width || 100;
        let h = img.height || 100;
        const ratio = Math.min(maxW / w, maxH / h, 1.0);
        canvas.width = Math.round(w * ratio);
        canvas.height = Math.round(h * ratio);

        points = (initialData || []).map(p => ({
            hex: p.hex,
            rel_x: p.rel_x,
            rel_y: p.rel_y
        }));

        drawCanvas();
        updateUI();
    };

    img.onerror = function () {
        console.error("Failed to load photo preview image into canvas.");
        if (canvas.parentElement) {
            canvas.parentElement.innerHTML = '<div style="color: #ef4444; font-size: 13px; padding: 20px;">Failed to render image canvas.</div>';
        }
    };

    // Set src AFTER onload is attached
    img.src = imgB64;

    // Fallback if image was cached and already complete
    if (img.complete && img.naturalWidth > 0) {
        img.onload();
    }

    function samplePixelHex(x, y) {
        x = Math.max(0, Math.min(canvas.width - 1, Math.round(x)));
        y = Math.max(0, Math.min(canvas.height - 1, Math.round(y)));
        try {
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            return "#" + (1 << 24 | pixel[0] << 16 | pixel[1] << 8 | pixel[2]).toString(16).slice(1).toUpperCase();
        } catch (e) {
            return "#888888";
        }
    }

    function drawCanvas() {
        if (!canvas.width || !canvas.height) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        const w = canvas.width;
        const h = canvas.height;
        points.forEach(p => {
            p.hex = samplePixelHex(p.rel_x * w, p.rel_y * h);
        });

        points.forEach((p, idx) => {
            const px = p.rel_x * w;
            const py = p.rel_y * h;
            const isDragging = (draggingIdx === idx);

            if (isDragging) {
                const loupeR = 24;
                const loupeY = Math.max(loupeR + 4, py - 36);
                ctx.save();
                ctx.beginPath();
                ctx.arc(px, loupeY, loupeR, 0, Math.PI * 2);
                ctx.clip();
                const zoomSize = 16;
                ctx.drawImage(canvas, px - zoomSize / 2, py - zoomSize / 2, zoomSize, zoomSize, px - loupeR, loupeY - loupeR, loupeR * 2, loupeR * 2);
                ctx.restore();

                ctx.beginPath();
                ctx.arc(px, loupeY, loupeR, 0, Math.PI * 2);
                ctx.lineWidth = 3;
                ctx.strokeStyle = '#FFFFFF';
                ctx.stroke();
                ctx.lineWidth = 1;
                ctx.strokeStyle = 'rgba(0,0,0,0.6)';
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(px, loupeY, 2, 0, Math.PI * 2);
                ctx.fillStyle = '#FF0000';
                ctx.fill();
            }

            // Outer shadow ring
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
        if (countValLbl) countValLbl.textContent = points.length.toString();
        if (extractBtn) {
            extractBtn.textContent = points.length > 0 ? `Extract ${points.length} Colors` : 'Extract Colors';
        }

        if (chipContainer) {
            chipContainer.innerHTML = '';
            points.forEach((p, idx) => {
                const chip = document.createElement('div');
                chip.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:6px 12px;background:var(--bg-main,#222);border:1px solid var(--border-color,#444);border-radius:6px;gap:12px;';

                const left = document.createElement('div');
                left.style.cssText = 'display:flex;align-items:center;gap:10px;';

                const swatch = document.createElement('div');
                swatch.style.cssText = `width:24px;height:24px;border-radius:4px;background-color:${p.hex};border:1px solid rgba(255,255,255,0.2);`;

                const lbl = document.createElement('span');
                lbl.textContent = p.hex;
                lbl.style.cssText = 'font-family:monospace;font-weight:700;font-size:14px;';

                left.appendChild(swatch);
                left.appendChild(lbl);

                const delBtn = document.createElement('button');
                delBtn.textContent = '✕';
                delBtn.style.cssText = 'background:transparent;border:none;color:#ef4444;cursor:pointer;font-size:14px;font-weight:bold;';
                delBtn.onclick = () => {
                    points.splice(idx, 1);
                    drawCanvas();
                    updateUI();
                };

                chip.appendChild(left);
                chip.appendChild(delBtn);
                chipContainer.appendChild(chip);
            });
        }

        const hexes = points.map(p => p.hex);
        const hiddenInput = document.getElementById('photo-colors-input');
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(hexes);
        }
        if (extractBtn) {
            extractBtn.setAttribute('hx-vals', JSON.stringify({ "colors": hexes }));
            if (window.htmx) htmx.process(extractBtn);
        }
    }

    function getCanvasCoords(e) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / (rect.width || 1);
        const scaleY = canvas.height / (rect.height || 1);
        const clientX = (e.touches && e.touches.length > 0) ? e.touches[0].clientX : e.clientX;
        const clientY = (e.touches && e.touches.length > 0) ? e.touches[0].clientY : e.clientY;
        return {
            x: Math.max(0, Math.min(canvas.width, (clientX - rect.left) * scaleX)),
            y: Math.max(0, Math.min(canvas.height, (clientY - rect.top) * scaleY))
        };
    }

    canvas.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        const coords = getCanvasCoords(e);
        const x = coords.x;
        const y = coords.y;
        const w = canvas.width;
        const h = canvas.height;

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
        } else if (points.length < 16) {
            const rel_x = x / w;
            const rel_y = y / h;
            const hex = samplePixelHex(x, y);
            points.push({ hex, rel_x, rel_y });
            draggingIdx = points.length - 1;
        }
        drawCanvas();
        updateUI();
    };

    canvas.ondblclick = function (e) {
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
            drawCanvas();
            updateUI();
        }
    };

    window.addEventListener('mousemove', function (e) {
        if (draggingIdx === null) return;
        const coords = getCanvasCoords(e);
        points[draggingIdx].rel_x = coords.x / canvas.width;
        points[draggingIdx].rel_y = coords.y / canvas.height;
        points[draggingIdx].hex = samplePixelHex(coords.x, coords.y);
        drawCanvas();
        updateUI();
    });

    window.addEventListener('mouseup', function () {
        if (draggingIdx !== null) {
            draggingIdx = null;
            drawCanvas();
        }
    });

    // Touch events for mobile
    canvas.addEventListener('touchstart', function (e) {
        if (e.touches && e.touches.length === 1) {
            e.preventDefault();
            canvas.onmousedown(e);
        }
    }, { passive: false });

    window.addEventListener('touchmove', function (e) {
        if (draggingIdx !== null && e.touches && e.touches.length === 1) {
            e.preventDefault();
            const coords = getCanvasCoords(e);
            points[draggingIdx].rel_x = coords.x / canvas.width;
            points[draggingIdx].rel_y = coords.y / canvas.height;
            points[draggingIdx].hex = samplePixelHex(coords.x, coords.y);
            drawCanvas();
            updateUI();
        }
    }, { passive: false });

    window.addEventListener('touchend', function () {
        if (draggingIdx !== null) {
            draggingIdx = null;
            drawCanvas();
        }
    });

    window._photoDecCount = function () {
        if (points.length > 0) {
            points.pop();
            drawCanvas();
            updateUI();
        }
    };

    window._photoIncCount = function () {
        if (points.length < 16) {
            const rel_x = Math.random() * 0.8 + 0.1;
            const rel_y = Math.random() * 0.8 + 0.1;
            const hex = samplePixelHex(rel_x * canvas.width, rel_y * canvas.height);
            points.push({ hex, rel_x, rel_y });
            drawCanvas();
            updateUI();
        }
    };
};

// ----------------------------------------
// Photo Upload with Client-Side Downscaling (Mobile & Large Photo Safe)
// ----------------------------------------
window.handlePhotoUpload = function (input) {
    const file = input.files && input.files[0];
    if (!file) return;

    let modalContainer = document.getElementById('modal-container');
    if (!modalContainer) {
        modalContainer = document.createElement('div');
        modalContainer.id = 'modal-container';
        document.body.appendChild(modalContainer);
    }
    modalContainer.className = 'modal-backdrop';
    modalContainer.style.position = 'fixed';
    modalContainer.style.inset = '0';
    modalContainer.style.background = 'rgba(0,0,0,0.75)';
    modalContainer.style.display = 'flex';
    modalContainer.style.alignItems = 'center';
    modalContainer.style.justifyContent = 'center';
    modalContainer.style.zIndex = '1000';
    modalContainer.innerHTML = `
        <div style="background: var(--panel-bg, #1a1a1a); color: var(--text-main, #fff); padding: 24px 32px; border-radius: 14px; border: 1px solid var(--border-color, #333); font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 14px; box-shadow: 0 16px 40px rgba(0,0,0,0.6);">
            <div style="width: 32px; height: 32px; border: 3px solid rgba(255,255,255,0.2); border-top-color: var(--accent-red, #967D6D); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
            <div style="font-size: 14px; letter-spacing: 0.5px;">Optimizing & extracting photo colors...</div>
        </div>
        <style>@keyframes spin { 100% { transform: rotate(360deg); } }</style>
    `;

    const uploadToast = window.showToast ? window.showToast('Downscaling & extracting photo colors...', 'loading', 0) : null;

    const reader = new FileReader();
    reader.onload = function (e) {
        const img = new Image();
        img.onload = function () {
            // Client-side downscaling to max 1000px: drops 15MB camera photos to ~100KB JPEG!
            const maxDim = 1000;
            let w = img.width;
            let h = img.height;
            if (w > maxDim || h > maxDim) {
                if (w > h) {
                    h = Math.round((h * maxDim) / w);
                    w = maxDim;
                } else {
                    w = Math.round((w * maxDim) / h);
                    h = maxDim;
                }
            }

            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, w, h);

            canvas.toBlob(function (blob) {
                const formData = new FormData();
                formData.append('photo', blob || file, file.name || 'photo.jpg');

                fetch('/api/extract-photo', {
                    method: 'POST',
                    body: formData
                })
                .then(res => {
                    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
                    return res.text();
                })
                .then(html => {
                    if (uploadToast) uploadToast.dismiss();
                    if (window.showToast) window.showToast('Photo loaded! Tap or drag pins to pick colors', 'success', 3500);

                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newModal = doc.getElementById('modal-container');
                    if (newModal) {
                        modalContainer.replaceWith(newModal);
                        
                        // Safely execute all script tags inside newModal so canvas initializes
                        const scripts = newModal.querySelectorAll('script');
                        scripts.forEach(oldScript => {
                            const s = document.createElement('script');
                            if (oldScript.src) {
                                s.src = oldScript.src;
                            } else {
                                s.textContent = oldScript.textContent;
                            }
                            document.body.appendChild(s);
                            s.remove();
                        });

                        if (window.htmx) htmx.process(newModal);
                    }
                })
                .catch(err => {
                    console.error("Photo extract error:", err);
                    if (uploadToast) uploadToast.update('Photo extract failed: ' + (err.message || 'Error'), 'error', 4000);
                    modalContainer.innerHTML = `
                        <div style="background: var(--panel-bg, #1a1a1a); color: var(--text-main, #fff); padding: 24px; border-radius: 14px; border: 1px solid var(--border-color, #333); text-align: center; max-width: 380px;">
                            <div style="color: #ef4444; font-weight: 700; margin-bottom: 8px;">Photo Extract Error</div>
                            <div style="font-size: 13px; color: var(--text-muted, #888); margin-bottom: 16px;">${err.message || 'Could not process photo'}</div>
                            <button type="button" class="btn" onclick="window.closeModal()" style="padding: 8px 20px;">Close</button>
                        </div>
                    `;
                });
            }, 'image/jpeg', 0.85);
        };
        img.onerror = function () {
            if (uploadToast) uploadToast.update('Invalid image file format', 'error', 3500);
            modalContainer.innerHTML = `
                <div style="background: var(--panel-bg, #1a1a1a); color: var(--text-main, #fff); padding: 24px; border-radius: 14px; border: 1px solid var(--border-color, #333); text-align: center; max-width: 380px;">
                    <div style="color: #ef4444; font-weight: 700; margin-bottom: 8px;">Invalid Image</div>
                    <div style="font-size: 13px; color: var(--text-muted, #888); margin-bottom: 16px;">Could not read this file as an image.</div>
                    <button type="button" class="btn" onclick="window.closeModal()" style="padding: 8px 20px;">Close</button>
                </div>
            `;
        };
        img.src = e.target.result;
    };
    reader.onerror = function () {
        if (uploadToast) uploadToast.update('Could not read selected file', 'error', 3500);
        modalContainer.innerHTML = `
            <div style="background: var(--panel-bg, #1a1a1a); color: var(--text-main, #fff); padding: 24px; border-radius: 14px; border: 1px solid var(--border-color, #333); text-align: center; max-width: 380px;">
                <div style="color: #ef4444; font-weight: 700; margin-bottom: 8px;">File Read Error</div>
                <button type="button" class="btn" onclick="window.closeModal()" style="padding: 8px 20px;">Close</button>
            </div>
        `;
    };
    reader.readAsDataURL(file);
};
