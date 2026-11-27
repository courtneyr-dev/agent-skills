# Keyboard criteria and tools

Source: W3C, "Web Content Accessibility Guidelines (WCAG) 2.2"
Location: https://www.w3.org/TR/WCAG22/
Version or retrieved date: W3C Recommendation, 5 October 2023; not re-fetched at authoring time
Rights: W3C Document License; cite, do not copy

Source: Deque, axe-core
Location: https://github.com/dequelabs/axe-core
Version or retrieved date: 4.13.0, the copy resolved from the local node_modules on 2026-11-25
Rights: MPL-2.0; used as an installed library, not copied

Source: Microsoft, Playwright
Location: https://playwright.dev/
Version or retrieved date: 1.62.1 with Chromium 151.0.7922.34, resolved locally on 2026-11-25
Rights: Apache-2.0; used as an installed library, not copied

## Criteria the walk checks

| Rule | WCAG 2.2 success criterion | Level | What the walk observes |
|---|---|---|---|
| keyboard-unreachable | 2.1.1 Keyboard | A | A control with its own click listener or an interactive role never receives focus |
| keyboard-trap | 2.1.2 No Keyboard Trap | A | Tab never reaches the end-of-page sentinel within `--max-tabs`, and Escape doesn't release focus |
| focus-order-positive-tabindex | 2.4.3 Focus Order | A | A positive tabindex; a human confirms the order (non-blocking) |
| focus-not-visible | 2.4.7 Focus Visible | AA | Computed outline, box-shadow, border colors, background, color and text decoration are identical focused and unfocused |

## Why axe-core is the baseline, not the test

axe-core checks rules it can evaluate from the DOM and computed styles in one pass. Its rule list has no check that presses Tab, so a script that cancels Tab inside a widget, a `div` that only listens for clicks, and `outline: none` on `:focus` pass the scan. On `fixtures/donate-before.html` axe-core 4.13.0 reported 0 violations; the walk found 3 invisible-focus links, 1 click-only switch and 1 trap.

## What this doesn't establish

WCAG 2.4.11 Focus Not Obscured and 2.4.13 Focus Appearance need size, contrast and overlap measurements the walk doesn't take. Screen-reader output, Shift+Tab order, and flows behind dialogs need their own runs. None of this replaces testing with disabled users.
