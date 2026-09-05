---
name: prop-for-that
description: "Use when building web or PWA UI that must react in CSS to runtime state CSS can't see (pointer, size, visibility, network, battery, media, form validity, image color), or when the user says 'react to X in CSS' or 'what JS knows that CSS doesn't'. Checks native CSS first."
---

# prop-for-that — runtime state as CSS custom properties

CSS can't see most of what the browser already knows: where the pointer is, how
big an element is, whether you're offline, battery level, whether a video is
playing, how full a textarea is. `prop-for-that` runs one tiny batched loop that
writes that state into CSS custom properties (`--live-*` reactive, `--const-*`
write-once), so your stylesheets react with plain `var()`/`calc()` (continuous
values) or `@container style()` (discrete values) — no per-element event
handlers, no JS in the animation path.

Zero deps, TypeScript, SSR-safe, MIT. **Pinned to `prop-for-that@0.7.2` — it's
pre-1.0, so pin the version and re-read the changelog before bumping.** Full
catalog, gotchas, and complete recipes live in `reference.md` (read it before
writing CSS against these props).

## Step 1 — check native CSS FIRST (this is the rule, not a footnote)

Most "JS knows, CSS doesn't" is *already* native CSS. Don't add a JS dependency
for anything in this list — use the platform:

| You want… | Use native CSS | Not the library |
| --- | --- | --- |
| React to scroll position/progress | `animation-timeline: scroll()` / `view()` | ✅ |
| Element size → layout | container queries + `cqw/cqh` units | ✅ |
| Viewport size → layout | media queries + `dvh/svh/lvh` units | ✅ |
| Dark/light mode | `prefers-color-scheme`, `light-dark()` | ✅ |
| Reduce motion | `prefers-reduced-motion` | ✅ |
| Hover/touch capability | `@media (hover)`, `(pointer: fine/coarse)` | ✅ |
| Per-field validity styling | `:user-valid` / `:user-invalid` / `:required` | ✅ |
| Installed-PWA styling | `@media (display-mode: standalone)` | ✅ |
| "Form has an invalid field" | `form:has(:invalid)` | ✅ |

Reach for the library **only** for state the platform genuinely can't expose:

- **Pointer position** as numbers (x/y, ratios) — `pointer`, `pointer-local`
- **Connectivity** — `online`, `network` (downlink/rtt/save-data/effective-type)
- **Device** — `battery`, `fps`, `orientation`, `motion`, `geo`, `cpu-pressure`
- **Page state** — `page-focused`, `page-visible`, `nav-type`, `visual-viewport`
  (pinch-zoom/offset — the one viewport read CSS *can't* do)
- **Numeric reads CSS lacks** — element size *as a variable* (`size`), char
  count / fill % (`field`), form completion counts (`form-state`), select index
  (`select`), color-input value (`color-input`), image natural size/loaded/broken
  (`img`), scroll velocity & direction (`scroll-velocity`), clock (`clock`)
- **Media** — playback time/paused/volume (`media`), dominant/accent color of an
  image or video (`img-color`, `video-color`)

> Edge note: scroll *direction* has a Chromium-only `@container scroll-state(scrolled:)`
> condition and there's a Chromium-only scroll-velocity approximation, but neither
> is Baseline — use `scroll-velocity` for portable, numeric values.

## Step 2 — is this even the right kind of project?

- **Strong fit:** a live-browser PWA or site (this is the home — e.g. the Outpost
  PWA). The whole value is *live* runtime state.
- **Caveated fit — WordPress / public front-ends:** every effect ships JS to
  every visitor. The `/head` constants are cheap and fine site-wide; live sources
  only for a justified, measured effect. The block *editor* is freer than the
  front end. Justify per-effect against the performance budget.
- **Non-fit — skip entirely:** deterministic renderers (Remotion and other
  frame-by-frame video), SSR-only output with no client runtime, Node CLIs.
  Pointer/battery/network mean nothing in a pre-rendered frame.

## Step 3 — install and wire it

```bash
npm i prop-for-that@0.7.2
```

| Entry | When |
| --- | --- |
| `prop-for-that/auto` | Declarative. `<script type="module">import 'prop-for-that/auto'</script>` then add `data-props-for="key …"` to elements (globals on `<html>`). Lazy-loads each plugin chunk on first use. Must be a module. |
| `prop-for-that` | Imperative — `propsFor()`, `register()`, `configure()`. Use for shadow-DOM (auto only sees light DOM) and explicit teardown. |
| `prop-for-that/head` | FOUC-safe `--const-*` (scrollbar width, DPR, cores) written inline before first paint. Inline a synchronous build in `<head>`. |

For Vite/Preact apps (like Outpost), `import 'prop-for-that/auto'` once at entry,
then drive styling from attributes — see the recipes in `reference.md`.

## Spotlight recipes (full copy-paste versions in `reference.md`)

1. **Offline / save-data banner + network-aware imagery** — `online` + `network`
   on `<html>`; discrete booleans → `@container style(--live-online: 0)` /
   `style(--live-net-save-data: 1)` drop heavy imagery, show a banner. Pure CSS.
2. **Pointer-reactive card tilt + size-aware text** — `pointer` (global) +
   `size` (on the card); continuous ratios → `rotateY(calc((var(--live-pointer-x-ratio) - .5) * 16deg))`.
3. **Char counter / fill bar + submit-gating** — `field` on a wrapper (so the
   sibling counter inherits its vars), `form-state` on the `<form>`;
   `inline-size: calc(var(--live-fill-pct) * 100%)` and unlock the button under
   `@container style(--live-all-valid: 1)`.
4. **FOUC-safe scrollbar gutter + DPR** — `/head` constants; reserve
   `calc(var(--const-scrollbar-w) * 1px)`, crisp hairlines with `calc(1px / var(--const-dpr))`.

## Five gotchas that bite (full list in `reference.md`)

1. **Custom properties inherit downward only.** Element-scoped vars land on the
   bound element — to let *siblings* react, bind a common ancestor. (`field` /
   `range` help: bind the wrapper, they find the inner `<input>`.)
2. **Right consumer for the value.** Continuous numbers → `var()` + `calc()`.
   Discrete/boolean/integer → `@container style()`, which matches on **equality
   only** (`style(--x < 5)` isn't stable) — emit booleans/tiers for thresholds.
3. **Values are unitless.** Multiply by `1px` / `1deg` / `100%` in CSS.
4. **Global `--live-*` go into an adopted stylesheet,** not inline `<html>` style
   — read computed style, not `documentElement.style`.
5. **`auto` sees light DOM only** and loads plugin chunks only from verbatim CDNs
   (unpkg/jsDelivr file paths), not rewriting ones (esm.sh, `+esm`).

## Performance posture (maps to the Code Output Verification Checklist)

One `requestAnimationFrame` flush per frame, write-on-change diffing, shared
observers, element sources paused off-screen, whole loop frozen while the tab is
hidden, `configure({ liveHz: 30 })` to throttle. **Strong** on JS-minimization
(JS only samples; CSS does the reacting), complexity (zero deps, platform
primitives), and trade-off honesty. **Watch:** it *is* client JS; per-frame style
recalc scales with how many `--live-*` your selectors consume; `pointer` is
high-frequency (drive expensive transforms sparingly); it ships **no
observability** — wire your own INP / Long-Animation-Frame RUM if an effect is
load-bearing.

Links: [docs](https://prop-for-that.netlify.app/docsite/) ·
[llms.txt](https://prop-for-that.netlify.app/llms.txt) ·
[repo](https://github.com/argyleink/prop-for-that)
