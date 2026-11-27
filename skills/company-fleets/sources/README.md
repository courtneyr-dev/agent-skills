# Company-fleets sources

This folder records which upstream skill repositories the company fleets use, at which revision, under which license, and which requirement each skill covers. Everything here is generated from live state plus facts read from the pinned files on 2026-11-25 and 2026-11-26. The ledger, matrix and evidence describe the reference installation the fleets were built on (macOS, 2026-11-25 to 2026-11-26); this repository ships none of the upstream skills, so a fresh checkout starts with all of them absent.

| File | What it holds |
|---|---|
| `ledger.json` | 24 upstream repositories with revision, commit date, license, rights notes, installer side effects (read, never run), native-tool assumptions and status; 254 installed skills with destination, tree hash, model visibility and links that leave the skill directory |
| `capability-matrix.json` | All 235 rows of `../registry/requirements.json`, each mapped to one disposition, with a coverage summary by fleet |
| `build_sources.py` | Regenerates both JSON files. The recorded facts live in this script; edit them here |
| `verify_sources.py` | Checks the ledger and matrix against your install; exits 1 with a resume step on drift. Needs skill-sync beside company-fleets with `render` and `apply_pins`, and skill-sync's `sources.json` |
| `qualify.py` | Runs installed upstream scripts on synthetic Fixture Co inputs and writes `evidence/qualification.json` |
| `evidence/` | Raw outputs from the reference installation: the hide-and-pin log, `sync_skills.py check` output, qualification results |

## Rebuild and check

```bash
cd skills/company-fleets/sources
python3 qualify.py            # optional: refresh script evidence
python3 build_sources.py      # rewrites ledger.json and capability-matrix.json
python3 verify_sources.py     # exit 0 consistent, 1 findings, 2 invalid
python3 -m unittest           # verifier tests; skipped when skill-sync lacks render and apply_pins
```

`build_sources.py` reads upstream clones under `$FRIG_UPSTREAM_ROOT` (default `<skills-root>/factory-rig/upstream`) and skill-sync's registry and cache under `$SKILL_SYNC_HOME`; `config.example.env` documents both.

After `sync_skills.py apply` updates an upstream skill, rerun `build_sources.py`; the verifier reports any installed tree that no longer matches its pin until you do.

## Statuses

Each repository and each installed skill carries exactly one of six statuses. Activation is recorded separately as `model_invocation`, so a hidden skill can still be verified.

- `installed-and-verified`: installed, its tree matches the pin, and a recorded behavioral check passed. For the earlier systems (Magnus, Matt, Noodle, yysun, tstack, Obsidian) the check belongs to `skills/factory-rig/registry/components.json`, named in `status_owner`; this ledger doesn't re-decide it.
- `installed-inactive`: installed and hash-checked, with no behavioral check on record. All WordPress skills sit here: they're model-visible and in daily use, but this ledger holds no evidence for them.
- `verification-failed`: a qualification case failed on a script defect, not a fixture error.
- `source-only`: read for gap analysis, nothing installed.
- `blocked-authentication` and `blocked-platform`: installation or use needs an account or a host that doesn't exist here.

## Qualification

`qualify.py` ran 21 cases against 9 installed upstream skills on 2026-11-26: 18 pass, 2 fail, 1 blocked (`evidence/qualification.json`). The earlier run's failures came from the harness, not the scripts: it ran from a directory without its `qual/` fixtures, passed an unfilled profile template, handed the lesson renderer a directory, and expected exit 0 where month-end-close documents exit 4 for a reconciliation that doesn't prove. The runner now writes every fixture into a temporary working directory.

Real script defects stay visible:

- `composer-security-update`: `scripts/audit_table.py:128-130` prints "Could not parse audit JSON" and exits 0, so malformed input passes as success. Status `verification-failed`.
- `k12-lesson-plan-creation`: `scripts/render_lesson_html.py` has no validation and renders a lesson whose `documents` is a string, though `references/lesson-json.md:18` requires an array. Status `verification-failed`. Its DOCX renderer is blocked on python-docx.
- `pricing-strategist`, `capacity-planner` and `channel-economics` reject malformed JSON with an unhandled traceback instead of an error message. They still exit non-zero, so the cases pass with a recorded defect.

Passing a script case shows the script keeps its contract on synthetic input. It doesn't show that the business advice is right.

## Context budget fix

The 176 skills installed on 2026-11-25 from 12 new repositories added their descriptions to every session's skill list. Roles load procedures by path, so these skills don't need to be model-visible. Each one now carries `disable-model-invocation: true`, pinned with `sync_skills.py pin <skill> disable-model-invocation` so upstream updates keep it. Skill-sync renders the pin into installs and leaves the raw upstream snapshot untouched.

Measured on the reference installation over `skills/*/SKILL.md` with the parser in `skills/skill-sync/audit_skills.py`:

| Measure | Before (22:57) | After (22:58) |
|---|---|---|
| Model-visible skills | 414 | 238 |
| Description characters of model-visible skills | 173,780 | 68,686 |
| Listing cost (name + 4 + description, capped at 1,536) | 182,209 | 73,072 |

The drop of 105,094 description characters equals the hidden set's own total, so nothing else changed between the two measurements. The skill audit run ten seconds later still reports the listing at 73,418 of a 32,000-character budget, 2.3 times over, so Claude Code keeps truncating descriptions; the remaining load comes from skills outside this workstream. All 176 hidden skills and the 78 skill-sync entries for Magnus, yysun, Matt, Noodle, tstack and WordPress report `up-to-date` (`evidence/sync-check.txt`).

Excluded from hiding, per the brief: magnus919 (including the new web-accessibility), yysun, mattpocock, t3dotgg, poteto, WordPress (including the new wp-ability-development), and every source installed before 2026-11-25.

## Decisions

- **Alireza Rezvani (`alirezarezvani/claude-skills`)**: 30 packages across c-level advisors, commercial, finance, operations, product analytics and compliance. Medical-device and other unrelated regulatory families stay out (requirement S07-018). The C-level advisors link `../agent-protocol/SKILL.md`, which isn't installed; the ledger lists every such link.
- **Agency Agents (`msitarzewski/agency-agents`)**: role seeds only, nothing installed. Profiles invent experience (`product/product-manager.md:14`, "10+ years") and state universal numeric targets (`engineering/engineering-cms-developer.md:469`), so fleet roles take responsibilities from them and nothing else. Its `specialized/agents-orchestrator.md` is a competing orchestrator and isn't adopted.
- **Kanopi (`kanopi/cms-cultivator`)**: code-standards-checker, composer-security-update and pr-quality-report. They assume DDEV, Teamwork and Snyk (`composer-security-update/SKILL.md:10-134`, `pr-quality-report/SKILL.md:103`); none of the three exists on the reference installation, so those steps run only through a project's actual tools. Kanopi's private libraries aren't claimed.
- **WordPress (`WordPress/agent-skills`)**: the canonical WordPress source, already installed. It tracks `trunk` and targets WordPress 7.0+ and PHP 7.4+ (`README.md:187`), so a legacy client site routes by its own versions.
- **WooCommerce**: the Automattic toolkit's three skills are installed; the official `woocommerce/agent-skills` repository's two skills cover nothing the toolkit and WordPress skills leave open, so it stays source-only.
- **Cloudflare, HashiCorp, Trail of Bits**: installed and inactive. Cloudflare needs an account and scope; none is named. HashiCorp's `terraform-test` says apply is the default mode and creates real resources (`SKILL.md:28`), so qualification uses `command = plan` or mock providers, and terraform is absent here. Trail of Bits is CC BY-SA 4.0: copy its text into a local adapter and the adapter inherits ShareAlike.
- **Marketing and design**: Corey Haines's 22 and Zach Stevens's 11 skills are the canonical procedures. Sends and publishing pass the fleets' send and claims gates.
- **samber (`samber/developer-relations-skills`)**: the whole tree, 93 of 93, so the router's sibling references resolve. See the closure result below.
- **Learning Commons (`learning-commons-org/agent-skills`)**: the one canonical K-12 teaching source, all five skills; no same-named Anthropic teaching skill is installed. Rubric CSVs exist under `evals/` in the clone, but no automated evaluator is published (`evals/README.md:40`), and the rubrics aren't yet wired into the rig evaluator. That's open work, not a blocker.
- **DaRL instructional agents**: all three repositories are research pipelines (arXiv 2508.19611). They need a network pip install, an OpenAI key and LaTeX, so nothing is installed. Their "Test Student" is an LLM persona review, a fixture, never learner evidence.

## Rejected sources

- `wateryqz/instructional_agents112`: a near-copy of `DaRL-GenAI/instructional_agents`, last changed 2026-04-17, with no stated fork relationship. The canonical repository supersedes it.
- `msitarzewski/agency-agents` as an installable set, and its orchestrator.
- `woocommerce/agent-skills` for now (see above).
- The DaRL default model and simulated student as evidence of learning.

## samber closure

Every `samber/developer-relations-skills@<name>` reference under `skills/` at the pinned revision was checked against the tree (`ledger.json` `closure`): 1,224 references to 94 names, 93 of which exist. `substack-playbook` is referenced 4 times (`devto-playbook/SKILL.md:133`, `medium-playbook/SKILL.md:162` and their descriptions) and doesn't exist at the pin. The router says "65-skill collection" (`developer-relations-kickoff/SKILL.md:12`) while the tree holds 93. Skills also hand off to collections that aren't pinned, chiefly `samber/developer-platform-skills` (94 references) and `samber/dev-event-organizer-skills` (27). The devrel fleet's roles attach `api-reference-quality` and `sdk-package-publishing`, which belong to the unpinned platform collection and aren't installed.

## Name conflicts

- **Synced plugins**: `customer-research`, `seo-audit` and `design-system` also ship in synced plugins. Roles load the rig copies by path, and the hidden rig copies never compete in the model's list.
- **Fleet prefixes**: upstream names `product-marketing`, `product-analytics` and `product-film` share the product fleet's `product-` prefix, and samber's `devrel-*` skills share the devrel prefix. Skill-sync keys installs by upstream directory name, so the names stay; ownership is in the ledger, and fleet originals must not reuse these names.
- **Overlapping functions**: samber `docs-seo` against Corey Haines `ai-seo` and `seo-audit`, and the Kanopi and WordPress coding-standards checks. `agency-platform-adapters` picks per project.
- **VERIFIED naming**: Alireza's `VERIFIED.md` lists `compliance-readiness`, not the installed `compliance-os`, so no activation result covers it.

## Constraints that matter

- Alireza's VERIFIED results measure activation only: Claude Code 2.1.317, sonnet, the skill's own plugin, two positive prompts and one negative. They say nothing about business accuracy or Codex.
- Agency Agents profiles are seeds; numbers become stated hypotheses.
- Terraform tests run in plan mode or with mocked providers.
- One K-12 teaching source: Learning Commons.
- WordPress skills target recent versions.
- Learning Commons publishes rubrics, not an evaluator.
- A simulated student is a fixture.
- Kanopi workflows assume DDEV, Teamwork and Snyk.
- `yysun/project-manager` has no LICENSE file (its `plugin.json` says MIT), and `alp82/curia` has none for its own code: neither is redistributable as is. `cody-hutson/pmo-platform` is BUSL-1.1, source-available.

## Blockers and open work

| Item | Resume step |
|---|---|
| Cloudflare skills can't act | Name the account and scope, sign in with wrangler, then qualify one skill against a disposable project |
| Terraform checks can't run | Install terraform 1.7+, then run `terraform test` with `command = plan` or a mock provider on a fixture module |
| Learning Commons DOCX render | `render_all.sh` would pip-install python-docx; approve that install or render HTML only |
| DaRL pipeline | Approve the pip install, an OpenAI key and TeX, then run `course-generate` on a synthetic brief with a chosen model |
| Learning Commons rubrics in the rig evaluator | Wire the CSVs from the clone's `evals/` into the education fleet's evaluator |
| Shared marketing and design context files | Name one owner each for `.agents/product-marketing.md`, `.agents/brand.md` and `.agents/design.md` |
| `substack-playbook` and the unpinned samber collections | Pin `samber/developer-platform-skills` if the devrel roles keep attaching its skills |
