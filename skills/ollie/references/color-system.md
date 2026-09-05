## Color Palette System

### The 11 Color Slots

Every color palette in Ollie defines exactly these 11 slots. The **slug** is what you reference in block attributes and theme.json styles; the **name** is the human-readable label.

| Name | Slug | Role | Usage Notes |
|------|------|------|-------------|
| **Brand** | `primary` | Main brand color | The hero color. "Use my brand color" = this. |
| **Brand Accent** | `primary-accent` | Light tint of brand | Pairs with Brand. Use for light backgrounds behind brand-colored text. |
| **Brand Alt** | `primary-alt` | Secondary brand color | Pairs with Brand Alt Accent. A complementary or secondary color. |
| **Brand Alt Accent** | `primary-alt-accent` | Dark companion to Brand Alt | Text color that works on Brand Alt backgrounds and vice versa. |
| **Contrast** | `main` | Primary dark/black | Always a very dark color. Used for text, dark sections, footers. |
| **Contrast Accent** | `main-accent` | Light color for dark backgrounds | An off-white/light that is readable on `main` backgrounds. |
| **Base** | `base` | White / page background | Always white or near-white. The default page background. |
| **Base Accent** | `secondary` | Muted text color | A tinted mid-tone — good for secondary text, subtle highlights, bylines. |
| **Tint** | `tertiary` | Very light gray background | Used for surfaces, cards, alternating sections. "Light background" often means this. |
| **Border Base** | `border-light` | Light border color | Standard border for cards, inputs, dividers. |
| **Border Contrast** | `border-dark` | Darker border color | Heavier borders, active states, emphasis. |

> **Rule C-01**: Never use hardcoded hex/rgb/hsl colors in block attributes. Always reference a design token slug. The design linter will reject hardcoded values.

### Color Pairing Rules

These pairs are designed to work together (foreground/background swappable):
- **Brand** (`primary`) + **Brand Accent** (`primary-accent`)
- **Brand Alt** (`primary-alt`) + **Brand Alt Accent** (`primary-alt-accent`)
- **Contrast** (`main`) + **Contrast Accent** (`main-accent`)
- **Base** (`base`) + **Contrast** (`main`) — white bg, dark text
- **Tint** (`tertiary`) + **Contrast** (`main`) — light gray bg, dark text

When setting a background color, always set a compatible text color from the pairing rules above.

### Interpreting User Requests

| User says... | Use this slug |
|-------------|---------------|
| "brand color" / "primary color" / "main color" | `primary` |
| "secondary color" / "accent color" | `primary-alt` |
| "dark background" / "dark section" | `main` (bg) + `base` or `main-accent` (text) |
| "light background" | `tertiary` (tint) or `base` (white) |
| "white background" | `base` |
| "muted text" / "subtle text" | `secondary` |
| "border" | `border-light` (default) or `border-dark` (emphasis) |

### CSS Variable Pattern

In block attributes and theme.json styles, reference colors as:
```
"var:preset|color|primary"
```
This becomes the CSS variable `--wp--preset--color--primary` at render time.

### Available Color Palettes

Pre-built palettes in `styles/colors/`. To switch palettes, apply the palette's JSON to `settings.color.palette` in theme.json or use the Site Editor.

| File | Title | Brand Color | Character |
|------|-------|------------|-----------|
| `blue.json` | Blue | #1b4cff | Professional, tech |
| `green.json` | Green | #00786f | Nature, health |
| `pink.json` | Pink | #FF50A9 | Creative, playful |
| `orange.json` | Orange | #FF6637 | Warm, eCommerce |
| `red.json` | Red | #F82F58 | Bold, energetic |
| `teal.json` | Teal | #45A1B8 | Calm, modern |
| `neon.json` | Neon | #495148 (sage + lime accents) | Agency, bold |

**When a user asks to "switch to blue" or "use the blue palette":** read `styles/colors/blue.json` and apply its `settings.color.palette` array to the main `theme.json`. Do NOT create new colors — use the existing palette file.
