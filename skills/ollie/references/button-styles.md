## Button Styles

Pre-built button styles in `styles/blocks/button/`. These are registered block styles for `core/button`. Apply via `className: "is-style-{slug}"`.

| Style | Slug | Background | Text |
|-------|------|------------|------|
| Brand | `button-brand` | `primary` | `base` |
| Brand Alt | `button-brand-alt` | `primary-alt` | `primary-alt-accent` |
| Dark | `button-dark` | `main` | `base` |
| Light | `button-light` | `base` | `main` |
| Tint | `secondary-button` | `tertiary` | `main` |

Default button (set in theme.json): `main` background, `base` text, 5px border-radius, font-weight 500, font-size small, padding 0.6em 1em.

**When a user asks to change a button color**, first check if one of these existing styles matches. If so, apply the variation by setting `className` in **both** the block comment JSON **and** the inner HTML `class` attribute. Both must match or the editor won't reflect the style.

**Correct example** — applying the "Brand" button style:

```html
<!-- wp:button {"className":"is-style-button-brand"} -->
<div class="wp-block-button is-style-button-brand"><a class="wp-block-button__link wp-element-button">Get Started</a></div>
<!-- /wp:button -->
```

**Wrong** — class only on the inner div (front-end works, editor does not):

```html
<!-- wp:button {} -->
<div class="wp-block-button is-style-button-brand"><a class="wp-block-button__link wp-element-button">Get Started</a></div>
<!-- /wp:button -->
```

The `className` in the block comment is what WordPress uses to set the active variation in the editor sidebar. Without it, the editor shows no style selected even though the front-end renders correctly.

When combining with other attributes like `width`, merge them:

```html
<!-- wp:button {"width":100,"className":"is-style-button-brand"} -->
<div class="wp-block-button has-custom-width wp-block-button__width-100 is-style-button-brand"><a class="wp-block-button__link wp-element-button">Get Started</a></div>
<!-- /wp:button -->
```
