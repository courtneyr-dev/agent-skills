"""mirror: a throwaway skills root for hosting tests, so a gate's fixed owner paths land in a temp folder.

make(dest) builds dest/skills, where every entry of the real skills root is a symlink except
company-fleets/fleets/hosting/fixtures and company-fleets/fleets/hosting/owner, which are copied. A
script run from the mirror finds its owner root, owner files, fixtures and sibling skills inside the
mirror, the way it would in an installed rig, so a test can play the owner without touching the rig.
"""
from __future__ import annotations

import os
import shutil

FLEET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.normpath(os.path.join(FLEET, "..", "..", ".."))
COPIED = ("fixtures", "owner")


def _link_children(src: str, dst: str, skip: set) -> None:
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if name not in skip:
            os.symlink(os.path.join(src, name), os.path.join(dst, name))


def make(dest: str) -> str:
    """Build the mirror under dest and return its skills root."""
    root = os.path.join(dest, "skills")
    cf = os.path.join(SKILLS_ROOT, "company-fleets")
    _link_children(SKILLS_ROOT, root, {"company-fleets"})
    _link_children(cf, os.path.join(root, "company-fleets"), {"fleets"})
    _link_children(os.path.join(cf, "fleets"), os.path.join(root, "company-fleets", "fleets"), {"hosting"})
    fleet = os.path.join(root, "company-fleets", "fleets", "hosting")
    _link_children(FLEET, fleet, set(COPIED))
    for name in COPIED:
        src = os.path.join(FLEET, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(fleet, name), symlinks=True)
        else:
            os.makedirs(os.path.join(fleet, name))
    return root


def fleet_dir(root: str) -> str:
    return os.path.join(root, "company-fleets", "fleets", "hosting")


def owner_dir(root: str, skill: str) -> str:
    return os.path.join(fleet_dir(root), "owner", skill)


def fixtures(root: str, *parts: str) -> str:
    return os.path.join(fleet_dir(root), "fixtures", *parts)


def script(root: str, skill: str, name: str) -> str:
    return os.path.join(root, skill, "scripts", name)
