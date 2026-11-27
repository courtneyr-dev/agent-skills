#!/usr/bin/env python3
"""List the eval cases that need a skill or tool this repository doesn't ship, and what each needs.

    python3 scripts/eval-external-needs.py            # print the list
    python3 scripts/eval-external-needs.py --write    # rewrite registry/eval-external-needs.json
    python3 scripts/eval-external-needs.py --check    # exit 1 when that file is stale

A resolve case runs `bin/fleet resolve` and refuses '"installed": false', so it needs every skill its
resolved roles attach that registry/external-skills.json lists. Those ids come from the registry, not
from a run. DECLARED holds the few cases that reach an upstream skill or a local tool another way.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from fleetlib.evalrun import script_cases  # noqa: E402
from fleetlib.registry import Registry  # noqa: E402
from fleetlib.resolve import resolve  # noqa: E402

OUT = os.path.join(ROOT, "registry", "eval-external-needs.json")
INSTALLED_FALSE = '"installed": false'
WORDPRESS = ["wordpress-router", "wp-project-triage", "wp-plugin-development", "wp-block-development",
             "wp-block-themes", "wp-rest-api", "wp-performance", "wp-wpcli-and-ops", "wp-phpstan", "wp-playground"]
PLAYWRIGHT = "node_modules with playwright and axe-core (AGENCY_A11Y_NODE_MODULES)"
DECLARED = {
    "agency.eval.adapter-current-wordpress": {"skills": WORDPRESS + ["code-standards-checker"], "tools": []},
    "agency.eval.keyboard-defects-missed-by-axe-found": {"skills": [], "tools": [PLAYWRIGHT]},
    "agency.eval.keyboard-fixed-page-no-false-positives": {"skills": [], "tools": [PLAYWRIGHT]},
    "agency.eval.scoped-brief-to-verified-handoff": {"skills": [], "tools": [PLAYWRIGHT]},
    "devrel.eval.routes-installed-pass": {"skills": ["developer-journey-map", "developer-quickstart-guide",
                                                     "docs-code-sample-standards", "developer-workshop-program",
                                                     "developer-feedback-loop", "devrel-metrics"], "tools": []},
    "devrel.eval.routes-scan-finds-drift": {"skills": ["devto-playbook", "medium-playbook"], "tools": []},
    "product.eval.gate-ready-candidate": {"skills": ["release-engineering"], "tools": []},
    "hosting.eval.tenant-isolation-sandbox-isolated": {"skills": [], "tools": ["a running Docker daemon"]},
    "hosting.eval.tenant-isolation-sandbox-control-leaks": {"skills": [], "tools": ["a running Docker daemon"]},
    "hosting.eval.tenant-isolation-liar-build-control-leaks": {"skills": [], "tools": ["a running Docker daemon"]},
    "hosting.eval.role-build-runtime-engineer": {"skills": [], "tools": ["a running Docker daemon"]},
}
DECLARED_SOURCES = dict({s: "WordPress/agent-skills" for s in WORDPRESS},
                        **{"code-standards-checker": "kanopi/cms-cultivator",
                           "devto-playbook": "samber/developer-relations-skills",
                           "medium-playbook": "samber/developer-relations-skills"})


def _arg(argv, flag):
    return argv[argv.index(flag) + 1]


def build(root=ROOT):
    with open(os.path.join(root, "registry", "external-skills.json"), encoding="utf-8") as fh:
        external = json.load(fh)["skills"]
    cases, case_ids = {}, set()
    for _fleet, _path, _doc, case in script_cases(root):
        case_ids.add(case["id"])
        argv = case["check"]["argv"]
        absent = argv + list(case["check"].get("expect", {}).get("absent", []))
        if "resolve" in argv and INSTALLED_FALSE in absent:
            out = resolve(Registry(root), _arg(argv, "--profile"), _arg(argv, "--workload"))
            skills = sorted({s["id"] for r in out["roles"] for s in r["skills"] if s["id"] in external})
            if skills:
                cases[case["id"]] = {"skills": skills, "tools": []}
    missing = sorted(set(DECLARED) - case_ids)
    if missing:
        raise SystemExit("DECLARED names cases no evals.json has: %s" % ", ".join(missing))
    cases.update({k: {"skills": sorted(v["skills"]), "tools": v["tools"]} for k, v in DECLARED.items()})
    sources = dict(external, **DECLARED_SOURCES)
    used = sorted({s for c in cases.values() for s in c["skills"]})
    unsourced = [s for s in used if s not in sources]
    if unsourced:
        raise SystemExit("no install source for: %s" % ", ".join(unsourced))
    return {
        "label": "Eval cases that can't pass from this repository alone, and the upstream skills or local tools "
                 "each needs. Install each skill from its source into the skills folder that holds company-fleets "
                 "(agency-platform-adapters looks for the WordPress ones in ~/.agents/skills); role attachments "
                 "name the same source in blocked_reason.",
        "generated_by": "scripts/eval-external-needs.py --write",
        "cases": dict(sorted(cases.items())),
        "sources": {s: sources[s] for s in used},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = json.dumps(build(), indent=2) + "\n"
    if a.write:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(text)
        return 0
    if a.check:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("registry/eval-external-needs.json is stale; run scripts/eval-external-needs.py --write")
            return 1
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
