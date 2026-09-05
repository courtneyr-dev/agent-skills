# Tool quirks

Behavior of the tools this audit drives, by tool. Host- and plugin-specific signals (which flush shows a notice, which redirects silently) live in `config.yml` under `cache_steps[].confirm` and `security_layer.cache_clear`, next to the step they belong to.

## Browser channel (Browser pane / Claude in Chrome)

- JS results that contain hrefs or query strings come back as `[BLOCKED: Cookie/query string data]`. Click elements from JS (`document.querySelector(...).click()`) and read notices or network requests afterwards; never return a link URL from JS.
- Some flushes redirect with no admin notice. Start `read_network_requests` tracking before the click and confirm by the request substring in the config.
- `find` refs go stale after a page inserts a banner or notice; run `find` again before a second click on the same page.
- Hidden pane: `resize_window preset=desktop` yields a 0×0 viewport (mobile media queries apply; `getBoundingClientRect` and `offsetParent` are garbage) and `computer` clicks and keys time out after 30 s. Force `resize_window width=1280 height=720` for desktop measurements and drive journeys with `el.focus(); el.click()` in `javascript_exec`. `read_page`, `get_page_text`, and JS keep working while hidden.
- `computer` `wait` caps at 10 s per action; poll with JS or repeat the wait.
- Screenshot judgments (layout, og:image, gauges): zoom the region first (`computer` action `zoom` with a region); the full-viewport image is too small to judge.

## Sessions

- wp-admin and my.yoast.com sessions expire independently. Logging in is off-limits; an expired session records "not readable this run" for that check and the run continues. The WordPress "Remember Me" cookie lasts 14 days.

## PageSpeed Insights

- The keyless PSI API quota is usually exhausted. Use the UI: `https://pagespeed.web.dev/analysis?url=<encoded>` auto-runs both form factors in one pass.
- `get_page_text` returns only the report stylesheet. Scores sit inside shadow roots: pierce them for `.lh-gauge__wrapper` / `.lh-exp-gauge__wrapper`; each gauge appears three times per form factor, and the page holds four rendered report copies (mobile and desktop, twice each) — pull `.lh-container` blocks and dedupe.
- "Discover what your real users are experiencing … No Data" means no CrUX; label the scores lab-only.
- Best Practices under 100 right after a fix is often a stale edge cache: re-run the cache steps, wait 2 min, retest before recording.
- A consent banner rendered as a centered modal in a clean (cookie-free) profile is a frequent mobile LCP element; in a cookied session the same banner may be a corner button, so the two views differ.

## WAVE

- The report page's `get_page_text` returns only "Loading...". Read `document.querySelector('#summary').innerText` and `#details` via JS.

## Website Carbon

- Counters animate on scroll-into-view: scroll to the bottom, then regex `document.body.innerText`.
- The direct `/website/<slug>/` URL 404s for a never-tested site; open the homepage, set the input value and `form.requestSubmit()` via JS, then read the result page.
- Their API returns "Unauthorised"; don't use it.

## SSL Labs

- Status runs DNS → IN_PROGRESS → READY. Every field is `None` until READY; that is the scan working, not a failing grade. Record only at READY.
- A fresh API scan takes about 4 min. Start it first and poll between other checks.
- zsh: `status` is a read-only variable; a loop that assigns it dies. Use `st`.
- The grade caps at A− without HSTS, so this check and the security-headers check move together.
- If the API rate-limits, the browser UI at https://www.ssllabs.com/ssltest/ takes 2–3 min.

## securityheaders.com and header caching

- Use `?q=<url>&followRedirects=on`.
- Headers are cached with pages at the edge. A header fix shows on a cache-busted URL (`?nocache=<timestamp>`) before the bare URL; test both after any header change and after the cache steps.

## Is It Agent Ready

- The tool's shape changed in 2026-09: categories are Discoverability, Content (Markdown negotiation), Bot Access Control (Content-Signal), API/Auth/MCP/Skills, Commerce, and it no longer lists an llms.txt check. Read the categories from the page each run; when the shape changes again, describe the new shape in the report so the next diff aligns.
- Re-run when the page shows a cached result or offers "scan again".

## Rich Results Test

- `https://search.google.com/test/rich-results?url=<encoded>` auto-runs; results in 60–90 s.

## Social previews and unfurlers

- opengraph.xyz became a meta-tag inspector with a template gallery in 2026-08; it no longer renders per-network cards. microlink also only parses tags.
- A real unfurl that fetches and processes the image: `https://cardyb.bsky.app/v1/extract?url=<encoded>` (Bluesky's card service).
- Networks cache cards aggressively; after a fix, use each platform's own debugger before recording the card as still broken.

## Email

- Count SPF lookups by expanding includes and redirects recursively (script in `checks.md`); counting top-level includes undercounts, and the 10-lookup limit fails silently.
- A host-provider SPF include can cover a different MX provider through nested includes; expand the chain before reporting a mismatch. `config.email.spf_covers_mx_via` records the known-good chain.
- mxtoolbox surfaces lookup overruns, syntax errors, and blocklist hits that raw `dig` output hides.

## Validators (when markup validation is needed)

- Nu: `POST https://validator.w3.org/nu/?out=json` with the saved HTML; it needs a real User-Agent. Feed validator: `check.cgi?url=…&output=soap12`. Filter Alpine/Vue attribute errors before reading results.
