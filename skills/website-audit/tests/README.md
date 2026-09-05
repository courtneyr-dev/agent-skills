# Tests

`coverage-test.py` proves the installed skill did not drop anything from the master playbook.

```bash
python3 ~/.claude/skills/website-audit/tests/coverage-test.py
```

Rerun it after **every** change to the source playbook at
`$VAULT_DIR/Areas/Website UX Audits/website-ux-navigation-design-audit-master-prompt.md`.
That is the guard against the source and the skill quietly drifting apart.

It checks: frontmatter legality and the 1,536-char listing cap · required file structure ·
progressive loading (SKILL.md defers rather than inlines) · all 19 Standing Rules present ·
all 6 evidence labels present · all 24 framing fields mapped in the intake coverage table ·
every unsupplied section explicitly declared rather than silently invented.
