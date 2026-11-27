# Sources

| Source | Location | Version | Rights | What this skill takes from it |
|---|---|---|---|---|
| developer-quickstart-guide, `references/verification-protocol.md` and § Pass threshold | https://github.com/samber/developer-relations-skills/tree/c3a1b6912791539567727723baf626b4fec5ac7a/skills/developer-quickstart-guide | commit c3a1b6912791539567727723baf626b4fec5ac7a (2026-11-08) | MIT, copyright 2026 Samuel Berthe | The five cold-run criteria and the CI regression job this tool implements. Cited, not copied. |
| docs-code-sample-standards, `scripts/sample-audit.py` | https://github.com/samber/developer-relations-skills/tree/c3a1b6912791539567727723baf626b4fec5ac7a/skills/docs-code-sample-standards | same commit | MIT, copyright 2026 Samuel Berthe | The `tier=run` fence info-string convention, so the linter and the replay read the same markup. |
| macOS `sandbox-exec(1)` | `/usr/bin/sandbox-exec`, `man sandbox-exec` | macOS 26, checked 2026-11-25; Apple marks the tool deprecated | Apple system software; invoked, not redistributed | Denies outbound network except localhost and reads under the user's home. Checked on macOS on 2026-11-25: Python 3.9 ran, localhost answered 200, 1.1.1.1:443 raised PermissionError, listing the home directory failed. |
| Python standard library | `subprocess`, `os.killpg`, `tempfile` | 3.9 and later | PSF License | Process-group cleanup and disposable directories. |
