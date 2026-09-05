## Typography System

### Font Sizes (Fluid)

All font sizes use `clamp()` for responsive scaling. Reference as `var:preset|font-size|{slug}` or just the slug in a `fontSize` attribute.

| Slug | Size | Fluid Range |
|------|------|-------------|
| `x-small` | 0.95rem | 0.825–0.95rem |
| `small` | 1.05rem | 0.9–1.05rem |
| `base` | 1.165rem | 1–1.165rem |
| `medium` | 1.65rem | 1.2–1.65rem |
| `large` | 2.35rem | 1.5–2.35rem |
| `x-large` | 2.9rem | 1.875–2.9rem |
| `xx-large` | 3.75rem | 2.25–3.75rem |

> **Rule C-02**: Never use custom font sizes like `18px` or `2rem`. Always use a `fontSize` slug from the type scale above.

### Font Families

| Slug | Font | Use |
|------|------|-----|
| `primary` | Mona Sans | Default body + headings |
| `expanded` | Mona Sans Expanded | Wide, impactful headings |
| `condensed` | Mona Sans Condensed | Compact headings |
| `narrow` | Mona Sans Narrow | Tight, editorial headings |
| `monospace` | Monospace system stack | Code blocks |

Reference as `var:preset|font-family|{slug}`. Additional fonts can be installed via `ollie/manage-global-styles` → `install-font`.

### Font Weights (Custom)

Reference as `var:custom|fontWeight|{slug}`.

thin (100), extra-light (200), light (300), regular (425), medium (500), semi-bold (600), bold (700), extra-bold (800), black (900)

### Line Heights (Custom)

Reference as `var:custom|lineHeight|{slug}`.

none (1), tight (1.1), snug (1.2), body (1.5), relaxed (1.625), loose (2)

### Typography Presets

Pre-built typography combinations in `styles/typography/`. Each defines body + heading fonts, weights, and sometimes custom sizes.

| File | Body | Headings | Character |
|------|------|----------|-----------|
| `typography-preset-1` | Mona Sans | Mona Sans Expanded | Modern, wide headings |
| `typography-preset-2` | DM Sans | DM Sans (bold) | Geometric, neutral |
| `typography-preset-3` | Mona Sans | Big Shoulders | Display contrast |
| `typography-preset-4` | Space Grotesk | Space Grotesk | Monospace-inspired |
| `typography-preset-5` | Source Serif 4 | Montagu Slab | Serif + slab headings |
| `typography-preset-6` | Mona Sans | Fraunces (bold) | Modern + elegant serif |
| `typography-preset-7` | Source Serif 4 | Source Serif 4 (extra-bold) | Full serif |
| `typography-preset-8` | Mona Sans | Mona Sans (extra-bold) | Bold, tight headings |
| `typography-preset-9` | Mona Sans | Mona Sans Narrow (bold) | Narrow, editorial |
| `typography-preset-10` | Geist | Geist (semi-bold) | Modern tech |
