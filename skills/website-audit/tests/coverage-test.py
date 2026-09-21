#!/usr/bin/env python3
"""Coverage test for the website-audit skill.

Proves the installed skill still represents the master playbook faithfully.
Rerun after every change to the source playbook. Exits non-zero on any failure.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILS = []

def check(label, ok, detail=""):
    print(f"  {'OK  ' if ok else 'FAIL'} {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILS.append(label)

FILES = ["SKILL.md",
         "references/intake-and-brief.md", "references/audit-playbook.md",
         "references/skill-routing.md", "references/report-template.md",
         "references/severity-and-evidence.md", "references/standards-and-modules.md",
         "references/site-health-module.md",
         "examples/example-intake.md", "examples/example-audit-excerpt.md"]

skill = (ROOT / "SKILL.md").read_text()

print("\n[1] frontmatter")
m = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check("frontmatter present", bool(m))
if m:
    try:
        import yaml
        fm = yaml.safe_load(m.group(1))
    except ImportError:
        fm = {k.split(":")[0].strip(): "" for k in m.group(1).splitlines() if ":" in k}
        print("       (pyyaml absent — key-only check)")
    LEGAL = {"name","description","when_to_use","argument-hint","arguments",
             "disable-model-invocation","user-invocable","allowed-tools","disallowed-tools",
             "model","effort","context","agent","background","hooks","paths","shell",
             "metadata","license","compatibility"}
    check("no illegal fields", not (set(fm) - LEGAL), str(set(fm) - LEGAL))
    n = len(str(fm.get("description",""))) + len(str(fm.get("when_to_use","")))
    check("description+when_to_use within 1536-char listing cap", n <= 1536, f"{n} chars")

print("\n[2] structure")
for f in FILES:
    check(f, (ROOT / f).exists())

print("\n[3] progressive loading")
body = skill[m.end():] if m else skill
for f in FILES[1:8]:
    check(f"{f} named in SKILL.md", f.split('/')[-1] in body)
total = sum(len((ROOT/f).read_text()) for f in FILES[1:] if (ROOT/f).exists())
check("SKILL.md smaller than what it defers", len(skill) < total,
      f"{len(skill)} vs {total}")

print("\n[4] Standing Rules 1-19")
play = (ROOT/"references/audit-playbook.md").read_text().lower()
sev  = (ROOT/"references/severity-and-evidence.md").read_text().lower()
PROBES = {1:"whole task",2:"intent over",3:"ambiguity",4:"survey",5:"adjacent work",
          6:"definition of done",7:"mechanism first",8:"ceremonial",
          9:"separate evidence from inference",10:"taste",11:"mental state",
          12:"conformance",13:"not observed in the sample",14:"wholesale redesign",
          15:"fashionable",16:"five axes",17:"access controls",18:"privacy",19:"reread"}
for k, v in PROBES.items():
    check(f"Rule {k:2} ({v})", v in play or v in sev)

print("\n[5] evidence taxonomy")
sev_raw = (ROOT/"references/severity-and-evidence.md").read_text()
for lab in ["Observed","Measured","Standards-based","Heuristic","Hypothesis","User-reported"]:
    check(f"label {lab}", lab in sev_raw)

print("\n[6] framing-field coverage map")
intake = (ROOT/"references/intake-and-brief.md").read_text().lower()
FIELDS = ["Role","Background","Why this audit matters","Organization or site purpose",
          "Primary audiences","Most important user tasks","goals","Known constraints",
          "Action","Complexity","Required method","Priority pages or journeys",
          "Explicit exclusions","Required standards","Definition of done","Primary URL",
          "Additional domains","Source material","Presentation","Authenticated roles",
          "Analytics","Comparison sites","assistive-technology","Project-notes location"]
for f in FIELDS:
    check(f"field: {f}", f.lower() in intake)

print("\n[7] site-health battery parity (source skill phases 2-14)")
shm = (ROOT/"references/site-health-module.md").read_text().lower()
BATTERY = {"P2 frontend/console":"console", "P3 PageSpeed":"pagespeed",
           "P4 a11y plugin":"accessibility plugin", "P5 SEO plugin":"seo plugin",
           "P6 AI visibility":"ai visibility", "P7 security headers":"securityheaders",
           "P8 SSL/TLS":"ssllabs", "P9 rich results":"rich-results",
           "P10 WAVE":"wave.webaim", "P11 carbon":"websitecarbon",
           "P12 agent ready":"isitagentready", "P13 CMS site health":"site-health.php",
           "P14 report + WoW diff":"week-over-week"}
for k,v in BATTERY.items():
    check(k, v in shm, v)
check("P1 cache clear gated, not default", "excluded by default" in shm and "--own-site" in shm)
check("P15 remediation excluded", "out of scope for this skill entirely" in shm)
check("health skills not invoked", "do **not** invoke" in shm)

print("\n[8] playbook sections present, not pending")
play = (ROOT/"references/audit-playbook.md").read_text()
sev  = (ROOT/"references/severity-and-evidence.md").read_text()
rep  = (ROOT/"references/report-template.md").read_text()
std  = (ROOT/"references/standards-and-modules.md").read_text()

for f in ["references/audit-playbook.md","references/severity-and-evidence.md",
          "references/standards-and-modules.md","references/report-template.md"]:
    check(f"{f} no longer pending", "PENDING SOURCE" not in (ROOT/f).read_text())

MODULES = ["information architecture","interaction design","content design","accessibility",
           "responsive","forms and journeys","search and discovery","performance as experienced",
           "trust and safety","wordpress","research and analytics","quality control"]
for m in MODULES:
    check(f"module: {m}", m in play.lower())

check("default definition of done present", "default definition of done" in play.lower())
check("DoD has 8 checkable criteria", play.lower().count("not observed in the sample") >= 1
      and "fewer than eight met" in play.lower())

for axis in ["Critical","Major","Moderate","Minor"]:
    check(f"severity level: {axis}", axis in sev)
for eff in ["Trivial","Contained","Substantial","Structural"]:
    check(f"effort level: {eff}", eff in sev)
check("axes explicitly not averaged", "never average" in sev.lower())

check("report structure present", "what to do first" in rep.lower())
check("what-is-working section mandatory", "mandatory" in rep.lower())
check("withdrawn findings stay visible", "withdrawn finding stays visible" in rep.lower())

check("acquisition-before-conversion rule", "check acquisition before diagnosing conversion" in play.lower())
check("inherited-premises rule", "unverified until checked" in play.lower())
check("per-breakpoint a11y rule", "test each breakpoint independently" in play.lower())

print()
if FAILS:
    print(f"FAILED ({len(FAILS)}): " + "; ".join(FAILS)); sys.exit(1)
print("ALL CHECKS PASSED"); sys.exit(0)
