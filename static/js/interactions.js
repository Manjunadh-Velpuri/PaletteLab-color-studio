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
    }).catch(err => {
        console.error('Failed to copy: ', err);
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
};// ----------------------------------------
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
