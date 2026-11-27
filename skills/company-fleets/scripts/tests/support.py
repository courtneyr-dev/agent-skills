"""Hermetic registry roots for tests: the shipped registry/*.json, empty files for every fleet, then
the sample fleets from fixtures/, and a fake skills root holding only the skills the samples attach."""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from fleetlib.registry import Registry  # noqa: E402

FIXTURES = os.path.join(SKILL, "fixtures")


def make_root(tmp, sample=True):
    root = os.path.join(tmp, "root")
    skills_root = os.path.join(tmp, "skills")
    os.makedirs(os.path.join(root, "registry"))
    for name in ("company.json", "fleets.json", "profiles.json"):
        shutil.copy(os.path.join(SKILL, "registry", name), os.path.join(root, "registry", name))
    fleets = [f["id"] for f in json.load(open(os.path.join(root, "registry", "fleets.json")))["fleets"]]
    for f in fleets:
        d = os.path.join(root, "fleets", f)
        os.makedirs(d)
        for kind, extra in (("roles", {"roles": [], "workloads": []}), ("skills", {"skills": []}), ("evals", {"evals": []})):
            write(os.path.join(d, kind + ".json"), dict({"schema_version": 1, "fleet": f}, **extra))
    if sample:
        src = os.path.join(FIXTURES, "sample-fleets")
        for f in os.listdir(src):
            shutil.copytree(os.path.join(src, f), os.path.join(root, "fleets", f), dirs_exist_ok=True)
    os.makedirs(os.path.join(skills_root, "verification-methodology"))
    open(os.path.join(skills_root, "verification-methodology", "SKILL.md"), "w").write("---\nname: verification-methodology\n---\n")
    return Registry(root, skills_root)


def read(reg, rel):
    with open(reg.path(rel)) as fh:
        return json.load(fh)


def write(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)


def edit(reg, rel, fn):
    """Apply fn to the parsed file and write it back; returns a fresh Registry so files_read starts empty."""
    doc = read(reg, rel)
    fn(doc)
    write(reg.path(rel), doc)
    return Registry(reg.root, reg.skills_root)


def messages(result):
    return [e["message"] for e in result["errors"]]


def isolate_owner_root(test):
    """Repoint the owner root (fleets/<fleet>/owner) to a temp folder for one test; gates read the same module attribute."""
    import tempfile
    from fleetlib import ownerlog
    tmp = tempfile.mkdtemp(prefix="owner-root-")
    old = ownerlog.FLEETS_ROOT
    ownerlog.FLEETS_ROOT = tmp
    test.addCleanup(shutil.rmtree, tmp, True)
    test.addCleanup(setattr, ownerlog, "FLEETS_ROOT", old)
    return tmp
