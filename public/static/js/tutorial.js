/**
 * PaletteLab Interactive Tutorial Engine
 */

const TUTORIAL_STORAGE_KEY = 'palettelab_tutorial_completed';

const TUTORIAL_STEPS = [
    {
        id: "onboarding",
        title: "Welcome to PaletteLab! ✨",
        content: "Would you like a quick interactive tour to see how to extract and craft beautiful palettes?",
        target: null, // Centered
        btnPrimary: "Yes, show me around!",
        btnSkip: "Nah, I'm good."
    },
    {
        id: "text-extract",
        title: "1. Magic Text Extraction",
        content: "Just paste any text containing color codes (HEX, RGB, HSL) into this box, and click extract. We'll find them automatically! \n\nClick 'Next' to see it in action.",
        target: "#extract-form",
        onNext: () => {
            const input = document.getElementById("raw-text-input");
            if (input) {
                input.value = "Sunset vibes: #FF5E3A, rgb(255, 149, 0), hsl(48, 100%, 50%)";
                const submitBtn = document.querySelector('#extract-form button[type="submit"]');
                if (submitBtn) submitBtn.click();
            }
        }
    },
    {
        id: "random-palette",
        title: "2. Random Generation",
        content: "Feeling uninspired? Click this button to instantly generate a balanced, visually appealing palette.",
        target: "#random-palette-btn",
        onNext: () => {
             const btn = document.getElementById("random-palette-btn");
             if (btn) btn.click();
        }
    },
    {
        id: "add-color",
        title: "3. 2D Color Canvas",
        content: "Open an interactive 2D canvas to pick colors manually. Click anywhere in the color panel popup to add a color, and double-click a color to remove it.",
        target: "#add-color-btn"
    },
    {
        id: "photo-extract",
        title: "4. Photo Extraction",
        content: "Upload any photo here. We'll automatically cluster the pixels and extract the most dominant and vibrant colors.",
        target: "#photo-extract-wrapper",
        onNext: () => {
            // For the tutorial, we simulate a photo upload using the dummy route if desired,
            // or we just skip triggering it to not interrupt the flow with a file picker.
        }
    },
    {
        id: "visual-tweaks",
        title: "5. Visual Tweaks",
        content: "Customize how you view your palette. Switch between Layouts (like Chips, Orbs, Ribbons) or sort them by Hue, Saturation, or Luminance.",
        target: ".canvas-tools-left"
    },
    {
        id: "export",
        title: "6. Export & Go",
        content: "When you're happy with your palette, export it as a high-res PNG or clean vector SVG. That's it! You're ready to create.",
        target: ".canvas-tools-right",
        btnPrimary: "Finish Tour"
    }
];

class TutorialEngine {
    constructor() {
        this.currentStepIndex = 0;
        this.isActive = false;
        
        // UI Elements
        this.overlay = null;
        this.tooltip = null;
        this.highlightedElement = null;
    }

    init() {
        // Check if tutorial was already completed
        if (localStorage.getItem(TUTORIAL_STORAGE_KEY) === 'true') {
            return;
        }

        // Wait a bit before showing the prompt
        setTimeout(() => this.start(), 1500);
    }

    start() {
        if (this.isActive) return;
        this.isActive = true;
        this.currentStepIndex = 0;
        
        this.buildUI();
        this.renderStep();
    }

    buildUI() {
        // Create Overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'tutorial-overlay';
        document.body.appendChild(this.overlay);

        // Create Tooltip Bubble
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tutorial-tooltip';
        
        this.tooltip.innerHTML = `
            <h3 id="tut-title"></h3>
            <p id="tut-content" style="white-space: pre-wrap;"></p>
            <div class="tutorial-actions">
                <button class="tutorial-skip" id="tut-skip-btn">Skip</button>
                <div class="tutorial-nav">
                    <button class="tutorial-btn" id="tut-prev-btn">Prev</button>
                    <button class="tutorial-btn primary" id="tut-next-btn">Next</button>
                </div>
            </div>
        `;
        document.body.appendChild(this.tooltip);

        // Bind events
        document.getElementById('tut-skip-btn').addEventListener('click', () => this.end());
        document.getElementById('tut-prev-btn').addEventListener('click', () => this.prev());
        document.getElementById('tut-next-btn').addEventListener('click', () => this.next());

        // Fade in
        requestAnimationFrame(() => {
            this.overlay.classList.add('active');
            this.tooltip.classList.add('active');
        });
    }

    renderStep() {
        const step = TUTORIAL_STEPS[this.currentStepIndex];
        
        // Update texts
        document.getElementById('tut-title').textContent = step.title;
        document.getElementById('tut-content').textContent = step.content;
        
        const nextBtn = document.getElementById('tut-next-btn');
        const prevBtn = document.getElementById('tut-prev-btn');
        const skipBtn = document.getElementById('tut-skip-btn');

        nextBtn.textContent = step.btnPrimary || 'Next';
        skipBtn.textContent = step.btnSkip || 'Skip Tutorial';

        // Toggle Prev button
        prevBtn.style.display = (this.currentStepIndex === 0) ? 'none' : 'block';

        // Handle highlighting
        this.clearHighlight();
        
        if (step.target) {
            const targetEl = document.querySelector(step.target);
            if (targetEl) {
                targetEl.classList.add('tutorial-highlight');
                this.highlightedElement = targetEl;
                
                // Position tooltip near the element
                this.positionTooltip(targetEl);
            } else {
                this.positionTooltipCentered();
            }
        } else {
            this.positionTooltipCentered();
        }
    }

    positionTooltipCentered() {
        this.tooltip.style.top = '50%';
        this.tooltip.style.left = '50%';
        this.tooltip.style.transform = 'translate(-50%, -50%)';
    }

    positionTooltip(targetEl) {
        const rect = targetEl.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        
        // Try to place it below the element
        let top = rect.bottom + 16;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2); // center horizontally

        // Adjust if it goes offscreen horizontally
        if (left < 16) left = 16;
        if (left + tooltipRect.width > window.innerWidth - 16) {
            left = window.innerWidth - tooltipRect.width - 16;
        }

        // Adjust if it goes offscreen vertically
        if (top + tooltipRect.height > window.innerHeight - 16) {
            top = rect.top - tooltipRect.height - 16; // place above
        }

        this.tooltip.style.top = `${top}px`;
        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.transform = 'none';
    }

    clearHighlight() {
        if (this.highlightedElement) {
            this.highlightedElement.classList.remove('tutorial-highlight');
            this.highlightedElement = null;
        }
    }

    next() {
        const step = TUTORIAL_STEPS[this.currentStepIndex];
        if (step.onNext) {
            step.onNext();
        }

        if (this.currentStepIndex < TUTORIAL_STEPS.length - 1) {
            this.currentStepIndex++;
            this.renderStep();
        } else {
            this.end();
        }
    }

    prev() {
        if (this.currentStepIndex > 0) {
            this.currentStepIndex--;
            this.renderStep();
        }
    }

    end() {
        this.clearHighlight();
        this.isActive = false;
        
        if (this.overlay) this.overlay.classList.remove('active');
        if (this.tooltip) this.tooltip.classList.remove('active');

        setTimeout(() => {
            if (this.overlay) this.overlay.remove();
            if (this.tooltip) this.tooltip.remove();
        }, 300);

        // Save state so it doesn't show again
        localStorage.setItem(TUTORIAL_STORAGE_KEY, 'true');
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.tutorialEngine = new TutorialEngine();
    window.tutorialEngine.init();
});
