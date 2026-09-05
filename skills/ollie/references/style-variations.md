# Style Variations, Layout, and Key Files

## Style Variations

Complete design presets in `styles/`. Each bundles a color palette + typography + element overrides.

| Variation | File | Brand Color | Heading Font | Character |
|-----------|------|-------------|-------------|-----------|
| **Studio** | `studio.json` | #FF50A9 (pink) | Mona Sans (extra-bold) | Creative, rounded buttons |
| **Startup** | `startup.json` | #454DFF (blue) | Mona Sans Expanded (medium) | Tech, clean |
| **eCommerce** | `ecommerce.json` | #FF6637 (orange) | Geist (semi-bold) | Warm, commercial |
| **Creator** | `creator.json` | #5A20FF (purple) | Mona Sans Condensed (bold) | Expressive, compact |
| **Agency** | `agency.json` | #495148 (sage) | Mona Sans Narrow (bold) | Uppercase, neon accents, editorial |

When a user asks to "switch to the agency style" or "use the startup variation," read the corresponding file and apply its settings.

---

## Layout

- Content width: 740px
- Wide width: 1260px

---

## Key Files

| What | Where |
|------|-------|
| Main config | `theme.json` |
| Color palettes | `styles/colors/*.json` |
| Button styles | `styles/blocks/button/*.json` |
| Typography presets | `styles/typography/*.json` |
| Style variations | `styles/*.json` (agency, creator, ecommerce, startup, studio) |
| Fonts | `assets/fonts/` |
