---
name: agency-platform-adapters
description: "Pick the right installed platform skills for a client project instead of a generic CMS persona: resolves the project's platform and version (WordPress, WooCommerce, Drupal, Cloudflare Workers, JavaScript or TypeScript apps, native iOS) to the exact upstream skills in their mounts, routes WordPress below 7.0 or PHP below 7.4 to a legacy path, and refuses platforms with no adapter (headless CMS, Laravel or Symfony, other commerce platforms, API contract testing, PWA) with the reason. Use for: which skills for this client site, platform adapter, CMS specialist routing, is this WordPress version supported, legacy client project, Drupal or WooCommerce project setup."
disable-model-invocation: true
---

# Agency platform adapters

One register (`references/adapters.json`) maps each platform the agency serves to the installed skills that do the work, with the supported range the upstream itself states. A resolver reads the project's facts and returns those skills or refuses. Nothing here re-implements a platform skill.

## When to use (and when not)

Use it when an engagement starts, when a CMS specialist or engineer picks up a client project, and when a client's platform version changes. Use `wp-project-triage` first on WordPress projects to get the real version.

Don't use it to judge code quality or to install skills. Missing skills are restored through the rig's skill-sync pipeline, never from this skill.

## Inputs and prerequisites

- A project facts JSON: `platform`, plus every fact the register's minimums need: a platform with `min_version` needs `version`, and one with `php_min` needs `php_version` (WordPress needs both). WooCommerce also needs `wordpress_version` and `php_version`, because WordPress's minimums and legacy route apply before WooCommerce's own range. A missing fact exits 2; it never resolves `supported`. Examples: `fixtures/project-wordpress-current.json`, `fixtures/project-wordpress-legacy.json`.
- The skill mounts named in the register: `~/.claude/skills` (rig) and `~/.agents/skills` (agents, where the WordPress/agent-skills set is installed).

## Method

1. Get the platform and version from the project itself (triage output, `composer.json`, `package.json`).
2. Run `python3 scripts/resolve_adapter.py --project PROJECT.json`.
3. Load only the skills listed in `skills`, from their `path`. Apply `standards` (WordPress PHP follows the WordPress Coding Standards and PHPDoc conventions; the project's own ruleset wins where it is stricter).
4. On `legacy`, follow `reason`: detection only, then a human CMS specialist confirms which APIs exist.

## Stopping conditions

- Exit 0, `supported`: the version is inside the upstream's stated range and every adapter skill is present.
- Exit 0, `range-unstated`: the upstream states no range; read `warnings` and confirm against the project's own requirements.
- Exit 1: `legacy`, `blocked`, `unknown` or `adapter-missing`. Don't fall back to a generic persona; follow `reason`.
- Exit 2: invalid project or register JSON, or a project missing a fact a register minimum needs (`fixtures/project-wordpress-php-only.json`).

## Output contract

One JSON object, keys sorted: `ok`, `decision`, `platform`, `version`, `skills` (each `id`, `mount`, `path`, `present`), `reason` when refused, `standards` and `source` when available, `warnings` and `limits`. On exit 2: `{"error": "..."}`.

## Failure states

- A register entry with a `min_version` but no legacy route, a blocked entry without a reason, or a skill in an unknown mount: exit 2, so a bad register edit can't route silently.
- An adapter skill deleted from its mount: `adapter-missing` names it.

## Missing capability

Platforms marked `blocked` have no installed skill. The resolver says so and names who owns the work until one is adopted or written; it never borrows another platform's skills.

## References

- `references/adapters.json`: the register, with upstream revision and license per adapter.
- `references/platform-sources.md`: where each supported range comes from.
- Tests: `cd scripts/tests && python3 -W ignore -m unittest discover -p 'test_*.py'` (`scripts/tests/test_resolve_adapter.py`).
