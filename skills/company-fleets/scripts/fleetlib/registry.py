"""Registry file layout and loading. Every read goes through Registry.load, which records the
relative path, so a caller can prove which files a command opened."""
from __future__ import annotations

import json
import os
from typing import Any, List

from . import SKILL_DIR

COMPANY = "registry/company.json"
FLEETS = "registry/fleets.json"
PROFILES = "registry/profiles.json"
REQUIREMENTS = "registry/requirements.json"
FLEET_KINDS = ("roles", "skills", "evals")


def fleet_file(fleet: str, kind: str) -> str:
    return "fleets/%s/%s.json" % (fleet, kind)


def fleet_of(namespaced_id: str) -> str:
    return namespaced_id.split(".", 1)[0]


class Registry:
    """A registry root (the skill directory by default) plus the rig skills root that holds skills/<id>/."""

    def __init__(self, root: str = SKILL_DIR, skills_root: str = ""):
        self.root = os.path.abspath(root)
        self.skills_root = os.path.abspath(skills_root or os.path.dirname(self.root))
        self.files_read: List[str] = []

    def path(self, rel: str) -> str:
        return os.path.join(self.root, rel)

    def exists(self, rel: str) -> bool:
        return os.path.isfile(self.path(rel.split("#", 1)[0]))

    def load(self, rel: str) -> Any:
        self.files_read.append(rel)
        with open(self.path(rel), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def skill_md(self, skill_id: str) -> str:
        return os.path.join(self.skills_root, skill_id, "SKILL.md")

    def skill_installed(self, skill_id: str) -> bool:
        return os.path.isfile(self.skill_md(skill_id))

    def fleet_dirs(self) -> List[str]:
        base = self.path("fleets")
        if not os.path.isdir(base):
            return []
        return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
