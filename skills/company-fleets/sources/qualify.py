#!/usr/bin/env python3
"""Run installed upstream scripts on synthetic Fixture Co inputs; write evidence/qualification.json.

Every fixture is written to a fresh temporary directory, which is also the working directory, so relative
paths always resolve. A case passes when the exit code matches its documented contract (and the output holds
the expected text); a case whose declared dependency is missing is blocked, not failed. A rejection that
surfaces as a Python traceback still counts as a rejection, but it is recorded as a defect.
Usage: python3 qualify.py
"""

import json
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[2] / "skills"
PY = sys.executable

PROFILE = {"company": "Fixture Co (synthetic)", "industry": "saas", "products_include_ai": True, "ai_high_risk_per_eu": False,
           "deploys_ai_in_eu": False, "products_are_medical_devices": False, "sells_to_eu_customers": True,
           "sells_to_us_customers": True, "sells_to_enterprise_b2b": True, "processes_personal_data": True,
           "processes_eu_personal_data": True, "headcount": 40, "stage": "series_a", "processes_phi": False,
           "us_healthcare_covered_entity": False, "us_healthcare_business_associate": False, "nis2_essential_entity": False,
           "nis2_important_entity": False, "adopts_nist_csf": False, "us_government_contractor": False}
FILES = {
    "profile.json": json.dumps(PROFILE),
    "malformed.json": '{"company": "Fixture Co", ',
    "bad.csv": "not,a,ledger\n1,2\n",
    "composer.lock": json.dumps({"packages": [{"name": "fixture/vulnerable-lib", "version": "1.0.0"}]}),
    "audit.json": json.dumps({"advisories": {"fixture/vulnerable-lib": [{"advisoryId": "PKSA-fixture-0001", "packageName": "fixture/vulnerable-lib",
                                                                        "affectedVersions": "<1.0.1", "title": "Synthetic advisory for Fixture Co",
                                                                        "cve": None, "link": "https://example.invalid/advisory", "severity": "high"}]}}),
    "lesson-bad.json": json.dumps({"title": "Fixture lesson", "documents": "not-a-list"}),
    "docs/quickstart.md": "# Fixture Co quickstart\n\n```bash\ncurl -H 'Authorization: Bearer FIXTURE_TOKEN' https://api.example.invalid/v1/items\n```\n",
}


def s(skill, script):
    return str(SKILLS / skill / "scripts" / script)


# (skill, kind, argv, stdin file, expected exit codes, expected output text, dependency that may block the case)
CASES = [
    ("month-end-close", "positive", [PY, s("month-end-close", "reconciliation_matcher.py"), "--sample", "--output", "json"], None, {4}, "UNRECONCILED", None),
    ("month-end-close", "negative", [PY, s("month-end-close", "reconciliation_matcher.py"), "--gl", "bad.csv", "--source", "bad.csv"], None, {3}, None, None),
    ("compliance-os", "positive", [PY, s("compliance-os", "framework_selector.py"), "profile.json", "--output", "json"], None, {0}, None, None),
    ("compliance-os", "negative", [PY, s("compliance-os", "framework_selector.py"), "malformed.json"], None, "nonzero", None, None),
    ("pricing-strategist", "positive", [PY, s("pricing-strategist", "pricing_model_picker.py"), "--sample", "--output", "json"], None, {0}, None, None),
    ("pricing-strategist", "negative", [PY, s("pricing-strategist", "pricing_model_picker.py"), "--input", "malformed.json"], None, "nonzero", None, None),
    ("pricing-strategist", "boundary", [PY, s("pricing-strategist", "pricing_model_picker.py"), "--sample", "--profile", "agency"], None, {2}, None, None),
    ("capacity-planner", "positive", [PY, s("capacity-planner", "capacity_modeler.py"), "--sample", "--output", "json"], None, {0}, None, None),
    ("capacity-planner", "negative", [PY, s("capacity-planner", "capacity_modeler.py"), "--input", "malformed.json"], None, "nonzero", None, None),
    ("channel-economics", "positive", [PY, s("channel-economics", "cost_to_serve_calculator.py"), "--sample", "--output", "json"], None, {0}, None, None),
    ("channel-economics", "negative", [PY, s("channel-economics", "cost_to_serve_calculator.py"), "--input", "malformed.json"], None, "nonzero", None, None),
    ("composer-security-update", "positive", [PY, s("composer-security-update", "audit_table.py"), "composer.lock"], "audit.json", {0}, "fixture/vulnerable-lib", None),
    ("composer-security-update", "negative", [PY, s("composer-security-update", "audit_table.py")], "malformed.json", "nonzero", None, None),
    ("docs-code-sample-standards", "positive", [PY, s("docs-code-sample-standards", "sample-audit.py"), "--format", "summary", "docs"], None, {0, 1}, None, None),
    ("docs-code-sample-standards", "negative", [PY, s("docs-code-sample-standards", "sample-audit.py"), "no-such-docs"], None, "nonzero", None, None),
    ("developer-community-health", "positive", ["bash", s("developer-community-health", "contributor-absence-factor.sh"), "-r", "repo"], None, {0}, None, None),
    ("developer-community-health", "negative", ["bash", s("developer-community-health", "contributor-absence-factor.sh"), "-r", "no-such-repo"], None, "nonzero", None, None),
    ("developer-community-health", "boundary", ["bash", s("developer-community-health", "contributor-absence-factor.sh"), "-r", "repo", "-p", "150"], None, "nonzero", None, None),
    ("k12-lesson-plan-creation", "positive", [PY, s("k12-lesson-plan-creation", "render_lesson_html.py"), str(SKILLS / "k12-lesson-plan-creation/references/example_lesson.json"), "-o", "lesson.html"], None, {0}, "wrote lesson.html", None),
    ("k12-lesson-plan-creation", "negative", [PY, s("k12-lesson-plan-creation", "render_lesson_html.py"), "lesson-bad.json", "-o", "bad.html"], None, "nonzero", None, None),
    ("k12-lesson-plan-creation", "boundary", [PY, s("k12-lesson-plan-creation", "render_lesson_docx.py"), str(SKILLS / "k12-lesson-plan-creation/references/example_lesson.json")], None, {0}, None, "python-docx"),
]


def synthetic_repo(path):
    """Five synthetic authors with uneven commit counts, so the absence factor has something to measure."""
    path.mkdir()
    run = lambda *a, **kw: subprocess.run(["git", *a], cwd=path, check=True, capture_output=True, **kw)
    run("init", "-q")
    for i, (author, commits) in enumerate([("Ada Fixture", 6), ("Ben Fixture", 3), ("Cy Fixture", 2), ("Di Fixture", 1), ("Ed Fixture", 1)]):
        for n in range(commits):
            (path / f"f{i}.txt").write_text(f"{author} {n}\n")
            run("add", ".")
            run("-c", f"user.name={author}", "-c", f"user.email=f{i}@example.invalid", "commit", "-q", "-m", f"synthetic {n}")


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for rel, text in FILES.items():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / rel).write_text(text)
        synthetic_repo(work / "repo")
        for skill, kind, argv, stdin, expect, needle, dep in CASES:
            with open(work / stdin) if stdin else open("/dev/null") as fh:
                r = subprocess.run(argv, cwd=work, stdin=fh, capture_output=True, text=True, timeout=120)
            out = (r.stdout + r.stderr).replace(str(Path.home()), "~")
            ok = (r.returncode != 0) if expect == "nonzero" else (r.returncode in expect)
            ok = ok and (needle is None or needle in out)
            outcome = "pass" if ok else ("blocked" if dep and dep in out else "fail")
            case = {"skill": skill, "case": kind, "expect": expect if expect == "nonzero" else sorted(expect),
                    "expect_text": needle, "exit": r.returncode, "outcome": outcome,
                    "command": " ".join(a.replace(str(Path.home()), "~") for a in argv) + (f" < {stdin}" if stdin else ""),
                    "output_head": out[:600]}
            if r.returncode != 0 and "Traceback (most recent call last)" in out:
                case["defect"] = "rejects with an unhandled Python traceback instead of an error message"
            if outcome == "blocked":
                case["blocked_by"] = dep
            results.append(case)
    doc = {"runner": "qualify.py", "ran": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(),
           "_note": "Synthetic Fixture Co inputs written to a temporary working directory; outputs truncated to 600 characters. pass means the exit code (and expected text) matched the script's documented contract.",
           "results": results}
    (HERE / "evidence/qualification.json").write_text(json.dumps(doc, indent=1) + "\n")
    counts = {o: sum(1 for c in results if c["outcome"] == o) for o in ("pass", "fail", "blocked")}
    defects = sum(1 for c in results if c.get("defect"))
    print(f"qualification: {len(results)} cases, {counts['pass']} pass, {counts['fail']} fail, {counts['blocked']} blocked, {defects} traceback defects")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
