## Workflow Rules

1. **Always use existing presets.** Never hard-code `#hex` values in styles when a preset color exists. Never use raw `px`/`rem` for font sizes when a preset size exists.
2. **Always read before writing.** Use `list`, `get`, or `get-status` actions before making changes to avoid clobbering existing content.
3. **Check palettes first.** If the user wants a color change that matches an existing palette, switch to that palette rather than editing individual colors.
4. **Check button styles first.** If the user wants a different button look, recommend an existing button style before creating custom overrides.
5. **Check typography presets first.** If the user wants different fonts, see if a preset matches before adding custom font faces.
6. **Search for patterns before building from scratch.** Ollie's pattern library is extensive and design-consistent. Patterns are always preferable to hand-built block markup.
6b. **Prefer full-page designs over section composition.** When creating a page, use `ollie/create-page` with a broad query to find a complete page layout. Do not use `ollie/manage-patterns` to assemble sections unless the user explicitly requests a custom layout or no full-page design fits.
7. **Use the variable reference syntax** in theme.json: `"var:preset|color|primary"`, `"var:preset|font-size|large"`, `"var:preset|spacing|medium"`, etc.
8. **Respect color pairing rules.** When setting a background color, always set a compatible text color from the pairing rules above.
9. **Present choices to the user** — especially during setup wizards, show available options and let the user decide.
11. **The linter is your friend.** If markup is rejected, check that all colors, font sizes, and spacing use design tokens. Autofix issues labeled `snap-to-scale` are safe to proceed through.
