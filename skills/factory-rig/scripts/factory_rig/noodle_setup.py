"""Install the rig's Noodle skills into a project as real directories, and detect drift.

Override NOODLE-SKILL-RESOLUTION: Noodle builds its task-type registry from skill.Resolver.List(), which
skips symlinked skill directories (DirEntry.IsDir is false for symlinks), so a rig skill reached through
a symlinked skills mount is never registered and orders naming it are dropped at normalization.
The canonical files stay in this skills folder (factory-execute, factory-rig/noodle/schedule-stub);
this module writes generated real-directory copies into <project>/.agents/skills and records their hashes.
Preflight refuses to dispatch when a copy differs from its canonical source.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Dict, List

from .canon import sha_file

SKILLS_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CANONICAL: Dict[str, str] = {
    "factory-execute": os.path.join(SKILLS_ROOT, "factory-execute", "SKILL.md"),
    "schedule": os.path.join(SKILLS_ROOT, "factory-rig", "noodle", "schedule-stub", "SKILL.md"),
}
MANIFEST = ".frig-skills.json"


IGNORE_LINES = [".noodle/", ".worktrees"]  # no trailing slash on .worktrees, see ensure_gitignore


def ensure_gitignore(repo: str) -> bool:
    """Make Noodle's first worktree creation leave the integration checkout clean (override NOODLE-GITIGNORE).

    Noodle runs `git check-ignore -q .worktrees` before creating a worktree and appends ".worktrees/" when
    that fails. With the pattern ".worktrees/" the check fails while the directory does not exist yet (a
    trailing-slash pattern only matches directories), so Noodle dirties .gitignore in the primary checkout.
    The pattern ".worktrees" matches whether or not the directory exists. Returns True when it edited the file.
    """
    path = os.path.join(repo, ".gitignore")
    existing = open(path, "r", encoding="utf-8").read().split("\n") if os.path.exists(path) else []
    missing = [l for l in IGNORE_LINES if l not in existing]
    if not missing:
        return False
    with open(path, "a", encoding="utf-8") as fh:
        if existing and existing[-1] != "":
            fh.write("\n")
        fh.write("\n".join(missing) + "\n")
    return True


def install(repo: str) -> List[str]:
    ensure_gitignore(repo)
    base = os.path.join(repo, ".agents", "skills")
    written = []
    manifest = {}
    for name, src in CANONICAL.items():
        dest_dir = os.path.join(base, name)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "SKILL.md")
        shutil.copyfile(src, dest)
        manifest[name] = sha_file(dest)
        written.append(dest)
    with open(os.path.join(base, MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return written


def drift(repo: str) -> List[str]:
    """Reasons the project's copies no longer match the canonical rig skills (empty means in sync)."""
    base = os.path.join(repo, ".agents", "skills")
    problems = []
    for name, src in CANONICAL.items():
        dest = os.path.join(base, name, "SKILL.md")
        if not os.path.isfile(dest):
            problems.append("%s: project copy missing (run frig noodle-init)" % name)
        elif sha_file(dest) != sha_file(src):
            problems.append("%s: project copy differs from the canonical rig skill (rerun frig noodle-init)" % name)
    return problems
