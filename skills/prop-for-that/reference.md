# prop-for-that — full reference

Companion to `SKILL.md`. Catalog, native-CSS-first decision table, gotchas, and
complete copy-paste recipes. Pinned to **`prop-for-that@0.7.2`** (pre-1.0 — the
property catalog can shift between minor releases; re-check the changelog before
bumping). Verified against the library's own `llms.txt` on 2026-06-14.

## Native-CSS-first decision table

Spend the JS budget only where the platform genuinely can't help. Columns:
**state → native CSS today → verdict.**

| State | Native CSS today | Verdict |
| --- | --- | --- |
| Scroll position / progress | `animation-timeline: scroll()`; `@container scroll-state(scrolled)` (Chrome 144+) | **Native for animations.** No numeric scroll-position read in a var — library only if you need the number. |
| Scroll velocity & direction | Direction via `@container scroll-state(scrolled: top/bottom)` (Chromium-only, not Baseline); velocity approximation via scroll-driven anim + `@property` (Chromium-only) | **Library** (`scroll-velocity`) for portable, numeric velocity/direction. |
| Viewport width/height (layout) | `@media (width/height/aspect-ratio)`, `vw/vh/dvh/svh/lvh/vmin/vmax` | **Native.** |
| Visual viewport (pinch-zoom scale/offset) | none (CSS units track the *layout* viewport only) | **Library** (`visual-viewport`). The one viewport read CSS can't do. |
| Element size → layout | container queries + `cqw/cqh/cqi/cqb` units | **Native.** |
| Element size *as a number/variable* | none (queries gate at breakpoints; no numeric read) | **Library** (`size` → `--live-w/-h/-aspect`). |
| Element visibility in viewport | `animation-timeline: view()`, `content-visibility: auto` | **Native for scroll-into-view animation.** No boolean/ratio for general selectors → library (`visibility`) if you need a flag. |
| Pointer position (global / in-element) | none (`:hover` is binary, no coordinates) | **Library** (`pointer`, `pointer-local`). |
| Pointer type / hover capability | `@media (hover)`, `(pointer: fine/coarse)`, `any-hover` | **Native** (can't tell pen from mouse — both `fine`). |
| Color scheme (dark/light) | `prefers-color-scheme`, `light-dark()`, `color-scheme` | **Native.** |
| Reduced motion | `prefers-reduced-motion` | **Native.** |
| Reduced data / save-data | `prefers-reduced-data` is spec'd but **unimplemented** anywhere | **Library** (`network` → `--live-net-save-data`). |
| Online / offline | none | **Library** (`online`). |
| Network speed (downlink/rtt/effective-type) | none | **Library** (`network`). |
| Battery level & charging | none | **Library** (`battery`). |
| Page focus vs tab visibility | `:focus-within` is element focus only | **Library** (`page-focused`, `page-visible`). |
| Navigation type (reload/back-forward) | none | **Library** (`nav-type`). |
| FPS / frame rate | none (`@media (update)` is display capability, not achieved FPS) | **Library** (`fps`). |
| Device orientation / motion sensors | `@media (orientation)` is viewport aspect, *not* tilt | **Library** (`orientation`, `motion`) — permission-gated. |
| Geolocation | none | **Library** (`geo`) — permission-gated. |
| CPU / compute pressure | none | **Library** (`cpu-pressure`) — Chromium-only. |
| Media playback (time/duration/paused/volume) | none (no `:playing`/`:paused`) | **Library** (`media`). |
| Per-field validity *state* | `:user-valid`, `:user-invalid`, `:required`, `:in-range`, `:out-of-range`, `:placeholder-shown` | **Native** for state. |
| Char count / fill % of a field | none (`:placeholder-shown` is empty/not-empty only) | **Library** (`field` → `--live-length/-remaining/-fill-pct`). |
| Form-level valid/invalid counts, completion | `form:has(:invalid)` is a boolean only — no counting | **Library** (`form-state`). |
| Select index / option count | none (`sibling-index()` counts DOM siblings, not the chosen option) | **Library** (`select`). |
| Color-input value | none | **Library** (`color-input`). |
| Image natural size / loaded / broken | `aspect-ratio` is declared, not measured; no `:loaded`/`:broken` | **Library** (`img`). |
| Dominant / accent color of image or video | none | **Library** (`img-color`, `video-color`). |
| Clock / time of day | none (animations are relative, not wall-clock) | **Library** (`clock`). |
| Scrollbar width / DPR / core count | DPR via `@media (resolution)` buckets; `scrollbar-gutter`/`scrollbar-width` for layout; nothing for cores | **Library** (`/head` constants) for exact numbers. |
| Installed-PWA (display-mode) | `@media (display-mode: standalone/…)` | **Native** (for the `beforeinstallprompt` *event* you still need JS). |

## Variable catalog

All names are the full property. Reactive → `--live-`; write-once → `--const-`.
Values are unitless numbers unless noted. Plugin **import** names are camelCase;
the **key** for `propsFor` / `data-props-for` is the dashed form.

### Core sources (in the main bundle)

| key | scope | properties |
| --- | --- | --- |
| `viewport` | global | `--live-vw`, `--live-vh` |
| `size` | element | `--live-w`, `--live-h`, `--live-aspect` (w/h) |
| `visibility` | element | `--live-visible` (1/0, whole element in viewport), `--const-has-entered` (1/0, latches once fully in view, never resets) |
| `range` | element | `--live-value`, `--live-value-pct` (0–1). Bind the `<input>` or a container holding one. |

### Head constants (`prop-for-that/head`)

| property | value |
| --- | --- |
| `--const-scrollbar-w` | scrollbar width in px |
| `--const-scrollbar-thin-w` | scrollbar width with `scrollbar-width: thin` (= `--const-scrollbar-w` where unsupported) |
| `--const-dpr` | `devicePixelRatio` |
| `--const-cores` | `navigator.hardwareConcurrency` |
| `--const-mem` | `navigator.deviceMemory` in GiB (Chromium-only, coarse; `0` elsewhere) |

### Plugins (`prop-for-that/plugins`)

| import | key | scope | properties / notes |
| --- | --- | --- | --- |
| `pointer` | `pointer` | global | `--live-pointer-x`, `--live-pointer-y`, `--live-pointer-x-ratio` (0–1), `--live-pointer-y-ratio` (0–1). High-frequency (per `pointermove`). |
| `scrollVelocity` | `scroll-velocity` | global | `--live-scroll-velocity` (signed px/frame), `--live-scroll-direction` (1/-1/0) |
| `online` | `online` | global | `--live-online` (1/0) |
| `pageFocused` | `page-focused` | global | `--live-page-focused` (1/0 — frontmost + focused) |
| `pageVisible` | `page-visible` | global | `--live-page-visible` (1/0 — `document.visibilityState`; a visible tab can still be unfocused) |
| `navType` | `nav-type` | global | `--const-nav-type` (write-once string: `navigate`/`reload`/`back_forward`/`prerender`) |
| `network` | `network` | global | `--live-net-downlink`, `--live-net-rtt`, `--live-net-save-data` (1/0), `--live-net-type` (slow-2g=1…4g=4, else 0) |
| `battery` | `battery` | global | `--live-battery-level` (0–1), `--live-battery-charging` (1/0) |
| `clock` | `clock` | global | `--live-now` (epoch s), `--live-hours`, `--live-minutes`, `--live-seconds` |
| `fps` | `fps` | global | `--live-fps` |
| `visualViewport` | `visual-viewport` | global | `--live-vvp-scale`, `--live-vvp-offset-top`, `--live-vvp-height` |
| `orientation` | `orientation` | global | `--live-orient-alpha/-beta/-gamma` (deg) — permission-gated (iOS gesture) |
| `motion` | `motion` | global | `--live-accel-x/-y/-z` (m/s²) — permission-gated (iOS gesture) |
| `geo` | `geo` | global | `--live-geo-lat/-lng/-accuracy` (m) — permission-gated |
| `cpuPressure` | `cpu-pressure` | global | `--live-cpu-pressure` (nominal=0, fair=1, serious=2, critical=3) — Chromium-only, secure context + `compute-pressure` policy |
| `pointerLocal` | `pointer-local` | element | `--live-local-pointer-x-ratio`, `--live-local-pointer-y-ratio` (0–1 within element), `--live-local-pointer-inside` (1/0) |
| `media` | `media` | element | `--live-current-time`, `--live-duration`, `--live-progress` (0–1), `--live-paused` (1/0), `--live-volume` (0–1) |
| `field` | `field` | element | `--live-length`, `--live-empty` (1/0), `--live-valid` (1/0); per-reason validity flags (each 1/0) `--live-value-missing`, `--live-type-mismatch`, `--live-pattern-mismatch`, `--live-too-long`, `--live-too-short`, `--live-range-underflow`, `--live-range-overflow`, `--live-step-mismatch`, `--live-bad-input`, `--live-custom-error`; with `maxlength`: `--live-remaining`, `--live-fill-pct` (0–1) |
| `select` | `select` | element | `--live-index` (-1 if none), `--live-option-count`, `--live-index-pct` (0–1), `--live-value-num`, `--live-selected-count`, `--live-selected-pct` (0–1) |
| `colorInput` | `color-input` | element | `--live-color` (sRGB hex; typed mode registers it `<color>`) |
| `fieldState` | `field-state` | element | `--live-dirty`/`--live-pristine` (latches), `--live-touched`/`--live-untouched` (latches), `--live-changed` (un-latches), `--live-submitted`. Bind a field for its state, or a `<form>`/wrapper for the aggregate. |
| `formState` | `form-state` | element | `--live-field-count`, `--live-valid-count`, `--live-invalid-count`, `--live-all-valid` (1/0 submit gate), `--live-completion` (0–1). Bind a `<form>`/wrapper. |
| `img` | `img` | element | `--live-natural-w`, `--live-natural-h` (px), `--live-loaded` (1/0), `--live-broken` (1/0) |
| `imgColor` | `img-color` | element | `--live-img` (dominant), `--live-img-accent`, `--live-img-dark`, `--live-img-light`, `--live-img-avg`, `--live-img-temp` (−1 cool…+1 warm). Single sRGB hex each. Cross-origin needs `crossorigin` + CORS. |
| `videoColor` | `video-color` | element | `--live-video` (dominant), `--live-video-accent`. ~4 Hz on `requestVideoFrameCallback`. Cross-origin needs `crossorigin` + CORS. |

## API (imperative)

```ts
import { configure, register, unregister, isRegistered, propsFor, unbind, reset, pause, resume } from 'prop-for-that'

configure(opts)                 // call ONCE before any propsFor() (prefixes, typed, root, liveHz)
register(source)                // add a plugin/custom source by key
propsFor(keys)                  // global → writes to :root
propsFor(target, keys)          // element/NodeList/array → writes vars on the target(s)
unbind(target, keys?)           // detach some/all
reset()                         // tear down every binding + shared observers
pause() / resume()              // freeze / unfreeze the loop (values hold steady)
```

`configure({ typed: true })` registers each `--live-*` with `@property` so it
interpolates (consumers add `transition`/`@keyframes`). One-way door, `inherits:
true`, feature-detected. Markup equivalent under `auto`: `<html data-props-typed>`.

## Gotchas (read before writing CSS)

1. **Custom properties inherit downward only.** Element-scoped vars land on the
   bound element. For *siblings* to react, bind a common ancestor. `range` and
   `field` help: bind the wrapper, they find the inner `<input>` and write on the
   wrapper.
2. **Pick the right consumer.** Continuous numbers → `var()` + `calc()`.
   Discrete/boolean/integer → `@container style()`, **equality only**
   (`style(--x < 5)` isn't stable). Emit booleans/tiers for thresholds. Every
   element is a style-query container by default — no `container-type` needed.
3. **`visibility` is binary + latched, not a ratio.** No continuous visible-ratio
   and no scroll-position source — use native `animation-timeline: scroll()/view()`
   for continuous scroll-driven effects.
4. **Values are unitless.** Multiply by `1px`, `1deg`, `100%`, etc.
5. **Configure prefixes before attaching.** `configure({ livePrefix, constPrefix })`
   must run before any `propsFor()`.
6. **Typed `@property` is opt-in and one-way.** No unregister; global per
   `@property` name. Set initials via `configure({ typed: true, defaults: { 'pointer-x-ratio': 0.5 } })`.
7. **Permission-gated plugins** (`orientation`, `motion`, `geo`) and unsupported
   APIs feature-detect and no-op — registering them is always safe. iOS may need a
   user gesture. `cpu-pressure` is Chromium-only (secure context + policy).
8. **Global writes land in an adopted stylesheet,** not inline `<html>` style.
   Read computed style, not `documentElement.style`. Falls back to inline where
   constructable stylesheets are unsupported. (`/head` `--const-*` are inline.)
9. **Element sources pause off-screen** (shared `IntersectionObserver`) — work is
   torn down and last values freeze, resuming on re-entry. Globals/`:root` are
   never gated. Opt out with `gate: false`.
10. **Freeze / throttle.** Loop freezes while the tab is hidden. `pause()`/`resume()`
    stop/restart sampling. `configure({ liveHz: 30 })` caps the rate.
11. **`auto` is light-DOM only** (MutationObserver doesn't cross shadow roots —
    bind shadow elements with `propsFor(el, […])`) and lazy-loads plugin chunks
    only from verbatim CDNs (unpkg/jsDelivr file paths), not rewriting ones
    (esm.sh, `?module`, jsDelivr `+esm`). Load `auto` as `<script type="module">`.

## Recipes (complete, gotcha-respecting)

### 1. Offline / save-data banner + network-aware imagery

`online` + `network` are **global** → declare on `<html>`, they land on `:root`.
Booleans → `@container style()` equality only (one rule per discrete value).

```html
<html lang="en" data-props-for="online network">
  <body>
    <div class="net-banner net-banner--offline" role="status">You're offline. Posts will be queued and sent when you reconnect.</div>
    <div class="net-banner net-banner--slow" role="status">Slow connection — showing the lightweight view.</div>
    <header class="composer-hero"><h1>New post</h1></header>
    <script type="module">import 'prop-for-that/auto'</script>
  </body>
</html>
```

```css
.net-banner { display: none; padding: .5rem .75rem; font: 500 14px/1.4 system-ui; }
.net-banner--offline { background: #b91c1c; color: #fff; }
.net-banner--slow    { background: #b45309; color: #fff; }

@container style(--live-online: 0)        { .net-banner--offline { display: block; } }
@container style(--live-net-save-data: 1) { .net-banner--slow    { display: block; } }

.composer-hero {
  min-block-size: 220px;
  background: center / cover no-repeat url('/img/hero-2x.avif');
}
/* equality only → one rule per state, no OR inside the query */
@container style(--live-net-save-data: 1) { .composer-hero { background-image: none; background-color: #1e293b; } }
@container style(--live-online: 0)        { .composer-hero { background-image: none; background-color: #1e293b; } }
```

### 2. Pointer-reactive card tilt + size-aware text

`pointer` global (on `<html>`), `size` element-scoped (on the card). Both
continuous → `var()`/`calc()`. Children read the vars via downward inheritance.

```html
<html lang="en" data-props-for="pointer">
  <body>
    <article class="tilt-card" data-props-for="size">
      <div class="tilt-card__inner"><h2>Preview</h2><p>Your note, rendered live.</p></div>
    </article>
    <script type="module">import 'prop-for-that/auto'</script>
  </body>
</html>
```

```css
.tilt-card { inline-size: clamp(260px, 40vw, 480px); aspect-ratio: 3 / 2; perspective: 800px; }
.tilt-card__inner {
  block-size: 100%; border-radius: 12px; background: #0f172a; color: #f8fafc;
  display: grid; place-content: center; transform-style: preserve-3d;
  transform:
    rotateY(calc((var(--live-pointer-x-ratio) - 0.5) * 16deg))
    rotateX(calc((0.5 - var(--live-pointer-y-ratio)) * 16deg));
  transition: transform .08s linear;
  padding-inline: calc(var(--live-aspect) * 8px);
}
.tilt-card__inner h2 { font-size: clamp(18px, calc(var(--live-w) * 1px * 0.08), 40px); }
```

### 3. Char counter / fill bar + submit gating

`field` on a **wrapper** (so the sibling `.counter` inherits its vars),
`form-state` on the `<form>` (so the button — a descendant — reads `--live-all-valid`).

```html
<form class="composer" data-props-for="form-state">
  <div class="field" data-props-for="field">
    <label for="note">Note</label>
    <textarea id="note" name="note" maxlength="280" required></textarea>
    <div class="counter">
      <div class="counter__bar"></div>
      <span class="counter__remaining"></span>
    </div>
  </div>
  <button type="submit" class="submit">Post</button>
  <script type="module">import 'prop-for-that/auto'</script>
</form>
```

```css
.counter__bar {
  block-size: 4px; border-radius: 2px; background: #6366f1;
  inline-size: calc(var(--live-fill-pct) * 100%);   /* continuous 0–1 → ×100% */
  transition: inline-size .12s linear;
}
.counter__remaining { counter-reset: rem var(--live-remaining); font: 500 12px/1 system-ui; color: #475569; }
.counter__remaining::after { content: counter(rem) ' left'; }

@container style(--live-fill-pct: 1) { .counter__bar { background: #dc2626; } }   /* at limit */

.submit {
  opacity: calc(0.4 + var(--live-completion) * 0.6);
  pointer-events: none; transition: opacity .15s linear;
}
@container style(--live-all-valid: 1) { .submit { pointer-events: auto; } }
```

> CSS gating is presentational — keep real submission blocking in JS too. `--live-fill-pct`
> / `--live-remaining` exist only because the textarea has `maxlength`.

### 4. FOUC-safe scrollbar gutter + DPR constants

Use `/head` (not `auto`) — it writes `--const-*` **inline** on `:root` before
first paint. For true zero-FOUC, ship a synchronous inline build of `/head`.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <script>import('prop-for-that/head')</script>  <!-- prefer a synchronous inline build -->
    <link rel="stylesheet" href="/app.css">
  </head>
  <body><main class="app"><aside class="rail">Drafts</aside><section class="composer">…</section></main></body>
</html>
```

```css
.app  { padding-inline-end: calc(var(--const-scrollbar-w) * 1px); }  /* reserve gutter */
.rail { border-inline-end: calc(1px / var(--const-dpr)) solid #cbd5e1; }  /* crisp hairline */
@container style(--const-scrollbar-w: 0) { .app { padding-inline-end: 0; } }  /* overlay scrollbars */
```

## Links

- Docs: https://prop-for-that.netlify.app/docsite/
- Plugin & source reference: https://prop-for-that.netlify.app/docsite/reference/plugins/
- llms.txt: https://prop-for-that.netlify.app/llms.txt
- Repo: https://github.com/argyleink/prop-for-that
