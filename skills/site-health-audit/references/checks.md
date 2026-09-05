# Checks — method, record lists, done conditions

Config keys are written `config.<key>`. Evidence format for every recorded value: `source: <URL or command> · <field or selector>`. Browser channel: `config.browser.channel`; the tool traps for each service are in `quirks.md` — read that file's section for a tool before the first use of it in a run.

State file (`<report.dir>/.state/<date>.json`):

```json
{
  "date": "2026-09-04",
  "config": "<path>",
  "previous_report": "<path or null>",
  "ssl_labs": {"started": "<ISO time>", "status": "IN_PROGRESS"},
  "checks": {"1-caches": {"status": "done", "evidence": ["network: wpaas_action=flush_cache"]},
             "4-pagespeed": {"status": "pending"}},
  "not_read": []
}
```

## 0. Previous report

Newest file in `config.report.dir` matching `config.report.previous_glob`, by date prefix (Claude Code-era files are `YYYY-MM-DD-site-health-report.md`; older files are `YYYY-MM-DD.md`). Read its numbers into the state file under `previous` so every later check can write its Δ immediately.

Done: `previous_report` set in the state file (or `null` with "no previous report — baseline run" in the report header).

## 1. Caches

For each entry in `config.cache_steps`, in order, 3 s apart:

1. Open `where` (a wp-admin page or the admin bar).
2. Act: click the admin-bar anchor whose trimmed text matches the menu label (`[...document.querySelectorAll('#wpadminbar a')].find(a => a.textContent.trim() === '<label>').click()`), or run the `action` JS given. Never return the anchor's href from JS (see quirks: blocked query strings).
3. Confirm with the step's `confirm` signal: `notice:` (admin notice text), `network:` (a request containing the substring — start `read_network_requests` tracking before the click), `banner:` (page text), or `none` (record "unverified").
4. Record pass / fail / n/a with the signal seen.

`same_as:` repeats an earlier step. A step whose page reports an API/connection failure records "API failed" and the run continues. After the last step wait 30 s.

Done: one line per step in the report with its signal.

## 2. Frontend

1. Navigate to `config.site.url`. Read console errors (error-only filter); record count and the first line of each.
2. Regression script: `document.querySelectorAll('script[id="<config.frontend.regression_script_id>"]').length` — target 0.
3. Images: `[...document.images].filter(i => i.complete && i.naturalWidth > 0).length` of `document.images.length`.
4. Layout: screenshot, then zoom the header, the hero, and the footer regions; judge the zoomed images (no broken layout, no missing images, no blocking overlay). Note the consent banner's state (`config.plugins.consent`).

Done: console count, regression count, image ratio, layout verdict with the zoomed regions named.

## 3. SSL/TLS (Qualys SSL Labs API)

Start the scan first, right after check 2; poll between later checks. `H` is `config.site.bare_domain`.

```bash
H=example.com
curl -sS "https://api.ssllabs.com/api/v3/analyze?host=$H&publish=off&startNew=on&all=done" >/dev/null   # start
# poll (use `st`, not `status` — zsh reserves `status`)
st=$(curl -sS "https://api.ssllabs.com/api/v3/analyze?host=$H&publish=off&all=done" | tee /tmp/ssl.json | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'); echo "$st"
python3 - <<'PY'
import json
d=json.load(open('/tmp/ssl.json')); print('status:', d.get('status'))
for e in d.get('endpoints', []):
    det=e.get('details', {})
    print(' grade:', e.get('grade'), '| warnings:', e.get('hasWarnings'))
    print(' protocols:', [f"{x['name']} {x['version']}" for x in det.get('protocols', [])])
    print(' HSTS:', (det.get('hstsPolicy') or {}).get('status'), '| OCSP stapling:', det.get('ocspStapling'))
    print(' forwardSecrecy:', det.get('forwardSecrecy'), '| client sim errors:', sum(1 for s in det.get('sims', {}).get('results', []) if s.get('errorCode')))
PY
echo | openssl s_client -connect "$H:443" -servername "$H" 2>/dev/null | openssl x509 -noout -enddate -issuer
```

Record only when `status` is `READY`: grade (target A+), protocols offered (flag if TLS 1.3 is absent), HSTS status, OCSP stapling, forward secrecy, client-simulation failure count, certificate issuer and `notAfter` (flag when inside `config.host.cert_expiry_warn_days`). Fallback when the API rate-limits: https://www.ssllabs.com/ssltest/ in the browser (2–3 min).

Done: grade plus the six fields, each sourced to the API JSON or the openssl line.

## 4. PageSpeed Insights

Open `https://pagespeed.web.dev/analysis?url=<url-encoded config.site.url>` — it runs mobile and desktop in one pass (60–90 s). Read the scores from the DOM (quirks: shadow roots, four report copies). Record per form factor: Performance, Accessibility, Best Practices, SEO; lab LCP, CLS, TBT; the LCP element; "lab-only" when CrUX shows No Data. Target 100/100/100/100 on both.

For any score under 100, expand its diagnostics and record the failing audits by name. Performance under 100 on mobile: name the LCP element (a consent modal is a common one) and the CLS culprit. Best Practices under 100 right after a fix: re-run `cache_steps`, wait 2 min, retest before recording it.

Done: eight scores, three lab metrics per form factor, failing audits named, all sourced to the analysis URL.

## 5. Accessibility plugin dashboard

Skip (`n/a`) when `config.plugins.accessibility` is `none`. Open `config.plugins.accessibility.issues`. Record total open issues and the per-severity counts; when any count is above 0, list Check Type, Severity, WCAG level, Count, and whether the source is post content or a template (plugin/theme). Target 0 open.

Done: totals and the per-check table (or "0 open").

## 6. SEO plugin dashboard

Skip when `config.plugins.seo` is `none`. Open `config.plugins.seo.dashboard`. Record Search Console 28-day Impressions, Clicks, Average CTR, Average Position with their % change; top 5 content and top 5 queries with clicks; SEO score breakdown (Good / OK / Needs improvement / Not analyzed); Readability breakdown.

Done: four metrics, two top-5 lists, two breakdowns.

## 7. AI visibility tool

Skip when `config.plugins.ai_visibility` is `none`. Open its URL; record whatever it shows (visibility index and change, brand mentions, sentiment, competitor rank). A logged-out page records "not readable this run" (logging in is off-limits).

Done: metrics recorded or the not-read note.

## 8. Security headers

Open `https://securityheaders.com/?q=<url-encoded config.site.url>&followRedirects=on`. Record the grade (target A+), each missing header, and each flagged header with the value shown and the warning text. Map each finding to its owner from `config.headers.owners`; that owner decides the remediation tier. Cross-check the raw response: `curl -sSI <url> | grep -iE '^(content-security-policy|strict-transport|x-frame|x-content-type|permissions-policy|referrer-policy|reporting-endpoints|cf-cache-status|server):'`.

Done: grade, missing list, flagged list with owners, curl line captured.

## 9. Email authentication

Raw records first (`D` is `config.site.bare_domain`, selectors from `config.email.dkim_selectors`):

```bash
D=example.com
dig +short TXT "$D" | grep -i 'v=spf1'
dig +short TXT "_dmarc.$D"
dig +short MX "$D"
for s in selector1 selector2 default google k1 s1; do echo "$s: $(dig +short CNAME "$s._domainkey.$D")$(dig +short TXT "$s._domainkey.$D")"; done
python3 - "$D" <<'PY'
import re, subprocess, sys
def txt(n):
    out = subprocess.run(['dig', '+short', 'TXT', n], capture_output=True, text=True).stdout
    return [l.strip().strip('"').replace('" "', '') for l in out.splitlines()]
def spf(n):
    return next((r for r in txt(n) if r.startswith('v=spf1')), None)
count, seen = 0, set()
def walk(n, depth=0):
    global count
    if n in seen: return
    seen.add(n); r = spf(n); print('  ' * depth + f'{n}: {r}')
    if not r: return
    for t in r.split():
        m = re.match(r'^[+\-~?]?(include|a|mx|ptr|exists|redirect)(?:[:=](.*))?$', t)
        if not m: continue
        count += 1
        if m.group(1) in ('include', 'redirect') and m.group(2): walk(m.group(2), depth + 1)
walk(sys.argv[1]); print('lookups:', count, '/ 10')
PY
```

Then open `https://mxtoolbox.com/domain/<D>` for the consolidated view (SPF, DKIM, DMARC, MX, blocklists; it surfaces lookup overruns, syntax errors, and blocklist hits the raw records hide).

Record: SPF present, the full record, and the qualifier (`-all` hard fail is the target; `~all` soft; `?all` neutral); SPF lookup count out of 10; whether the expanded chain covers the current MX (compare the walk output with `config.email.expected_mx` and `config.email.spf_covers_mx_via` — expand before reporting a mismatch); DKIM selector found or "not found"; DMARC present, policy, `rua`, `pct`; blocklist status.

Regression when: SPF disappears or its qualifier weakens, the chain stops covering the MX, the lookup count reaches 10, a DKIM selector stops resolving, DMARC policy is downgraded, or the domain appears on a blocklist.

### 9b. Live email tests

Sends real mail. Run only when the user gave the go-ahead in this session and the newest report's live-email table is older than `config.email.live_tests.cadence_days`; otherwise record "skipped — sends real mail" with the last-run date.

1. Deliverability — https://www.mail-tester.com/: copy its one-time address; send from the site itself (`config.email.live_tests.smtp_test_path`, or a password reset for a test account set to that address); reload; record the score out of 10 and each deduction (SPF, DKIM, DMARC, reverse DNS, SpamAssassin rules, broken links, blocklisted IP). Target 10; below 8 lands in spam for some recipients.
2. Authentication walkthrough — https://learndmarc.com/: send to its address when mail-tester flags an authentication failure without an obvious cause; record which alignment check fails.
3. Transactional mail: password reset arrives (delivery time); new-user notification arrives to admin and user; contact form submission arrives and the auto-reply sends. Delete the test user afterwards.
4. Ground truth: in the receiving mailbox open the test message → Show original; record the `Authentication-Results` line (`spf=`, `dkim=`, `dmarc=`). This outranks any checker.

Done (9): SPF, lookup count, chain-covers-MX, DKIM, DMARC, blocklist, each sourced to a dig line or the mxtoolbox page. Done (9b): four results or the skip note.

## 10. Rich results and social previews

Latest post URL: `curl -s "<config.site.latest_post_source>"`.

Rich results: open `https://search.google.com/test/rich-results?url=<url-encoded>` for the homepage and the latest post (auto-runs, 60–90 s). Record valid items, warnings, errors per URL.

Social previews, per URL:

```bash
curl -sS -L --compressed "<url>" | grep -oE '<meta (property|name)="(og|twitter):[^"]*" content="[^"]*"'
curl -sS "<config.social.unfurler><url-encoded url>"          # real unfurl: title, description, image
curl -sL -o "$SCRATCH/og.img" "<og:image url>" && sips -g pixelWidth -g pixelHeight "$SCRATCH/og.img"
```

Record `og:title`, `og:description`, `og:image` (resolves: yes/no; dimensions; 1200×630 is the safe shape), `og:url`, `og:type`, `twitter:card`, and whether the post uses the site-wide fallback image (`config.social.default_og_image`, or the homepage's og:image when that key is empty). Regression when a page that had its own image falls back to the default, or the unfurler returns no image.

Done: rich-results triple for two URLs; six og fields plus unfurl result for two URLs.

## 11. WAVE

Open `https://wave.webaim.org/report#/<url-encoded config.site.url>`. Read `document.querySelector('#summary').innerText` (and `#details` for the items). Record errors, contrast errors, alerts, structural elements. Target 0 errors. Name each error with its element.

Done: four counts plus named errors.

## 12. Carbon

Open https://www.websitecarbon.com/, set the URL input via JS and `form.requestSubmit()`, then on the result page scroll to the bottom and regex `document.body.innerText` for the rating letter, grams of CO2 per visit, and the "cleaner than N%" figure.

Done: three values.

## 13. Is It Agent Ready

Open `https://isitagentready.com/<config.site.bare_domain>`; wait for the scan (30–90 s); re-run if it shows a cached result or offers "scan again". Record the overall score or grade, then every category and check as the page names them today with its pass / warn / fail state and one-line description, and the recommendations it surfaces. When the category set differs from the previous report, add one line describing the new shape so next week's diff aligns. Tier the findings: bot-blocking signals → owner `config.security_layer`; llms.txt and robots.txt directives → the user's decision; metadata or schema on specific posts → fix on approval.

Done: score plus the full category table with states.

## 14. WordPress Site Health

Open `<config.site.admin_url>site-health.php?tab`; wait until "Site Health Results are still loading…" is gone. Record critical count (target 0), recommended count, passed count. Per critical: title, category (Security / Performance / Compliance), description. Per recommended: title, category, key detail. Watch specifically: late scheduled events (each one not in `config.leave_as_is` is a finding), Consent API non-conforming plugins (record the list; diff it against last week), autoloaded options count and size (flag above 1 MB; the Info tab lists the largest entries), PHP version, loopback / REST / database warnings, object-cache status.

Done: three counts, per-item lines, the five watched values.

## 15. Report and diff

Compare each value with `previous` from the state file. A regression is any score, grade, or count that moved the wrong way, any new error or critical, any email record weakened, any og:image that fell back to the default, any agent-ready check that went from pass to fail. No movement: "No regressions detected". Action Items are ranked: regressions first, then carried baseline gaps; each carries its tier, owner, and the admin URL or file.

Template:

```markdown
# Site Health Report — <config.site.title>

**Date:** YYYY-MM-DD · **Tested by:** <config.report.tested_by> · **Previous:** <path or "none — baseline">
**Not read this run:** <check: reason, … or "none">

## Caches
| Step | Result | Signal | Source |

## Frontend
- Console errors: N · Regression script count: N · Images: N/N · Layout: intact / issue — source: …

## PageSpeed Insights
| Metric | Mobile | Desktop | Δ Mobile | Δ Desktop | Source |
| Performance / Accessibility / Best Practices / SEO | | | | | pagespeed.web.dev/analysis?url=… · gauge text |
- Lab: LCP / CLS / TBT per form factor · LCP element · CrUX: field / lab-only
- Failing audits: …

## Accessibility plugin
- Open issues: N (Δ) · Critical / High / Medium / Low: … — source: <issues URL>
| Check | Severity | WCAG | Count | Content or template |

## SEO plugin
| Metric | Value | Change | Δ vs last report | Source |
- SEO scores G/OK/NI/NA: … · Readability: … · Top 3 content: … · Top 3 queries: …

## AI visibility
- <metrics with Δ> or "not readable this run" — source: …

## Security headers: <grade> (Δ)
| Header | State | Value or warning | Owner (config) |

## SSL/TLS: <grade> (Δ)
- Protocols · HSTS · OCSP · Forward secrecy · Client-sim failures · Cert issuer, expires YYYY-MM-DD — source: api.ssllabs.com JSON, openssl

## Email authentication
| Record | State | Detail | Δ | Source |
| SPF / DKIM / DMARC / Blocklists | | | | dig, mxtoolbox |
- SPF lookups: N/10 · Chain covers MX: yes/no (expanded: …)
- Live tests: <table> or "skipped — sends real mail (last run YYYY-MM-DD)"

## Rich results
- Homepage: valid N / warnings N / errors N · Latest post <URL>: … — source: search.google.com/test/rich-results

## Social previews
| URL | og:title | og:description | og:image (dims, resolves) | twitter:card | Unfurl | Source |
- Fallback-image pages: …

## WAVE
- Errors N · Contrast N · Alerts N · Structural N — source: wave.webaim.org #summary

## Carbon
- Rating · g CO2/visit · cleaner than N% — source: websitecarbon.com result page

## Is It Agent Ready: <score> (Δ)
| Category | Check | State | Note |
- Shape change vs last report: none / …

## WordPress Site Health
- Critical N (target 0) · Recommended N · Passed N — source: site-health.php
- Late events · Consent API list (Δ) · Autoload N items, N KB · PHP x.y.z · Object cache
- Items in leave_as_is seen: …

## Regressions
…

## Action items
1. <finding> — tier · owner · URL/file
```
