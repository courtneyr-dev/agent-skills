#!/bin/sh
# Rerun every foundation check and write raw output to evidence/foundation-tests.txt.
skill=$(cd "$(dirname "$0")/.." && pwd)
rig=$(cd "$skill/../.." && pwd)
out="$skill/evidence/foundation-tests.txt"
mkdir -p "$skill/evidence"
{
  echo "# company-fleets foundation evidence, $(date -u +%Y-%m-%dT%H:%MZ), repository HEAD $(git -C "$rig" rev-parse --short HEAD 2>/dev/null || echo none)"
  echo "# All fixture data is synthetic (Fixture Co)."
  for py in python3 /usr/bin/python3; do
    command -v "$py" >/dev/null 2>&1 || continue
    echo; echo "## unit tests, $($py --version 2>&1)"
    echo "\$ cd scripts/tests && $py -W ignore -m unittest discover -p 'test_*.py' -v"
    (cd "$skill/scripts/tests" && $py -W ignore -m unittest discover -p 'test_*.py' -v 2>&1); echo "exit=$?"
  done
  echo; echo "## factory-rig tests (imported modules: canon, contract, receipts, lease)"
  echo "\$ cd ../factory-rig/scripts && python3 -W ignore -m unittest tests.test_core tests.test_flow"
  res=$(cd "$skill/../factory-rig/scripts" && python3 -W ignore -m unittest tests.test_core tests.test_flow 2>&1); code=$?
  echo "$res" | tail -4; echo "exit=$code"
  echo; echo "## live registry"
  echo "\$ bin/fleet validate --strict"
  "$skill/bin/fleet" validate --strict; echo "exit=$?"
  echo "\$ bin/fleet coverage  (requirements summary only)"
  "$skill/bin/fleet" coverage | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d["requirements"]; print(json.dumps({"registry_errors": d["registry_errors"], "rows": r["rows"], "uncovered": r["uncovered"], "by_workstream": r["by_workstream"]}, indent=2))'
  echo; echo "## adversarial pack on the demonstrated gates"
  for g in corporate-email-guard product-release-gate; do
    echo "\$ bin/fleet adversarial --skill $g"
    "$skill/bin/fleet" adversarial --skill "$g" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get("counts"))); [print("  %-40s %-10s %s" % (p["name"], p["result"], p.get("known_gap", ""))) for p in d["probes"]]'
  done
  echo "# eval-run equivalence: see evidence/eval-run-equivalence.txt (scripts/eval-equivalence.py)"
  head -3 "$skill/evidence/eval-run-equivalence.txt" 2>/dev/null || echo "(not written yet: python3 scripts/eval-equivalence.py)"
  echo; echo "## rig skill validator (needs PyYAML; CI installs pyyaml)"
  echo "\$ uv run --no-project --with pyyaml python validate_skills.py skills | grep -E '^(warning: )?skills/company-fleets/'; tail -1"
  if [ -f "$rig/validate_skills.py" ] && command -v uv >/dev/null 2>&1; then
    res=$(cd "$rig" && uv run --no-project --with pyyaml python validate_skills.py skills 2>&1); code=$?
    echo "$res" | grep -E '^(warning: )?skills/company-fleets/' || echo "(no lines for skills/company-fleets)"
    echo "skills with errors: $(echo "$res" | grep -v '^warning' | grep '^skills/' | cut -d/ -f2 | sort -u | tr '\n' ' ')"
    echo "$res" | tail -1; echo "exit=$code"
  else
    echo "validate_skills.py at the repository root or uv not found; skipped"
  fi
  echo; echo "## skill eval cases (evals/evals.json): deterministic part only"
  echo "# Each case's script_check is a unit test above. A model following SKILL.md on these prompts was not run."
  python3 - "$skill" "$out" <<'PY'
import json, re, sys
skill, out = sys.argv[1], sys.argv[2]
log = open(out).read()
for case in json.load(open(skill + "/evals/evals.json"))["evals"]:
    module_cls, name = case["script_check"].rsplit(".", 1)
    m = re.search(r"^%s \(%s\.%s\) \.\.\. (\w+)" % (re.escape(name), re.escape(module_cls), re.escape(name)), log, re.M)
    print("eval %s (%s): script check %s -> %s; model behavior: not run" % (case["id"], case["kind"], case["script_check"], m.group(1) if m else "NOT FOUND"))
PY
} > "$out" 2>&1
tail -3 "$out"
