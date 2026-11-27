#!/usr/bin/env python3
"""End-to-end agency demonstration: Client A's scoped brief to a verified support handoff.

SYNTHETIC FIXTURE (Fixture Co). Runs every check the brief's acceptance criteria name, binds the scope to a
factory-rig contract, gates the lifecycle stages, records a handoff.v1 through the company-fleets ledger,
then replays counterexamples on a throwaway copy. Each step states the exit code and JSON it must produce;
the run exits 0 only when every expectation holds, 3 when the browser adapter is missing.

The contract owner (agency.engagement-director) claims the instance FIX-AG-DONATE-1, which opens its one
owner ledger at fleets/agency/owner/FIX-AG-DONATE-1, records every owner value (margin policy and rate-card
pins, the human acceptor roster, stage acceptances, each handoff's open record and intake) with
`fleet owner-record`, which needs the claim token, and closes the ledger on release. Workers and the next
consumer only read those values back from that ledger; no command takes a ledger path.

An instance gets one ledger, so each run first moves the ledgers the last run left in the owner root into
that run's folder (runs/<last stamp>/owner-ledgers). That move is a same-user write to the owner root, the
kind the owner path's limit names; the demo does it as the owner, to start a fresh engagement with the same
fixture. Each counterexample claims its own instance (FIX-AG-DONATE-1-<NAME>) under its own contract copy,
and its ledger moves into this run's counterexamples folder when the counterexamples finish.

  AGENCY_A11Y_NODE_MODULES=<node_modules with playwright and axe-core> python3 fleets/agency/demo/run_demo.py [--log FILE]
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

AGENCY = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FLEETS_SKILL = os.path.normpath(os.path.join(AGENCY, "..", ".."))
SKILLS = os.path.dirname(FLEETS_SKILL)
FLEET = os.path.join(FLEETS_SKILL, "bin", "fleet")
GATE = os.path.join(SKILLS, "agency-engagement-gate", "scripts", "engagement_gate.py")
KEYS = os.path.join(SKILLS, "agency-keyboard-audit", "scripts", "keyboard_audit.py")
I18N = os.path.join(SKILLS, "agency-i18n-check", "scripts", "i18n_check.py")
FOUNDATIONS = os.path.join(SKILLS, "design-system", "scripts", "check-foundations.py")
sys.path.insert(0, os.path.join(SKILLS, "factory-rig", "scripts"))
RUN = None  # set in main(): DEMO/runs/<UTC stamp>, a fresh folder per run; DEMO/runs/LATEST names the newest
INSTANCE = "FIX-AG-DONATE-1"
OWNER_ROOT = os.path.join(AGENCY, "owner")  # company-fleets keeps each agency instance's one ledger here
DEMO = "demo/client-a-donate"
EVID = "evidence/client-a-donate"
LOCALES = ("en", "es", "ar")
STAGES = ["qualified-brief", "research-requirements", "decisions", "prototype", "implementation",
          "integrated-verification", "migration-rehearsal", "release-recommendation", "support-improvement"]


class Demo:
    def __init__(self, base, log):
        self.base, self.log, self.failures, self.blocked = base, log, [], False

    def p(self, rel):
        return os.path.join(self.base, rel)

    def where(self, cwd=None):
        cwd = cwd or self.base
        return os.path.relpath(cwd, SKILLS) if cwd.startswith(SKILLS) else "<throwaway copy>"

    def step(self, name, argv, exit_code, check=None, save=None, cwd=None, reviews=()):
        header = reviewed_lines(self, reviews)
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=cwd or self.base, timeout=300, stdin=subprocess.DEVNULL)
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            out = None
        if save:
            with open(self.p(save), "w", encoding="utf-8") as fh:
                fh.write(header + proc.stdout)
        problems = []
        if proc.returncode == 3:
            self.blocked = True
        if proc.returncode != exit_code:
            problems.append("exit %d, expected %d" % (proc.returncode, exit_code))
        if check and out is not None:
            try:
                note = check(out)
            except (KeyError, IndexError, TypeError) as exc:
                note = "check raised %r" % exc
            if note:
                problems.append(note)
        verdict = "PASS" if not problems else "FAIL: " + "; ".join(problems)
        if problems:
            self.failures.append(name)
        rel = [os.path.relpath(a, SKILLS) if os.path.isabs(a) and a.startswith(SKILLS) else a for a in argv]
        self.log.write("\n### %s\n$ (cwd %s) %s\nexit %d -> %s\n" % (name, self.where(cwd), " ".join(rel), proc.returncode, verdict))
        self.log.write(proc.stdout if len(proc.stdout) < 6000 else proc.stdout[:6000] + "\n... [truncated; full output in %s]\n" % save)
        if proc.stderr.strip():
            self.log.write("[stderr] %s\n" % proc.stderr.strip()[:800])
        return out


class Owner:
    """The contract owner: claims the instance with `fleet claim` (no ledger path: the claim opens the instance's one
    ledger under fleets/agency/owner), records owner values with `fleet owner-record`, and closes the ledger with
    `fleet release`, piping the claim token on stdin. The token stays in this process; the log never shows it."""

    def __init__(self, d, inputs, contract_sha, instance=None, workload="agency.workload.multilingual-launch"):
        self.d, self.inputs, self.n, self.instance = d, inputs, 0, instance or INSTANCE
        self.ident = ["--tenant", "tenant-a", "--workload", workload, "--instance", self.instance]
        proc = subprocess.run([FLEET, "claim"] + self.ident + ["--role", "agency.engagement-director", "--owner-pid", str(os.getpid()),
                              "--contract-hash", contract_sha], capture_output=True, text=True, cwd=d.base, stdin=subprocess.DEVNULL)
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        lease = out.get("lease", {}) if proc.returncode == 0 else {}
        self.epoch, self.token, self.ledger = lease.get("epoch"), lease.get("token", ""), out.get("ledger", "")
        d.log.write("\n### owner: claim %s#%s for agency.engagement-director (ledger %s)\nexit %d, epoch %s %s; the claim token stays in the owner process and is not logged\n"
                    % (workload, self.instance, os.path.relpath(self.ledger, SKILLS) if self.ledger else "none", proc.returncode, self.epoch,
                       "" if proc.returncode == 0 else out.get("refused", "")))
        if proc.returncode != 0:
            d.failures.append("owner claim of %s" % self.instance)

    def record(self, kind, rec, contract=None):
        self.n += 1
        rel = os.path.join(self.inputs, "%02d-%s.json" % (self.n, kind))
        write_json(self.d.p(rel), rec)
        argv = [FLEET, "owner-record"] + self.ident + ["--epoch", str(self.epoch), "--kind", kind, "--record", rel, "--base", "."]
        argv += ["--contract", contract] if contract else []
        proc = subprocess.run(argv, input=self.token + "\n", capture_output=True, text=True, cwd=self.d.base, timeout=120)
        verdict = "PASS" if proc.returncode == 0 else "FAIL"
        self.d.log.write("owner-record %-16s -> exit %d %s %s\n" % (kind, proc.returncode, verdict, " ".join(proc.stdout.split())))
        if proc.returncode != 0:
            self.d.failures.append("owner-record %s %s" % (kind, rel))

    def release(self):
        proc = subprocess.run([FLEET, "release"] + self.ident + ["--epoch", str(self.epoch), "--outcome", "done"],
                              input=self.token + "\n", capture_output=True, text=True, cwd=self.d.base)
        self.d.log.write("owner: release epoch %s, which closes the ledger -> exit %d\n" % (self.epoch, proc.returncode))
        if proc.returncode != 0:
            self.d.failures.append("owner release of %s" % self.instance)


def archive_owner_ledgers(dest, log, why, main=True):
    """Move the FIX-AG-DONATE-1-<NAME> ledgers, and with main the FIX-AG-DONATE-1 ledger too, out of the owner root
    into dest (a same-user write to the owner root; see the docstring)."""
    moved = []
    if os.path.isdir(OWNER_ROOT):
        for name in sorted(os.listdir(OWNER_ROOT)):
            if (main and name == INSTANCE) or name.startswith(INSTANCE + "-"):
                os.makedirs(dest, exist_ok=True)
                os.rename(os.path.join(OWNER_ROOT, name), os.path.join(dest, name))
                moved.append(name)
    log.write("owner-root move (%s): %s -> %s\n" % (why, ", ".join(moved) or "nothing to move", os.path.relpath(dest, SKILLS)))


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def reviewed_lines(d, paths):
    """One reviewed-sha256 line per output the check reads, hashed when the check runs, so a later edit leaves the review stale."""
    return "".join("reviewed-sha256: %s %s\n" % (sha(d.p(rel)), rel) for rel in paths)


def rules(o):
    return sorted({f["rule"] for f in o.get("findings", [])})


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def contract_for(d):
    return {"schema_version": 1, "task_id": "FIX-AG-DONATE-1", "repo": "fixture-co/tenant-a-site",
            "title": "SYNTHETIC: Client A multilingual donate page", "depends_on": [], "required_decisions": [],
            "spec": {"id": "SPEC-FIX-AG-DONATE", "revision": "1", "sha256": sha(d.p("fixtures/client-a/scoped-brief.json"))},
            "backends": ["implement-spec"], "base_branch": "main",
            "verify": {"argv": ["python3", "fleets/agency/demo/run_demo.py"]},
            "acceptance": ["Keyboard users reach and operate every control with visible focus",
                           "No placeholder, plural, untranslated or RTL layout defects",
                           "Token colors meet WCAG contrast", "The support runbook is complete"]}


STAND_IN = "SYNTHETIC FIXTURE (Fixture Co): acceptance recorded by the demo's contract owner as a stand-in for the named acceptor; not a real sign-off."


def ledger_for(d):
    """The worker's stage ledger and the owner's acceptance records for each settled stage (recorded through the owner path)."""
    ledger, acceptances = [], []

    def settle(stage, status, producer, acceptor, evidence=(), skip_reason=None):
        rec = {"label": STAND_IN, "stage": stage, "status": status, "producer": producer, "accepted_by": acceptor, "evidence": list(evidence)}
        if skip_reason:
            rec["skip_reason"] = skip_reason
        acceptances.append(rec)
        entry = {"stage": stage, "status": status, "producer": producer}
        if status == "done":
            entry["evidence"] = [{"path": p, "sha256": sha(d.p(p))} for p in evidence]
        ledger.append(entry)

    settle("qualified-brief", "done", "agency.estimator", "human:client-a-sponsor", [EVID + "/brief.json"])
    settle("research-requirements", "skipped", "agency.research-strategist", "human:delivery-owner",
           skip_reason="Human-data boundary: no donor research was run for this fixture; requirements come from the client's brief only, and no findings are claimed.")
    settle("decisions", "done", "agency.design-systems-lead", "agency.engagement-director", [DEMO + "/deliverable/tokens.css", EVID + "/foundations.txt"])
    settle("prototype", "done", "agency.ux-ui-designer", "agency.accessibility-specialist", [EVID + "/keyboard-en.txt"])
    settle("implementation", "done", "agency.web-engineer", "agency.qa-engineer", [DEMO + "/deliverable/build.py", DEMO + "/deliverable/template.html"])
    settle("integrated-verification", "done", "agency.qa-engineer", "human:delivery-owner",
           [EVID + "/keyboard-es.txt", EVID + "/keyboard-ar.txt", EVID + "/i18n.txt"])
    settle("migration-rehearsal", "skipped", "agency.migration-lead", "human:delivery-owner", skip_reason="New page with no existing content to migrate.")
    ledger += [{"stage": "release-recommendation", "status": "pending"}, {"stage": "support-improvement", "status": "pending"}]
    return ({"label": "SYNTHETIC FIXTURE (Fixture Co): stage ledger written by the worker. A settled stage counts only when the owner log holds the contract owner's acceptance for it; the demo's acceptances are stand-ins for the named acceptors, not real sign-offs.",
             "brief": "fixtures/client-a/scoped-brief.json", "stages": ledger}, acceptances)


ROSTER = {"label": "SYNTHETIC FIXTURE (Fixture Co): humans the contract owner allows to accept a stage.",
          "humans": ["human:client-a-sponsor", "human:delivery-owner"]}


def intake_for(handoff_id, extra=()):
    """The contract owner's input labels. The worker's update lists paths only."""
    return {"label": "SYNTHETIC FIXTURE (Fixture Co): input labels recorded once by the contract owner (human:delivery-owner stand-in).",
            "handoff_id": handoff_id,
            "inputs": [{"path": "fixtures/client-a/brief.md", "tenant_id": "tenant-a", "classification": "confidential",
                        "trust": "untrusted", "source_kind": "client-file"},
                       {"path": "fixtures/client-a/scoped-brief.json", "tenant_id": "tenant-a", "classification": "confidential",
                        "trust": "trusted", "source_kind": "rig-record"}] + list(extra)}


OWNER = {"handoff_id": "HO-FIX-AG-DONATE-SUPPORT", "workload_id": "agency.workload.multilingual-launch",
         "tenant_id": "tenant-a", "client_id": "client-a", "operating_profile": "agency",
         "outcome": "Client A's verified donate page and support package, ready for the support handoff owner.",
         "scope": ["Donate page template, build script and three locale pages", "Design tokens and styles", "Support runbook"],
         "exclusions": ["Payment processing", "Hosting operations", "Linguistic review (human:language-reviewer)"],
         "acceptance_criteria": ["Every output has fresh evidence under the current contract", "Linguistic review stays an open human decision"],
         "sources": [{"ref": "fixtures/client-a/scoped-brief.json", "revision": "FIX-AG-DONATE-1 r1"}],
         "producer": "agency.release-engineer", "reviewer": "agency.qa-engineer", "acceptance_owner": "human:delivery-owner",
         "execution_owner": "agency.engagement-director",
         "data": {"classification": "confidential", "allowed_destinations": ["tenant:tenant-a", "rig:evidence"]},
         "authority": {"tools": ["agency-engagement-gate", "agency-keyboard-audit", "agency-i18n-check"], "mutation": "staged",
                       "external_actions": "none", "publication": "staged-only"},
         "budget": {"max_minutes": 90, "max_retries": 1},
         "stop_conditions": ["Every output checked", "Budget reached"],
         "cancellation": "Stop, keep the checks run so far labeled partial, release the workload lease.",
         "next_consumer": "agency.support-handoff-owner",
         "readiness_criteria": ["Every output has fresh evidence under the current contract", "The runbook check passes"]}


def update_for(extra=None):
    outputs = [{"path": DEMO + "/deliverable/donate.%s.html" % l, "artifact_type": "page (%s)" % l} for l in LOCALES]
    outputs += [{"path": DEMO + "/deliverable/tokens.css", "artifact_type": "design tokens"},
                {"path": DEMO + "/deliverable/styles.css", "artifact_type": "stylesheet"},
                {"path": DEMO + "/deliverable/locales/ar.po", "artifact_type": "catalog (ar)"},
                {"path": DEMO + "/deliverable/locales/es.po", "artifact_type": "catalog (es)"},
                {"path": DEMO + "/support/runbook.md", "artifact_type": "support runbook"}]
    evidence = [{"path": EVID + "/keyboard-%s.txt" % l, "about": DEMO + "/deliverable/donate.%s.html" % l} for l in LOCALES]
    evidence += [{"path": EVID + "/foundations.txt", "about": DEMO + "/deliverable/tokens.css"},
                 {"path": EVID + "/i18n.txt", "about": DEMO + "/deliverable/styles.css"},
                 {"path": EVID + "/i18n.txt", "about": DEMO + "/deliverable/locales/ar.po"},
                 {"path": EVID + "/i18n.txt", "about": DEMO + "/deliverable/locales/es.po"},
                 {"path": EVID + "/runbook.txt", "about": DEMO + "/support/runbook.md"}]
    u = {"label": "SYNTHETIC FIXTURE (Fixture Co): the release engineer's worker update, paths only; the gate computes hashes.",
         "summary": "Three locale pages built from one template; keyboard, contrast, i18n and runbook checks pass. Linguistic review is still open.",
         "assumptions": ["Static hosting serves the release folder as is", "Amounts stay in US dollars until the language reviewer decides"],
         "unresolved_decisions": ["Linguistic review of es and ar by human:language-reviewer has not happened; release stays pending until it does"],
         "inputs": [{"path": "fixtures/client-a/brief.md"}, {"path": "fixtures/client-a/scoped-brief.json"}],
         "outputs": outputs, "evidence": evidence}
    u.update(extra or {})
    return u


def handoff_argv(py, handoff_id, update, contract=DEMO + "/handoff/contract.json"):
    return [py, GATE, "handoff", "--handoff-id", handoff_id, "--contract", contract, "--base", ".", "--update", update]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.join(AGENCY, "evidence", "demo-client-a-donate.txt"))
    args = ap.parse_args()
    modules = os.environ.get("AGENCY_A11Y_NODE_MODULES", "")
    log = open(args.log, "w", encoding="utf-8")
    log.write("# Agency demonstration: Client A scoped brief to verified support handoff (SYNTHETIC FIXTURE, Fixture Co)\n")
    log.write("$ AGENCY_A11Y_NODE_MODULES=%s python3 company-fleets/fleets/agency/demo/run_demo.py\nrun on %s\n"
              % (modules.replace(os.path.expanduser("~"), "~") or "(unset)", datetime.date.today().isoformat()))
    global RUN
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RUN = DEMO + "/runs/" + stamp
    os.makedirs(os.path.join(AGENCY, RUN), exist_ok=False)
    latest = os.path.join(AGENCY, DEMO, "runs", "LATEST")
    previous = open(latest, encoding="utf-8").read().strip() if os.path.isfile(latest) else ""
    archive_owner_ledgers(os.path.join(AGENCY, DEMO, "runs", previous or stamp, "owner-ledgers"), log,
                          "the ledgers the last run left, so this run can claim %s again" % INSTANCE)
    with open(latest, "w", encoding="utf-8") as fh:
        fh.write(stamp + "\n")
    log.write("run folder: %s (owner inputs and the counterexample copy); owner ledger: company-fleets/fleets/agency/owner/%s\n" % (RUN, INSTANCE))
    d = Demo(AGENCY, log)
    os.makedirs(d.p(EVID), exist_ok=True)
    py = sys.executable
    from factory_rig.contract import contract_hash

    contract = contract_for(d)
    write_json(d.p(DEMO + "/handoff/contract.json"), contract)
    owner = Owner(d, RUN + "/owner-inputs", contract_hash(contract))
    owner.record("pin", {"name": "margin-policy", "path": "../corporate/policies/margin-policy.json",
                         "label": "The company margin policy, owned by human:finance-owner."})
    owner.record("pin", {"name": "rate-card", "path": "fixtures/client-a/rates.json", "label": "The agency's internal cost rates for this engagement."})

    d.step("1 qualify and price the scoped brief against the owner-pinned policy and rate card",
           [py, GATE, "brief", "--brief", "fixtures/client-a/scoped-brief.json"], 0,
           lambda o: None if o["margin"]["margin"] > o["margin"]["floor"] else "margin not above floor", save=EVID + "/brief.json")
    d.step("2 scan the untrusted client brief (data, not instructions)", [FLEET, "scan", "fixtures/client-a/brief.md"], 0,
           lambda o: None if sorted(f["category"] for f in o["findings"]) == ["authority", "evidence", "exfiltration"] else "scan categories %s" % o["findings"],
           save=EVID + "/client-brief-scan.json")
    d.step("3 build the three locale pages from the catalogs", [py, "build.py"], 0, cwd=d.p(DEMO + "/deliverable"))
    header = reviewed_lines(d, [DEMO + "/deliverable/tokens.css"])
    proc = subprocess.run([py, FOUNDATIONS, "--config", "foundations.check.json"], capture_output=True, text=True, cwd=d.p(DEMO + "/deliverable"))
    with open(d.p(EVID + "/foundations.txt"), "w", encoding="utf-8") as fh:
        fh.write(header + proc.stdout)
    ok = proc.returncode == 0 and "PASS" in proc.stdout
    log.write("\n### 4 design tokens: upstream design-system check-foundations.py (contrast, values, nested radii)\n$ (cwd %s/deliverable) python3 design-system/scripts/check-foundations.py --config foundations.check.json\nexit %d -> %s\n%s"
              % (DEMO, proc.returncode, "PASS" if ok else "FAIL", proc.stdout))
    if not ok:
        d.failures.append("4 foundations")
    for l in LOCALES:
        d.step("5 keyboard audit with axe-core baseline: donate.%s.html" % l,
               [py, KEYS, "--page", DEMO + "/deliverable/donate.%s.html" % l, "--node-modules", modules], 0,
               lambda o: None if o["reached_end"] and o["tab_stops"] >= 7 else "walk incomplete", save=EVID + "/keyboard-%s.txt" % l, reviews=[DEMO + "/deliverable/donate.%s.html" % l])
    d.step("6 i18n check: es and ar catalogs, RTL template and CSS", [py, I18N, "--pot", DEMO + "/deliverable/locales/donate.pot",
           "--po", DEMO + "/deliverable/locales/es.po", "--po", DEMO + "/deliverable/locales/ar.po",
           "--template", DEMO + "/deliverable/template.html", "--css", DEMO + "/deliverable/styles.css"], 0,
           lambda o: None if o["linguistic_review"]["status"] == "required" else "linguistic review not kept human", save=EVID + "/i18n.txt",
           reviews=[DEMO + "/deliverable/styles.css", DEMO + "/deliverable/locales/ar.po", DEMO + "/deliverable/locales/es.po"])
    d.step("7 support runbook completeness", [py, GATE, "support", "--runbook", DEMO + "/support/runbook.md"], 0, save=EVID + "/runbook.txt", reviews=[DEMO + "/support/runbook.md"])

    stage_ledger, acceptances = ledger_for(d)
    write_json(d.p(DEMO + "/handoff/ledger.json"), stage_ledger)
    owner.record("roster", ROSTER)
    for rec in acceptances:
        owner.record("stage-acceptance", rec, contract=DEMO + "/handoff/contract.json")
    d.step("8 lifecycle stages bound to the factory-rig contract, acceptances read from the owner log", [py, GATE, "stages", "--ledger", DEMO + "/handoff/ledger.json",
           "--contract", DEMO + "/handoff/contract.json", "--base", "."], 0,
           lambda o: None if o["current_stage"] == "release-recommendation" and "stand-in" in o["label"] else "current stage %s" % o["current_stage"],
           save=EVID + "/stages.json")

    write_json(d.p(DEMO + "/handoff/owner.json"), OWNER)
    write_json(d.p(DEMO + "/handoff/intake.json"), intake_for(OWNER["handoff_id"]))
    write_json(d.p(DEMO + "/handoff/update.json"), update_for())
    owner.record("open", OWNER)
    owner.record("intake", intake_for(OWNER["handoff_id"]))
    built = d.step("9 worker records the support handoff; owner fields and input labels come from the owner log",
                   handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update.json"), 0,
                   lambda o: None if o["status"] in ("recorded", "duplicate") and len(o["untrusted_findings"]) == 3 and not o["refused_fields"] else "status %s" % o["status"],
                   save=EVID + "/handoff-build.json")
    if built and "submitted" in built.get("paths", {}):
        sub = os.path.relpath(built["paths"]["submitted"], AGENCY) if os.path.isabs(built["paths"]["submitted"]) else built["paths"]["submitted"]
        d.step("10 next consumer's gate: fleet handoff-check against the contract's owner ledger", [FLEET, "handoff-check", "--handoff", sub,
               "--contract", DEMO + "/handoff/contract.json", "--base", "."], 0, save=EVID + "/handoff-check.json")

    # The same instance's ledger holds only its own workload, so the hosting chain input stays in multilingual-launch
    # under the managed profile; agency.workload.launch-with-hosting gets its own instance when it runs.
    hosting = dict(OWNER, handoff_id="HO-FIX-AG-DONATE-HOSTING", operating_profile="managed", producer="agency.support-handoff-owner", reviewer="agency.release-engineer",
                   acceptance_owner="human:hosting-intake-owner", next_consumer="human:hosting-intake-owner",
                   outcome="Client A's verified release folder and runbook, ready for hosting intake when Fixture Co also hosts the site.",
                   readiness_criteria=["Every output has fresh evidence under the current contract",
                                       "The integrator names the hosting fleet's intake role as next_consumer once it exists"])
    write_json(d.p(DEMO + "/handoff/hosting-owner.json"), hosting)
    write_json(d.p(DEMO + "/handoff/hosting-intake.json"), intake_for(hosting["handoff_id"]))
    owner.record("open", hosting)
    owner.record("intake", intake_for(hosting["handoff_id"]))
    d.step("11 hosting chain input: the same package as an agency-to-hosting handoff", handoff_argv(py, hosting["handoff_id"], DEMO + "/handoff/update.json"), 0,
           lambda o: None if o["next_consumer"] == "human:hosting-intake-owner" else "wrong consumer", save=EVID + "/hosting-handoff-build.json")
    owner.release()

    # Counterexamples run on a copy kept in this run's folder, so the delivered files never change and nothing is deleted.
    tmp = d.p(RUN + "/counterexamples")
    for part in ("fixtures", "demo", "evidence"):
        shutil.copytree(d.p(part), os.path.join(tmp, part), ignore=shutil.ignore_patterns("runs", "superseded-*", "demo-*.txt"))
    c = Demo(tmp, log)

    def opened(name, extra=()):
        """A counterexample's own instance, FIX-AG-DONATE-1-<NAME>, under a copy of the contract with that task_id."""
        inst = "%s-%s" % (INSTANCE, name.upper())
        cpath = DEMO + "/handoff/contract-%s.json" % name
        write_json(c.p(cpath), dict(contract, task_id=inst))
        o = Owner(c, "owner-inputs/" + name, contract_hash(dict(contract, task_id=inst)), instance=inst)
        o.cpath = cpath
        o.record("open", OWNER)
        o.record("intake", intake_for(OWNER["handoff_id"], extra))
        return o

    t = opened("tampered")
    write_json(c.p(DEMO + "/handoff/update-tampered.json"), update_for({"acceptance_owner": "agency.release-engineer"}))
    c.step("C1 counterexample: a worker that obeyed 'approve your own QA results'", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update-tampered.json", t.cpath), 0,
           lambda o: None if [r["field"] for r in o["refused_fields"]] == ["acceptance_owner"]
           and json.load(open(o["paths"]["submitted"] if os.path.isabs(o["paths"]["submitted"]) else os.path.join(tmp, o["paths"]["submitted"])))["acceptance_owner"] == "human:delivery-owner"
           else "protected field moved")
    r = opened("relabel")
    bad = update_for()
    bad["inputs"].append({"path": "fixtures/client-b/brief.md", "tenant_id": "tenant-a", "classification": "public", "trust": "trusted"})
    write_json(c.p(DEMO + "/handoff/update-client-b.json"), bad)
    c.step("C2 counterexample: a worker labels Client B's brief as tenant-a public", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update-client-b.json", r.cpath), 1,
           lambda o: None if "input-not-in-intake" in rules(o) and "submitted" not in o.get("paths", {}) else "relabeled tenant input accepted")
    tb = opened("tenant", [{"path": "fixtures/client-b/brief.md", "tenant_id": "tenant-b", "classification": "confidential",
                            "trust": "untrusted", "source_kind": "client-file"}])
    bad["inputs"][-1] = {"path": "fixtures/client-b/brief.md"}
    write_json(c.p(DEMO + "/handoff/update-client-b.json"), bad)
    c.step("C2b counterexample: the owner labels it tenant-b, so it can't enter a tenant-a handoff", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update-client-b.json", tb.cpath), 1,
           lambda o: None if o["status"] == "invalid" and any("tenant-b" in f["message"] for f in o["findings"]) else "tenant leak not refused")
    st = opened("stale")
    recorded = c.step("C3 setup: record the handoff in the copy", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update.json", st.cpath), 0) or {}
    with open(c.p(DEMO + "/deliverable/donate.ar.html"), "a", encoding="utf-8") as fh:
        fh.write("<!-- edited after the handoff -->\n")
    c.step("C3 counterexample: a page edited after the handoff recorded it", [FLEET, "handoff-check", "--handoff", recorded.get("paths", {}).get("submitted", "missing.json"),
           "--contract", st.cpath, "--base", "."], 1,
           lambda o: None if any("changed after the handoff recorded it" in e for e in o["errors"]) else "stale output accepted")

    forged = opened("forged")
    write_json(c.p("worker-intake.json"), intake_for(OWNER["handoff_id"], [{"path": "fixtures/client-b/brief.md", "tenant_id": "tenant-a",
               "classification": "confidential", "trust": "untrusted", "source_kind": "client-file"}]))
    c.step("C6 counterexample: a worker runs the owner command with the owner's epoch but no claim token", [FLEET, "owner-record"]
           + forged.ident + ["--epoch", str(forged.epoch), "--kind", "roster", "--record", "worker-intake.json"], 1,
           lambda o: None if o.get("refused") == "not-the-lease-holder" else "owner path accepted a caller without the token")
    log_path = os.path.join(forged.ledger, "owner-log.ndjson")
    with open(log_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    entry = json.loads(lines[-1])
    entry["body"]["inputs"][0]["classification"] = "public"
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines[:-1] + [json.dumps(entry, sort_keys=True, separators=(",", ":"))]) + "\n")
    c.step("C6b counterexample: a worker edits the owner's intake entry in the owner log", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update.json", forged.cpath), 1,
           lambda o: None if rules(o) == ["owner-log-broken"] else "edited owner log accepted")
    sl = opened("symlink")
    os.rename(c.p("fixtures/client-a/brief.md"), c.p("fixtures/client-a/brief.md.orig"))
    os.symlink("../client-b/brief.md", c.p("fixtures/client-a/brief.md"))
    c.step("C7 counterexample: Client A's input becomes a symlink to Client B's brief after the intake", handoff_argv(py, OWNER["handoff_id"], DEMO + "/handoff/update.json", sl.cpath), 1,
           lambda o: None if "input-symlink-leaves-folder" in rules(o) and "submitted" not in o.get("paths", {}) else "symlinked tenant input accepted")
    os.remove(c.p("fixtures/client-a/brief.md"))
    os.rename(c.p("fixtures/client-a/brief.md.orig"), c.p("fixtures/client-a/brief.md"))
    relabeled = json.load(open(c.p(DEMO + "/handoff/ledger.json")))
    impl = next(s for s in relabeled["stages"] if s["stage"] == "implementation")
    impl.update(producer="agency.qa-engineer", status="skipped")
    write_json(c.p(DEMO + "/handoff/ledger-relabeled.json"), relabeled)
    write_json(c.p(DEMO + "/handoff/acceptances/implementation.json"), {"stage": "implementation", "producer": "agency.qa-engineer", "accepted_by": "human:x",
                                                                         "skip_reason": "not needed"})
    c.step("C8 counterexample: the producer relabels its stage, marks it skipped and writes its own acceptance file", [py, GATE, "stages",
           "--ledger", DEMO + "/handoff/ledger-relabeled.json", "--contract", DEMO + "/handoff/contract.json", "--base", "."], 1,
           lambda o: None if "acceptance-mismatch" in rules(o) else "relabeled stage accepted")

    with open(c.p("fixtures/client-a/scoped-brief.json"), "a", encoding="utf-8") as fh:
        fh.write("\n")
    c.step("C4 counterexample: scope edited without reissuing the PM contract", [py, GATE, "stages", "--ledger", DEMO + "/handoff/ledger.json",
           "--contract", DEMO + "/handoff/contract.json", "--base", "."], 1,
           lambda o: None if "scope-changed" in rules(o) else "scope change not caught")
    cpath = c.p(DEMO + "/handoff/contract.json")
    rewritten = json.load(open(cpath))
    rewritten["spec"]["sha256"] = sha(c.p("fixtures/client-a/scoped-brief.json"))
    write_json(cpath, rewritten)
    c.step("C5 counterexample: the contract's spec hash rewritten to match, revision unchanged", [py, GATE, "stages", "--ledger", DEMO + "/handoff/ledger.json",
           "--contract", DEMO + "/handoff/contract.json", "--base", "."], 1,
           lambda o: None if rules(o) == ["ledger-not-for-this-work"] else "rewritten spec accepted")
    archive_owner_ledgers(os.path.join(tmp, "owner-ledgers"), log, "the counterexamples' own instances, kept with this run", main=False)
    d.failures += c.failures
    d.blocked = d.blocked or c.blocked

    status = "BLOCKED (browser adapter missing)" if d.blocked else ("PASS" if not d.failures else "FAIL: " + ", ".join(d.failures))
    log.write("\n## Result: %s\n" % status)
    log.close()
    print(json.dumps({"ok": not d.failures, "blocked": d.blocked, "failures": d.failures, "log": os.path.relpath(args.log, FLEETS_SKILL)}, indent=2))
    return 3 if d.blocked else (0 if not d.failures else 1)


if __name__ == "__main__":
    sys.exit(main())
