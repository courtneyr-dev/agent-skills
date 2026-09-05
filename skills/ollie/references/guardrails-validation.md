## Guardrails & Validation

Ollie Abilities runs a **two-layer design linter** on all block markup before writing to WordPress.

### Layer 1 — Mutation Constraints
- **C-01**: All colors must reference registered design token slugs (no hardcoded hex/rgb/hsl)
- **C-02**: All font sizes must use the type scale slug or `var:preset|font-size|{slug}`
- **C-03**: All spacing (padding, margin, blockGap) must use `var:preset|spacing|{slug}`

### Layer 2 — Schema Validation
- **S-01**: Block markup must be valid block grammar (parseable by `parse_blocks`)
- **S-02**: Required block attributes must be present
- **S-03**: Attribute types and enum values must be valid
- **S-04**: Blocks that don't support innerBlocks must not contain them
- **S-05**: Inner block types must be valid per `allowedBlocks`
- **S-06**: No duplicate block anchor IDs
- **S-08**: No empty required content fields

### Hard Rules (Always Follow)
1. **Never use `core/html` (Custom HTML block)**. Build everything with core blocks and Ollie patterns.
2. **Never hardcode colors, font sizes, or spacing** — always use design tokens.
3. **Never use inline `<style>` tags or inline CSS** in block content.
4. **Always use core blocks** (`core/group`, `core/columns`, `core/cover`, `core/heading`, `core/paragraph`, `core/buttons`, `core/image`, `core/list`, `core/separator`, etc.).
5. **Prefer Ollie patterns over building from scratch** — search for patterns first via `ollie/manage-patterns`.
6. **Use Global Styles** for site-wide changes instead of per-block overrides.
7. **Use Global Styles or CSS classes** for reusable custom styles instead of inline styling.

If the linter rejects markup, check that all colors, font sizes, and spacing use design tokens. Autofix issues labeled `snap-to-scale` are safe to proceed through.
