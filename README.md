# PaletteLab - Color Studio 🎨

*For Freelance - UI/UX Designers, Frontend Developers and Professional Design Teams.*

Hi everyone! I am Manjunadh Velpuri, and this is my first real project on GitHub. I made this small tool called PaletteLab to help with colors and palettes. I'm still learning, so there might be a few bugs here and there. Do try it out and feel free to point them out!

## What it does ✨
Right now, the web app can do a few cool things:
- **Extract colors from text**: You can paste text with HEX, RGB, or HSL codes, and it will pull all the colors out.
- **Extract colors from photos**: Upload an image, and it finds the main colors used in it.
- **Random palette generator**: Don't know what colors to use? It can generate random palettes based on different styles and themes.
- **Tweak colors**: You can easily shade or tint the colors to make them lighter or darker.
- **Convert formats**: There's a Conversion Table mode that shows your colors in HEX, RGB, HSL, HSV, CMYK, and LAB formats.
- **Export**: You can download your palette as a PNG or SVG image.

## Tech used 💻
I kept the stack pretty simple to focus on learning:
- **Python**: For all the core logic and color math.
- **FastHTML**: Used this to build the web UI quickly without writing a ton of Javascript. It's really fast!
- **Pillow**: For image processing when extracting colors from photos.

## How to run it 🚀
If you want to run this on your own machine, just follow these steps:

1. Clone this repository:
   ```bash
   git clone https://github.com/Manjunadh-Velpuri/PaletteLab-color-studio.git
   cd PaletteLab-color-studio
   ```
2. Install the required packages. I recommend doing this in a virtual environment:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the main file:
   ```bash
   python api/index.py
   ```
4. Open your browser and go to the link shown in the terminal (usually `http://localhost:5001`).

## Why I built this 💡
I always found it slightly annoying to switch between different tabs just to convert a color code or grab a palette from a photo. So, I decided to build something that puts all these basic features in one place. It was also a great excuse for me to try out Python for web development instead of just simple scripts!

## Two Modes. One Workflow. 🔄
I wanted the app to feel fast and simple. When you're inside PaletteLab, the interface hides the scaffolding—no watermarks, no messy titles, just raw color data so we can prioritize speed and clarity. 

But when you export your palette as a PNG or SVG, the app automatically generates a professionally structured color matrix for you! It includes the naming, hex values, and a really clean visual hierarchy. It basically gives you a design-system-ready deliverable without having to manually set up the layout yourself.



## Project Structure 📁
Here is a quick overview of what each folder and file in this project does:

```text
PaletteLabWeb/
├── api/                                  # Serverless entry point for Vercel
│   └── index.py                          # Main FastHTML web application and API routes
│
├── core_logic/                           # Backend Python color math and processing
│   ├── core/                             # Core algorithms and utilities
│   │   ├── color_utils.py                # Math conversions (RGB, LAB, CMYK, etc.)
│   │   ├── exporter.py                   # High-res PNG/SVG export generation
│   │   └── renderer.py                   # Pillow-based visual layout engine (cards, honeycomb, etc.)
│   │
│   ├── extraction/                       # Image processing logic
│   │   └── photo_extractor.py            # Extracts color palettes from uploaded images
│   │
│   ├── generatePalette/                  # Palette generation and naming
│   │   ├── color_matcher.py              # Nearest-neighbor color naming database
│   │   ├── generate_cache.py             # Caches generated palettes
│   │   └── palette_generator.py          # Procedural color harmony generation
│   │
│   └── parsers/                          # Text parsing logic for different formats
│       ├── cmyk_parser.py                # Parses CMYK text inputs
│       ├── hsl_parser.py                 # Parses HSL text inputs
│       ├── hsv_parser.py                 # Parses HSV text inputs
│       ├── lab_parser.py                 # Parses LAB text inputs
│       └── rgb_parser.py                 # Parses RGB text inputs
│
├── static/                               # Static assets served to the client
│   ├── css/                              # Stylesheets (glassmorphism UI)
│   ├── fonts/                            # Bundled typography (Inter, JetBrains, LeagueSpartan)
│   ├── icons/                            # Vector SVG icons for the UI
│   ├── js/                               # Frontend javascript (interactions)
│   └── themes.json                       # JSON configuration for UI color themes
│
└── web_ui/                               # HTML Component rendering logic
    ├── components/                       # Reusable UI widgets
    │   ├── canvas.py                     # Main workspace and toolbar
    │   ├── color_picker_modal.py         # Hex color picker dialog
    │   ├── color_row.py                  # Individual color row item
    │   ├── conversion_table.py           # Multi-format conversion matrix
    │   ├── layout.py                     # Base HTML shell and head tags
    │   ├── modals.py                     # General modal components
    │   └── photo_modal.py                # Image upload and extraction dialog
    │
    ├── routes/                           # (Additional HTMX routing handlers)
    └── theme_loader.py                   # Loads and parses themes.json
```

## Future Scope 🔭
Since I'm still learning, I want to keep improving this. Here are some ideas I haven't built yet but want to add soon:
- **Live preview mockups**: show the palette applied to a sample UI (buttons, card, small layout) so you can judge how it'd actually look used, not just as flat swatches.
- **A contrast checker**: to see if text colors are accessible on background colors.
- **More beautiful layouts**: for exporting palettes (like a moodboard style).
- **Better mobile support**: so it looks nice on phones.
---

### Author 👨‍💻

<a href="https://github.com/Manjunadh-Velpuri">
  <img src="https://img.shields.io/badge/Manjunadh%20Velpuri-181717?style=for-the-badge&logo=github&logoColor=white" height="28" />
</a>

Built with ❤️ — feel free to reach out, open an issue, or contribute!

---

## License 📄
This project is under the [MIT License](LICENSE) — feel free to use it, learn from it, or build on it.
