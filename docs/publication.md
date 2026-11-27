# Publication

This repository is a **release artifact**, not a second place to edit skills. Most files under
`skills/` are generated from a private canonical source; a few are written here by hand.

> **Public-authored skills are maintained directly in `agent-skills` and must never be overwritten
> by the generator.**

## Complete skill artifacts

Publication governs a whole skill **directory**, not just its `SKILL.md`. Every supporting file —
scripts, references, templates, example configs, fixtures — carries an explicit mode in
`publish/policy.yml`:

```yaml
skills:
  gatherer:
    mode: generated
    files:
      trac-watchlist.txt: generated        # transform(canonical); hashed in the lock
      scripts/gather.py: public-authored   # hand-written for public users; apply never touches it
      tests/test_gather.py: public-authored
  readwise-synthesis-pass:
    files:
      state.json: excluded                 # runtime state; must never publish
```

Skill-level and file-level ownership are deliberately independent. A `generated` skill can contain
a `public-authored` supporting file, and it usually should when the mechanical transform would
produce something worse. Several public scripts here resolve the vault directory at runtime
(`os.environ.get("VAULT_DIR", "~/Documents/Notes")`) where the transform would emit a literal
`$VAULT_DIR` that does not work — those files are `public-authored` for exactly that reason.

### Defaults fail closed in both directions

```yaml
defaults:
  supporting_files:
    undeclared_canonical: excluded   # a new private file cannot leak by appearing on disk
    undeclared_public: blocked       # a stale or hand-added public file cannot hide
```

An **allowlist** was chosen over "publish everything except exclusions". Canonical skill
directories hold `.bak` files, real site configs, run-state ledgers and scripts that push to
private infrastructure; with a denylist, any one of those publishes the moment someone forgets an
exclusion. The cost is that adding a supporting file to a public skill takes a policy line. That is
the intended friction.

### Executable bit and symlinks

Generated scripts keep their executable bit, and the lock records it with a trailing `x`, so a
mode-only change is drift. Six published scripts had silently lost `+x` before this was tracked.

Supporting files that are **symlinks are refused**, not dereferenced. There is no symlink
publication policy, so publishing one would be a guess about whether the link or its content is
the artifact.

### Retirement

A canonical file that disappears does **not** delete its public output. `apply` refuses while a
declared source is missing, and the published file stays. Removing something from the public tree
is a deliberate policy edit, never a side effect of a missing source.

## Two classes

| Mode | Count | Who owns the file | Generator behaviour |
|---|---:|---|---|
| `generated` | 67 | the private canonical skill | rewrites it; hand edits are drift |
| `public-authored` | 8 | this repository | never written; validated only |

Public-authored: `wiki-cycle`, `weekly-site-health-audit`, `wiki-memory`,
`readwise-methods-review`, `job-search`, `company-fleets`, `factory-rig`, `factory-execute`. These
are hand-written public editions with setup instructions and rationale a private copy has no reason
to carry. `job-search` has no private counterpart at all. The last three are public editions of rig
skills whose canonical copies hold run state; see [Company fleet skills](#company-fleet-skills).

A skill with no declared mode is an **error**. Nothing is assumed to be generated.

## Commands

```bash
python3 publish/publish_skills.py --dry-run   # default; writes nothing, shows unified diffs
python3 publish/publish_skills.py --apply     # writes generated skills only
python3 publish/publish_skills.py --check     # CI drift detector; non-zero on any drift
python3 publish/publish_skills.py --apply --only NAME...   # publish or check named skills only
python3 publish/tests/test_publish.py         # 41 tests
```

`--only` exists because a full `--apply` refuses while any declared source is missing, and a full
`--check` reports every skill whose canonical copy moved. With `--only`, apply writes the named
skills and keeps every other skill's lock lines; check compares the named skills and still
validates the manifest against the whole policy. `--verify-public` always covers every skill.

`--check` fails when a generated file was hand-edited, a canonical source changed without
republishing, policy references a missing source, the manifest and policy disagree, or a privacy
gate trips. For public-authored skills it only checks the file exists — it never compares them to a
canonical source.

## Adding a skill

**Generated:** add to `publish/policy.yml` with `mode: generated` and a `source` (a directory name
under `canonical_root`). Run `--dry-run`, read the diff, then `--apply`.

**Public-authored:** create `skills/<name>/SKILL.md` by hand and add `mode: public-authored` with a
`reason`. The generator will skip it forever.

## Transforms

Nineteen explicit named operations in `publish/transforms.py`, applied in the order the policy lists.
There is deliberately no general "remove anything personal" pass — every rule exists because a
specific skill needed it, and each has a test.

Identity and grammar: `full_name_and_agreement` (runs before `replace_personal_name`, so
"Courtney Robertson" never becomes "the user Robertson"), `replace_personal_name`,
`second_person_owner`. The pronoun rule preserves verb agreement: *she is → you are*,
*she approves → you approve*, *she tries → you try*. A naive `she → you` produces "you is" and is
rejected by tests.

Paths, longest prefix first: `vault_dir_variable`, `normalize_home_path`,
`genericize_vault_name`, `collapse_loop_reports_path`, `strip_para_number_prefix`.

Identifiers: `genericize_domain`, `genericize_identifiers`, `genericize_personal_site`,
`placeholder_private_example`.

Fleet skills: `public_license_frontmatter`, `public_rig_rights`, `private_prompt_reference`,
`private_branch_reference`, `credit_pstack_upstream`, `rig_mount_paths`, `synthetic_token_prefix`.
They run only in the fleet skills' shared list (`&fleet_transforms` in the policy), which leaves out
`second_person_owner`: in a claims checker it rewrote the pronoun set `"she"` to `"you"` and a
regex's `her` to `your`, and every test still passed. Read the transformed code, not only the
test result.

Per-skill `omit_lines_containing` removes named SKILL.md lines declaratively, and `replace_text`
rewrites named text in SKILL.md or a generated supporting file — the content to change is written
in the policy, never guessed. A `replace_text` entry whose text no longer appears in canonical
fails closed, so a canonical edit cannot quietly reopen a line the rewrite closed.

## Safety gates

Generation fails closed on: private absolute home paths, uncovered personal-name forms, the private
vault name, the private domain, credential-shaped assignments, private-key blocks, GitHub/API token
shapes, and explicit `<!-- private -->` markers.

**This is a named-pattern scan. It does not prove the absence of private information.** It catches
the forms we know about.

## Retirement

Explicit only. Add the name under `retired:` in the policy. **A missing canonical source never
deletes public output** — it is reported as a problem and the run refuses to apply.

## Manifest

`manifest.json` stays hand-maintained and is **validated, not regenerated**. It carries judgment —
attribution, licence interpretation, private exclusions — that heuristics must not overwrite.
`--check` verifies only the derivable facts: that policy and manifest agree on which skills are
vendored, and that no vendored skill is marked non-redistributable.

## Never published

External upstream skills (referenced in the manifest, never vendored), plugin-managed skills,
private-only skills, non-redistributable skills, and generated/synced outputs.

## What CI can and cannot prove

CI runs against this public repository. The canonical sources are private and are **not** available
to GitHub Actions, so the workflow cannot compare generated output to them.

| Check | Local | CI | Why |
|---|---|---|---|
| Transform unit tests | yes | yes | pure logic, no private input |
| Policy integrity (every skill has a mode) | yes | yes | reads `policy.yml` only |
| Public-authored protection | yes | yes | policy + repository files |
| Generated artifact matches `generated.lock` | yes | yes | lock is committed |
| Manifest/policy agreement | yes | yes | both in-repo |
| **Canonical drift** (source changed without republish) | **yes** | **no** | needs the private sources |

`--verify-public` is the CI mode. It proves every generated artifact is byte-identical to what the
publisher produced when `--apply` last ran, which catches hand edits made directly in the public
repo. It does **not** prove the artifacts are current with respect to canonical sources — only a
local `--check` can do that.

The test suite is scoped the same way. `publish/tests/test_publish.py` skips the five tests that
genuinely need the private sources when they are absent, and prints which mode it ran in. It is
never weakened to make CI green — the skipped tests still run in full locally.

`publish/generated.lock` is written by `--apply` and records the sha256 of each generated
`SKILL.md`. Public-authored skills are deliberately absent from it; a test fails if one appears.

Since complete-artifact publication landed, `--verify-public` also proves, using only files in
this repository: every generated supporting file matches its lock hash and executable bit, no
generated supporting file is missing, no `public-authored` or `excluded` file is hashed as
generated, no `excluded` file is present publicly, and no undeclared file sits in a generated skill
directory. It still cannot see canonical drift — that needs the private sources and stays in local
`--check`.

## Company fleet skills

Added in 1.1.0: 37 gate skills, `company-fleets`, `factory-rig` and `factory-execute`.

- **Gates are generated.** Each gate's files are an explicit allowlist taken from its tracked
  canonical files: SKILL.md, scripts, tests, references, evals and the fixtures its tests read.
  Their tests run from the published copies (1,012 tests), because a transform can change code.
- **Sibling layout is load-bearing.** Gates import `company-fleets/scripts/fleetlib` and
  `factory-rig/scripts/factory_rig`, and read hosting owner records and fixtures under
  `company-fleets/fleets/`. All of them sit under `skills/` so the relative paths hold.
- **Three editions are public-authored.** Their canonical copies hold run folders, owner ledgers,
  leases, review reports and machine paths. The editions keep what `validate --strict`, the tests
  and the gates read, measured by tracing file opens, and leave the rest out: 1,027 of 4,706
  company-fleets files ship. Machine values are environment variables with defaults relative to
  the skill folder, documented in `config.example.env` and `config/frig.example.env`.
- **Upstream skills stay external.** Roles attach 167 skills from other repositories. Each such
  attachment carries `"blocked_reason": "external: install from <owner/repo>; see the catalog"`,
  `registry/external-skills.json` lists them, and `validate` checks the two agree. Eval cases and
  acceptance rows that need those skills, Docker or rig-only scripts report blocked or fail in a
  public checkout; the SKILL.md says which.
- **Synthetic secrets look synthetic.** Fixture tokens use `fx_demo_`, and the tenant-isolation
  owner records were rebuilt with the owner commands after the rename. The leaked preview's
  sandbox record needs Docker to rebuild and still binds the pre-rename bytes; `promote` refuses
  that preview either way.
- **The hosting benchmark stays neutral.** It cites public Acquia, Pantheon and WordPress VIP
  documentation, lists providers alphabetically, states only what each cited page says, and keeps
  documented claim, proposed target, configured capability, measured result and contractual
  commitment in separate fields. Superiority claims appear only as inputs the gate must refuse.
- **gitleaks.** `.gitleaks.toml` extends the default rules with one allowlist: a JSON
  `"idempotency_key"` of 32 hex characters, a truncated sha256 of synthetic handoff content.

## Installation is a separate concern

Publication mode (generated vs public-authored) says nothing about installation. Both are
legitimate public artifacts and `install.sh` treats every skill identically. The publisher owns how a
file gets into `skills/`; the installer owns how it reaches an agent.

`install.sh` is non-destructive by construction: it creates missing links and reports every other
destination state as a conflict. Converting an existing copy, or repointing a link, is a migration
and is deliberately not automated. `--dry-run` is the default.

`-p <path>` limits a run to the skills `manifest.json` lists under `paths.<path>.skills`, plus any
`paths.<path>.requires`: the fleets, education and hosting paths require `company-fleets` and
`factory-rig`, because their scripts import those two from beside themselves. `--guided` asks one
question per path and then runs the same selection. Without `-p` or `--guided`, `--apply` links
all 75 skills.

## Cross-agent evidence

| Agent | Mechanism | Evidence |
|---|---|---|
| Claude Code | directory symlink | runtime-proven: lists, describes, invokes; relative resources resolve |
| Codex | directory symlink | runtime-proven: same, including `references/` through the link |
| OpenClaw | directory symlink | observed in production (45/45 links) |
| Cursor | directory symlink | **filesystem only** — no CLI on PATH, runtime invocation never tested |
| Gemini CLI | directory symlink | path supported; no installation observed |
