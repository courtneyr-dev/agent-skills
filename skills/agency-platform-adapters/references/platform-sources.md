# Platform sources and supported ranges

Each entry names the upstream, the local clone revision read on 2026-11-25 (`$FRIG_UPSTREAM_ROOT/<name>`) and its license. Skills are installed by the rig's skill-sync pipeline; this skill only points at them.

Source: WordPress/agent-skills, `docs/compatibility-policy.md` and README "Compatibility"
Location: https://github.com/WordPress/agent-skills
Version or retrieved date: 32ea909f7d01 (2026-11-25)
Rights: GPL-2.0-or-later; skills used in place from `~/.agents/skills`, not copied
Range: WordPress core 7.0 and later, PHP 7.4.0 and later. The policy says skills should default to 7.0 guidance and ask for a target version when behavior differs, which is why older projects take the legacy route.

Source: kanopi/cms-cultivator (code-standards-checker, composer-security-update, pr-quality-report)
Location: https://github.com/kanopi/cms-cultivator
Version or retrieved date: ff328fcc77af (2026-11-17)
Rights: GPL-2.0
Range: none stated. The skills read each project's own `composer.json` and `package.json` scripts, so they follow the project's PHPCS ruleset (WordPress or Drupal). Kanopi's private Teamwork, DDEV and audit conventions aren't part of the public source and aren't assumed.

Source: Automattic/claude-woocommerce-toolkit
Location: https://github.com/Automattic/claude-woocommerce-toolkit
Version or retrieved date: d70538707247 (2026-06-08)
Rights: GPL-2.0
Range: none stated. The skills name feature versions (for example WooCommerce 8.9 for additional checkout fields, 11.0 for the product editor removal) but no support range.

Source: cloudflare/skills (workers-best-practices, wrangler)
Location: https://github.com/cloudflare/skills
Version or retrieved date: ff191de7d903 (2026-11-24)
Rights: Apache-2.0
Range: Workers pin runtime behavior by compatibility date, so there is no version range to check.

Source: pstack typescript-best-practices
Location: installed from cursor/plugins (`pstack/skills/typescript-best-practices`) per skill-sync `sources.json`
Version or retrieved date: `main`, as installed on 2026-11-25
Rights: as recorded by the pstack distribution
Range: none stated.

Source: gstack ios-qa, ios-fix, ios-design-review
Location: installed in the rig skills directory; not tracked in skill-sync `sources.json`
Version or retrieved date: as installed on 2026-11-25 (SKILL.md `version: 1.0.0`)
Rights: not recorded locally; check the gstack distribution before redistribution
Range: none stated.
