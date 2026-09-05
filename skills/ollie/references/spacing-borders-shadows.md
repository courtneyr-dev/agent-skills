# Spacing, Border Radius, and Shadows

## Spacing System

Fluid spacing presets. Reference as `var:preset|spacing|{slug}`.

| Slug | Value |
|------|-------|
| `small` | clamp(0.5rem, 2.5vw, 1rem) |
| `medium` | clamp(1.5rem, 4vw, 2rem) |
| `large` | clamp(2rem, 5vw, 3rem) |
| `x-large` | clamp(3rem, 7vw, 5rem) |
| `xx-large` | clamp(4rem, 9vw, 7rem) |
| `xxx-large` | clamp(5rem, 12vw, 9rem) |
| `xxxx-large` | clamp(6rem, 14vw, 13rem) |

> **Rule C-03**: Never use hardcoded spacing like `20px` or `3rem`. Always use `var:preset|spacing|{slug}` for padding, margin, and blockGap.

---

## Border Radius

Reference as `var:preset|border-radius|{slug}`.

| Slug | Value |
|------|-------|
| `xs` | 0.25rem |
| `sm` | 0.375rem |
| `md` | 0.5rem |
| `lg` | 0.75rem |
| `xl` | 1rem |
| `2xl` | 1.5rem |
| `full` | 100rem |

---

## Shadows

8 shadow presets: `small`, `medium`, `large`, `extra-large` (each in light and dark variants like `small-dark`). Reference as `var:preset|shadow|{slug}`.
