# Remediation — tiers and procedure

The audit run ranks findings and tags each with a tier; it does not write to the live site. Fixes happen in a follow-up run after the user says which items to apply. Actions that need no approval, in either run: re-running `cache_steps` and retesting, re-running a single check, reading the Site Health Info tab, downloading an image to measure it.

Owners come from the config: `headers.owners`, `host.owns`, `security_layer.owns`, `email.*`, `leave_as_is`, `report_only`. An item whose owner is the host or the security layer is report-only regardless of category.

## Tier 1 — Fix on approval (content and settings, reversible in wp-admin)

- Console error matching `frontend.regression_script_id`: re-create the documented fix at `plugins.performance.code_snippets`. A new inline-script error of the same kind gets a snippet the same way; add the pattern to the config comment.
- PageSpeed Performance under 100 on mobile: consent script missing from the delay-JS list (`plugins.performance.delay_js_list`) → add it. Render-blocking CSS/JS → turn on the performance plugin's unused-CSS removal, defer, or delay options that are off. Unused JS from one plugin on the homepage → disable that script on the homepage in `plugins.performance.script_manager` when the page clearly does not use it.
- Accessibility plugin and WAVE errors in post content (empty buttons, missing alt text, missing form labels, empty links): fix in the post or page editor. Template-generated errors: list them with the generating plugin or theme; theme files are not edited from this skill.
- Contrast errors: record element, current ratio, required ratio. A Global Styles custom-property change is tier 1; anything else is listed for the user.
- Missing description, canonical, or og tags on a post: the SEO plugin's meta box for that post. Missing or wrong `og:image` on a post: set the featured image or the SEO plugin's social image; `og:description` follows the meta description. Site-wide OG tags absent: check SEO plugin → Site features → Open Graph is on before assuming a theme problem. Confirm at the unfurler after the cache steps.

## Tier 2 — Fix with caution (verify after; some go through a repo)

- Security headers: look up the owner in `headers.owners`. Theme- or plugin-owned headers change in that file through its repo and deploy path (a PR, never a live file edit) — for example.com that is `you-child` `inc/security-headers.php`. Edge-owned headers are report-only. Verify on a cache-busted URL first, then the bare URL once the edge cycles; the SSL Labs grade moves with HSTS.
- Rich Results schema errors: confirm the SEO plugin's Schema framework is on; note the affected post types; Schema output itself stays untouched.
- Site Health critical from a plugin conflict: update the plugin when an update exists. PHP, REST, loopback, or database criticals: investigate through wp-admin settings. Disk, permissions, server config: report-only (host).
- Autoloaded options above 1 MB: identify the largest entries in Site Health Info, name the responsible plugin; no mass deletes.
- A late scheduled event not in `leave_as_is`: check the owning plugin for a pending update or a stalled queue.
- Email authentication — DNS lives at `host.dns_provider`; each record is its own change, never batched with other edits, and DNS changes are one of the run's stop conditions.
  - DKIM absent: enable it at `email.dkim_enable_where`; publish the CNAMEs it issues; confirm every selector resolves before recording it fixed.
  - DMARC absent: publish `email.dmarc_first_policy` (`p=none` with a `rua` address) and leave it until the aggregate reports have been read. `p=quarantine` or `p=reject` come later, after every legitimate sender is aligned — moving early drops real mail.
  - SPF: change only when the expanded chain fails to cover the MX. `~all` → `-all` only after DKIM and DMARC reports show every sender aligned.
  - Re-check at mxtoolbox after propagation; the first read after a change can lag.

## Tier 3 — Leave as is

Every entry in `config.leave_as_is`: recorded each run, diffed against the previous report, never acted on. Late-event entries are flagged only when a different event is also late.

## Tier 4 — Report only

Every entry in `config.report_only`, plus anything owned by the host or the security layer: recorded with the owner named and, where useful, the exact ask (for example "raise edge cache TTL for static assets" or "renew the certificate before <date>").

## After fixes (follow-up run)

1. Run all `cache_steps` once.
2. Re-run only the checks that failed; read the same fields the same way.
3. Append to the report:

```markdown
## Remediation results
| Issue | Action | Result (fixed / partial / still failing) | Source |
Fixes attempted: N · confirmed: N
Remaining for the user: <item — owner — what is needed>
```

4. Final message: what was fixed, what still needs a hand, the report path.

## Plugin-specific paths (apply when `config.plugins` names the plugin)

- Perfmatters: Script Manager at `<site>/?perfmatters`; delay-JS list under JavaScript → Delay JavaScript; unused CSS under CSS → Remove Unused CSS; code snippets under Code → Add Snippet → PHP, Frontend Only.
- Yoast SEO: Schema framework and Open Graph toggles under Settings → Site features; per-post social image and meta description in the post's Yoast panel; Search Console figures on the dashboard.
- Accessibility Checker Pro: template-generated flags (decorative SVGs, media-player caption checks, plugin-emitted markup) can be dismissed with a reason in the issues list; content flags are fixed in the editor.
- Complianz: the consent modal is a common mobile LCP element in a clean profile; the fix is the delay-JS list, not the plugin.
