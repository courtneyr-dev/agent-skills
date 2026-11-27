#!/usr/bin/env python3
"""incident: SLO and burn-rate checks, and a tamper-evident incident record, for the hosting fleet.

  slo-check --slo SLO.json --events EVENTS.jsonl --now ISO [--routing ROUTING.json] [--claim-availability]
  incident open|update|mitigate|monitor|resolve|review|comms|approve|show --record FILE ...

Every incident command checks the record's head against the owner's anchors ledger, kept at one fixed
path in the fleet's owner folder (company-fleets/fleets/hosting/owner/hosting-incident-response/
anchors.ndjson), and appends the new head there, so a record rewritten and rehashed on its own fails.
An --anchors path or a record inside the owner folder is refused by name. open pins the owner's SLO file
(fixtures/incident-response/slo.json); an --slo naming any other file is refused. resolve derives
recovery itself from the monitoring events under that SLO, over the window before --at and every
event after it. An external update is approved only by `approve`, from an approver listed in the owner
file comms-approvers.json.

Python 3.9+, standard library only. Stdout is JSON. Exit 0 ok, 1 refused or the check found a
violation, 2 invalid input. The script needs no external capability, so it never exits 3. Hashing and atomic writes come from
skills/factory-rig; the untrusted-text scan comes from skills/company-fleets. The script never sends
anything: external communications stay drafts or approved text for a human to publish.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import re
import sys
from decimal import ROUND_CEILING, Decimal
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
LEARNING_TEMPLATES = "skills/incident-learning/templates"
OWNER_FILES = os.path.join(SKILLS_ROOT, "company-fleets", "fleets", "hosting", "fixtures", "incident-response")
COMMS_APPROVERS = os.path.join(OWNER_FILES, "comms-approvers.json")
OWNER_SLO = os.path.join(OWNER_FILES, "slo.json")
OWNER_ROOT = os.path.join(SKILLS_ROOT, "company-fleets", "fleets", "hosting", "owner", "hosting-incident-response")
ANCHORS = os.path.join(OWNER_ROOT, "anchors.ndjson")
FUTURE_SKEW_S = 300
BACKDATE_FLAG_S = 3600
RECOVERY_WINDOW_S = 300

for _name, _path, _marker in (
        ("factory-rig", os.path.join(SKILLS_ROOT, "factory-rig", "scripts"), "factory_rig"),
        ("company-fleets", os.path.join(SKILLS_ROOT, "company-fleets", "scripts"), "fleetlib")):
    if not os.path.isdir(os.path.join(_path, _marker)):
        raise ImportError("hosting-incident-response needs skills/%s beside it (looked in %s)" % (_name, _path))
    if _path not in sys.path:
        sys.path.insert(0, _path)

from factory_rig.canon import atomic_write, canonical, sha, sha_file  # noqa: E402
from fleetlib.untrusted import scan  # noqa: E402

GENESIS = "0" * 64
UTC = datetime.timezone.utc
PRINCIPAL = re.compile(r"^(?:human:[a-z0-9]+(?:-[a-z0-9]+)*|[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+(?:-[a-z0-9]+)*)$")
HUMAN = re.compile(r"^human:[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMANDER_ROLE = "hosting.incident-commander"
SEVERITIES = ("sev1", "sev2", "sev3", "sev4")

# Google SRE Workbook, "Alerting on SLOs": (severity, long window, short window, burn-rate threshold).
ALERT_RULES = (
    ("page", "1h", 3600, "5m", 300, Decimal("14.4")),
    ("page", "6h", 21600, "30m", 1800, Decimal("6")),
    ("ticket", "3d", 259200, "6h", 21600, Decimal("1")),
)

# command -> {state it may run from: state it moves to}. One table owns every transition.
TRANSITIONS = {
    "update": {"declared": "investigating", "investigating": "investigating",
               "mitigating": "mitigating", "monitoring": "monitoring"},
    "mitigate": {"investigating": "mitigating", "mitigating": "mitigating", "monitoring": "mitigating"},
    "monitor": {"mitigating": "monitoring"},
    "resolve": {"monitoring": "resolved"},
    "review": {"resolved": "reviewed"},
}


class InputError(Exception):
    """Invalid input: exit 2."""


class Refused(Exception):
    """A refusal: exit 1. payload names the reason."""

    def __init__(self, refusal: str, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.payload = dict(extra, refusal=refusal, detail=detail, verdict="refused")


def emit(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


# ---- parsing ---------------------------------------------------------------------------------------------


def parse_ts(value: Any, what: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise InputError("%s must be an ISO 8601 string" % what)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.datetime.fromisoformat(text)
    except ValueError:
        raise InputError("%s is not an ISO 8601 timestamp: %r" % (what, value))
    if stamp.tzinfo is None:
        raise InputError("%s needs a timezone offset or Z: %r" % (what, value))
    return stamp.astimezone(UTC)


def iso(stamp: datetime.datetime) -> str:
    return stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_number(value: Any) -> bool:
    return isinstance(value, (int, Decimal)) and not isinstance(value, bool)


def load_json(path: str, what: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh, parse_float=Decimal)
    except FileNotFoundError:
        raise InputError("%s not found: %s" % (what, path))
    except (ValueError, OSError) as exc:
        raise InputError("%s is not readable JSON: %s (%s)" % (what, path, exc))


def load_slo(path: str) -> Dict[str, Any]:
    doc = load_json(path, "SLO file")
    if not isinstance(doc, dict):
        raise InputError("SLO file must be a JSON object")
    if not isinstance(doc.get("name"), str) or not doc["name"].strip():
        raise InputError("SLO needs a name")
    sli = doc.get("sli")
    if not isinstance(sli, dict) or sli.get("kind") not in ("availability", "latency"):
        raise InputError("unknown SLI: sli.kind must be availability or latency")
    good = sli.get("good_when")
    if not isinstance(good, dict) or not good:
        raise InputError("sli.good_when must name at least one condition")
    unknown = sorted(set(good) - {"status_lt", "latency_ms_le"})
    if unknown:
        raise InputError("unknown good_when condition(s): %s" % ", ".join(unknown))
    needed = "status_lt" if sli["kind"] == "availability" else "latency_ms_le"
    if needed not in good:
        raise InputError("a %s SLI needs good_when.%s" % (sli["kind"], needed))
    for key, value in good.items():
        if not is_number(value) or value <= 0:
            raise InputError("good_when.%s must be a positive number" % key)
    target = doc.get("target")
    if not is_number(target) or not (0 < target < 1):
        raise InputError("target must be a number above 0 and below 1, got %r" % (target,))
    window = doc.get("window_days")
    if window is None:
        raise InputError("SLO needs window_days")
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        raise InputError("window_days must be a positive integer")
    return {"name": doc["name"], "kind": sli["kind"], "good_when": good, "target": Decimal(target),
            "window_days": window}


def load_routing(path: str) -> Dict[str, str]:
    doc = load_json(path, "routing file")
    routes = doc.get("routes") if isinstance(doc, dict) else None
    if not isinstance(routes, dict):
        raise InputError("routing file needs a routes object")
    for severity in ("page", "ticket"):
        receiver = routes.get(severity)
        if not isinstance(receiver, str) or not PRINCIPAL.match(receiver):
            raise InputError("routes.%s must be a role id or human: principal" % severity)
    return routes


def load_events(path: str, slo: Dict[str, Any]) -> List[Tuple[datetime.datetime, bool, int]]:
    """Return (timestamp, good, count) per event line. An optional first line holding only a label is skipped."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except UnicodeDecodeError:
        raise InputError("events file is not UTF-8 text: %s" % path)
    except OSError as exc:
        raise InputError("events file not readable: %s (%s)" % (path, exc))
    good_when = slo["good_when"]
    events = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line, parse_float=Decimal)
        except ValueError:
            raise InputError("events line %d is not JSON" % number)
        if not isinstance(obj, dict):
            raise InputError("events line %d is not an object" % number)
        if set(obj) == {"label"}:
            continue
        stamp = parse_ts(obj.get("ts"), "events line %d ts" % number)
        count = obj.get("count", 1)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise InputError("events line %d: count must be a positive integer" % number)
        ok = True
        for key, field, cmp in (("status_lt", "status", lambda v, lim: v < lim),
                                ("latency_ms_le", "latency_ms", lambda v, lim: v <= lim)):
            if key in good_when:
                if not is_number(obj.get(field)):
                    raise InputError("events line %d: %s must be a number" % (number, field))
                ok = ok and cmp(obj[field], good_when[key])
        events.append((stamp, ok, count))
    return events


# ---- slo-check -------------------------------------------------------------------------------------------


def tally(events: List[Tuple[datetime.datetime, bool, int]], start: datetime.datetime,
          end: datetime.datetime) -> Tuple[int, int]:
    total = bad = 0
    for stamp, ok, count in events:
        if start <= stamp <= end:
            total += count
            bad += 0 if ok else count
    return total, bad


def num(value: Optional[Decimal], places: int = 6) -> Optional[float]:
    return None if value is None else round(float(value), places)


def hour_coverage(events: List[Tuple[datetime.datetime, bool, int]], now: datetime.datetime,
                  window_s: int) -> Tuple[int, int]:
    """Hours of the window [now - window, now] that hold at least one event. Events outside the window don't count."""
    start, hours = now - datetime.timedelta(seconds=window_s), window_s // 3600
    seen = {min(int((stamp - start).total_seconds() // 3600), hours - 1)
            for stamp, _, _ in events if start <= stamp <= now}
    return len(seen), hours


def evaluate_alerts(events: List[Tuple[datetime.datetime, bool, int]], now: datetime.datetime,
                    budget_fraction: Decimal, routes: Optional[Dict[str, str]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    first = min((e[0] for e in events if e[0] <= now), default=None)
    covered_s = int((now - first).total_seconds()) if first else 0
    rates, rules, alerts = {}, [], []
    for severity, long_name, long_s, short_name, short_s, threshold in ALERT_RULES:
        for name, seconds in ((long_name, long_s), (short_name, short_s)):
            if name not in rates:
                t, b = tally(events, now - datetime.timedelta(seconds=seconds), now)
                rates[name] = (Decimal(b) / Decimal(t) / budget_fraction) if t else None
        covered = bool(first) and covered_s >= long_s
        long_rate, short_rate = rates[long_name], rates[short_name]
        firing = covered and long_rate is not None and short_rate is not None \
            and long_rate > threshold and short_rate > threshold
        rule = {"severity": severity, "long_window": long_name, "short_window": short_name,
                "threshold": num(threshold), "long_rate": num(long_rate), "short_rate": num(short_rate),
                "long_window_covered": covered, "firing": firing,
                "receiver": routes[severity] if (routes and firing) else None}
        rules.append(rule)
        if firing:
            alerts.append(rule)
    return rates, rules, alerts


def slo_check(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    slo = load_slo(args.slo)
    now = parse_ts(args.now, "--now")
    events = load_events(args.events, slo)
    routes = load_routing(args.routing) if args.routing else None
    in_past = [e for e in events if e[0] <= now]
    first = min((e[0] for e in in_past), default=None)
    covered_s = int((now - first).total_seconds()) if first else 0
    window_s = slo["window_days"] * 86400
    budget_fraction = 1 - slo["target"]
    assumptions = [
        "Alert thresholds and windows are the Google SRE Workbook 'Alerting on SLOs' starting values (page at 14.4x over 1h and 5m, page at 6x over 6h and 30m, ticket at 1x over 3d and 6h); tune them per service.",
        "A window holds events with now-window <= ts <= now. A burn rate is (bad/total) / (1 - target) over that window.",
        "An alert needs both windows above the threshold and the long window covered by events; an uncovered long window is reported, not evaluated.",
        "The error budget is event-based: (1 - target) x events in the SLO window. A budget at 0 remaining counts as a violation (freeze point).",
        "Event counts come from the log as given; the script does not check the log for double delivery.",
        "An availability claim needs at least one event in every hour of the SLO window, and at least 1 / (1 - target) events in it, so one bad event can't move the SLI by more than the error budget; events outside the window don't count.",
    ]
    if routes is None:
        assumptions.append("No routing file: alerts carry receiver null and reach nobody.")
    out: Dict[str, Any] = {"command": "slo-check", "slo": slo["name"], "target": num(slo["target"]),
                           "now": iso(now), "window_days": slo["window_days"], "assumptions": assumptions}
    covered_h, window_h = hour_coverage(events, now, window_s)
    window_covered = covered_h == window_h
    out["coverage"] = {"covered_seconds": covered_s, "window_seconds": window_s, "covered_hours": covered_h,
                       "window_hours": window_h, "covers_window": window_covered}
    if args.claim_availability and not window_covered:
        out.update(verdict="refused", refusal="insufficient-window",
                   detail="events fall in %d of the %d hours of the %d-day window; a percentage needs data in every hour "
                          "of the window, so a short run cannot establish one" % (covered_h, window_h, slo["window_days"]))
        return 1, out
    total, bad = tally(events, now - datetime.timedelta(seconds=window_s), now)
    if args.claim_availability and not total:
        out.update(verdict="refused", refusal="insufficient-window",
                   detail="no events fall inside the SLO window, so there is no availability to claim")
        return 1, out
    needed = int((1 / budget_fraction).to_integral_value(rounding=ROUND_CEILING))
    if args.claim_availability and total < needed:
        out.update(verdict="refused", refusal="insufficient-events", events=total, events_needed=needed,
                   detail="%d events in the window; one bad event among fewer than %d moves the SLI by more than the whole "
                          "error budget of a %s target, so the window can't resolve that target" % (total, needed, num(slo["target"])))
        return 1, out
    observed = (Decimal(total - bad) / Decimal(total)) if total else None
    out["sli"] = {"observed": num(observed), "good": total - bad, "total": total, "bad": bad}
    out["availability_claim"] = None
    if args.claim_availability:
        out["availability_claim"] = {"percent": "%s" % (observed * 100).quantize(Decimal("0.0001")), "window_days": slo["window_days"]}
    allowed = budget_fraction * total
    if total:
        remaining_fraction = 1 - Decimal(bad) / allowed
        state = "ok" if remaining_fraction > 0 else ("exhausted" if remaining_fraction == 0 else "overspent")
        out["budget"] = {"allowed_bad": num(allowed), "consumed_bad": bad, "remaining_bad": num(allowed - bad),
                         "remaining_fraction": num(remaining_fraction), "state": state}
    else:
        state = "no-data"
        out["budget"] = {"state": state}
    rates, rules, alerts = evaluate_alerts(events, now, budget_fraction, routes)
    out["burn_rates"] = {name: num(rate) for name, rate in rates.items()}
    out["alert_rules"] = rules
    out["alerts"] = alerts
    violation = bool(alerts) or state in ("exhausted", "overspent")
    out["verdict"] = "violation" if violation else ("no-data" if state == "no-data" else "ok")
    return (1 if violation else 0), out


# ---- incident record -------------------------------------------------------------------------------------


REQUIRED_FIELDS = {"open": ("incident_id", "title", "severity", "commander", "comms_coordinator"),
                   "resolve": ("recovery_evidence",), "comms": ("audience", "status"),
                   "approve": ("approves_seq", "text_sha256")}


class Tampered(Exception):
    def __init__(self, line: int, detail: str) -> None:
        super().__init__(detail)
        self.line, self.detail = line, detail


def verify_chain(text: str) -> List[Dict[str, Any]]:
    """Parse and verify every line: JSON, sequence, prev_sha256 link and the sha256 over the canonical line."""
    if not text:
        return []
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    events, prev = [], GENESIS
    for n, line in enumerate(lines, 1):
        try:
            ev = json.loads(line)
        except ValueError:
            raise Tampered(n, "line is not JSON")
        if not isinstance(ev, dict) or not all(k in ev for k in ("seq", "ts", "command", "to", "prev_sha256", "sha256")):
            raise Tampered(n, "line is missing chain fields")
        if ev["seq"] != n - 1:
            raise Tampered(n, "sequence number %r, expected %d" % (ev["seq"], n - 1))
        if ev["prev_sha256"] != prev:
            raise Tampered(n, "prev_sha256 does not match the line before")
        body = {k: v for k, v in ev.items() if k != "sha256"}
        if sha(body) != ev["sha256"]:
            raise Tampered(n, "sha256 does not match the line's content (line was edited)")
        if n == 1 and ev["command"] != "open":
            raise Tampered(n, "first line is not an open event")
        for field in REQUIRED_FIELDS.get(ev["command"], ()):
            if field not in ev:
                raise Tampered(n, "%s line has no %s" % (ev["command"], field))
        events.append(ev)
        prev = ev["sha256"]
    return events


def tamper_refusal(exc: Tampered) -> Refused:
    return Refused("tampered-record", "line %d: %s" % (exc.line, exc.detail), line=exc.line)


def read_record(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        raise InputError("record is not UTF-8 text: %s" % path)
    except OSError:
        raise InputError("record not found: %s" % path)
    try:
        events = verify_chain(text)
    except Tampered as exc:
        raise tamper_refusal(exc)
    if not events:
        raise InputError("record is empty: %s" % path)
    return events


def owner_ledger(args: argparse.Namespace) -> str:
    """The anchors ledger is the owner's, at one fixed path; the caller can't name another or keep the record in it."""
    named = getattr(args, "anchors", None)
    if named and os.path.realpath(named) != os.path.realpath(ANCHORS):
        raise Refused("anchors-not-owner-ledger", "record heads are anchored only in the owner's ledger %s; the caller-named "
                      "%s is refused" % (ANCHORS, named))
    record = os.path.realpath(args.record)
    if record == os.path.realpath(OWNER_ROOT) or record.startswith(os.path.realpath(OWNER_ROOT) + os.sep):
        raise Refused("record-inside-owner-ledger", "the record %s sits inside the owner's ledger folder %s; the incident "
                      "record is the commander's artifact and lives elsewhere" % (args.record, OWNER_ROOT))
    return ANCHORS


def owner_slo(named: Optional[str]) -> str:
    if named and os.path.realpath(named) != os.path.realpath(OWNER_SLO):
        raise Refused("slo-not-owner-file", "an incident is judged only against the owner's SLO %s; the caller-named %s is "
                      "refused" % (OWNER_SLO, named))
    return OWNER_SLO


def load_anchor(path: str, incident_id: str) -> Optional[Dict[str, Any]]:
    """The owner's last anchored head for this incident, or None. The ledger lives apart from the record."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        raise Refused("anchor-unreadable", "the owner's anchors ledger %s is not UTF-8 text" % path)
    last = None
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            raise Refused("anchor-unreadable", "anchors line %d is not JSON" % n)
        if isinstance(entry, dict) and entry.get("incident_id") == incident_id:
            last = entry
    return last


def check_anchor(events: List[Dict[str, Any]], path: str) -> None:
    anchor = load_anchor(path, events[0]["incident_id"])
    if anchor is None:
        raise Refused("anchor-missing", "the anchors ledger holds no head for %s; the record was not written by these commands"
                      % events[0]["incident_id"])
    head = events[-1]
    if (anchor.get("seq"), anchor.get("sha256")) != (head["seq"], head["sha256"]):
        raise Refused("anchor-mismatch", "record head is seq %d %s, the owner anchored seq %s %s; the record was edited, "
                      "truncated or extended outside these commands" % (head["seq"], head["sha256"], anchor.get("seq"), anchor.get("sha256")))


def append_anchor(path: str, incident_id: str, ev: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(canonical({"incident_id": incident_id, "seq": ev["seq"], "sha256": ev["sha256"],
                            "recorded_at": ev["recorded_at"]}) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def owner_approvers(audience: str) -> List[str]:
    doc = load_json(COMMS_APPROVERS, "owner approvers file")
    names = doc.get(audience) if isinstance(doc, dict) else None
    if not isinstance(names, list) or not all(isinstance(n, str) and HUMAN.match(n) for n in names):
        raise InputError("owner approvers file %s needs a list of human: principals under %r" % (COMMS_APPROVERS, audience))
    return names


def evidence_status(events: List[Dict[str, Any]]) -> Optional[str]:
    resolved = next((e for e in reversed(events) if e["command"] == "resolve"), None)
    if resolved is None:
        return None
    evid = resolved["recovery_evidence"]
    path = evid.get("path") if isinstance(evid, dict) else None
    if not isinstance(path, str) or not os.path.isfile(path):
        raise Refused("evidence-changed", "recovery evidence %r is gone; the resolution has nothing behind it" % (path,))
    if sha_file(path) != evid.get("sha256"):
        raise Refused("evidence-changed", "recovery evidence %s changed after resolve (sha256 differs)" % path)
    return "match"


def current_state(events: List[Dict[str, Any]]) -> str:
    return events[-1]["to"]


def append_event(path: str, anchors: str, command: str, at: Optional[str], make: Any,
                 creating: Optional[str] = None) -> Dict[str, Any]:
    """Lock the record, verify the chain and its anchored head, let make(events, ts) refuse or return (to, data),
    append one line and anchor it. creating is the incident id when opening."""
    wall = datetime.datetime.now(UTC).replace(microsecond=0)
    stamp = parse_ts(at, "--at") if at else wall
    if (stamp - wall).total_seconds() > FUTURE_SKEW_S:
        raise InputError("--at %s is in the future (now %s)" % (iso(stamp), iso(wall)))
    if creating and load_anchor(anchors, creating) is not None:
        raise Refused("record-exists", "the anchors ledger already holds incident %s" % creating)

    flags = os.O_RDWR | os.O_APPEND | (os.O_CREAT if creating else 0)
    try:
        fd = os.open(path, flags, 0o644)
    except FileNotFoundError:
        raise InputError("record not found: %s (start one with `incident open`)" % path)
    with os.fdopen(fd, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            events = verify_chain(fh.read())
        except Tampered as exc:
            raise tamper_refusal(exc)
        except UnicodeDecodeError:
            raise InputError("record is not UTF-8 text: %s" % path)
        if creating and events:
            raise Refused("record-exists", "%s already holds an incident; the record is append-only" % path)
        if not creating and not events:
            raise InputError("record is empty: %s" % path)
        if events:
            check_anchor(events, anchors)
        if events and stamp < parse_ts(events[-1]["ts"], "last event ts"):
            raise InputError("--at %s is earlier than the last event (%s)" % (iso(stamp), events[-1]["ts"]))
        before = events[-1]["to"] if events else None
        if not creating and command in TRANSITIONS and before not in TRANSITIONS[command]:
            raise Refused("illegal-transition", "%s is not allowed from state %s" % (command, before),
                          command=command, state=before, allowed_from=sorted(TRANSITIONS[command]))
        to, data = make(events, stamp)
        ev = {"seq": len(events), "ts": iso(stamp), "recorded_at": iso(wall), "command": command, "from": before,
              "to": to or before, "prev_sha256": events[-1]["sha256"] if events else GENESIS}
        ev.update(data)
        ev["sha256"] = sha(ev)
        fh.write(canonical(ev) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        append_anchor(anchors, creating or events[0]["incident_id"], ev)
    return ev


def backdated(ev: Dict[str, Any]) -> Optional[int]:
    """Seconds between when a line was written and the time its --at claims, when over an hour; else None."""
    if "recorded_at" not in ev:
        return None
    gap = int((parse_ts(ev["recorded_at"], "recorded_at") - parse_ts(ev["ts"], "ts")).total_seconds())
    return gap if gap > BACKDATE_FLAG_S else None


def need(args: argparse.Namespace, field: str) -> str:
    value = getattr(args, field, None)
    if not isinstance(value, str) or not value.strip():
        raise InputError("--%s is required" % field.replace("_", "-"))
    return value.strip()


def check_principal(value: Optional[str], what: str) -> Optional[str]:
    if value is not None and not PRINCIPAL.match(value):
        raise InputError("%s must be a role id (fleet.role) or human:slug, got %r" % (what, value))
    return value


def untrusted(text: str, ref: str) -> List[Dict[str, Any]]:
    """Flag instruction-like text. Findings are recorded; they never change authority or evidence rules."""
    return scan(text, ref)


def summarize(ev: Dict[str, Any]) -> str:
    return str(ev.get("text") or ev.get("title") or "")[:120]


def incident_cmd(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    action = args.action
    path = args.record
    check_principal(args.by, "--by")
    anchors = owner_ledger(args)
    if action == "show":
        events = read_record(path)
        check_anchor(events, anchors)
        opened = events[0]
        facts = [e for e in events if e.get("kind") == "fact"]
        hyps = [e for e in events if e.get("kind") == "hypothesis"]
        evidence = next((e["recovery_evidence"] for e in reversed(events) if e["command"] == "resolve"), None)
        approved = {e["approves_seq"]: e["by"] for e in events if e["command"] == "approve"}
        comms = [{"seq": e["seq"], "audience": e["audience"],
                  "status": "approved" if e["seq"] in approved else e["status"], "approved_by": approved.get(e["seq"])}
                 for e in events if e["command"] == "comms"]
        return 0, {"command": "incident show", "incident_id": opened["incident_id"], "title": opened["title"],
                   "severity": opened["severity"], "state": current_state(events),
                   "commander": opened["commander"], "comms_coordinator": opened["comms_coordinator"],
                   "events": len(events), "head_sha256": events[-1]["sha256"], "facts": len(facts),
                   "hypotheses": len(hyps), "recovery_evidence": evidence, "recovery_evidence_check": evidence_status(events),
                   "communications": comms,
                   "backdated": [{"seq": e["seq"], "ts": e["ts"], "recorded_at": e["recorded_at"], "seconds": backdated(e)}
                                 for e in events if backdated(e)],
                   "timeline": [{"seq": e["seq"], "ts": e["ts"], "command": e["command"], "to": e["to"],
                                 "summary": summarize(e)} for e in events],
                   "assumptions": ["The hash chain detects an edited, inserted or reordered line; the head anchored in the owner's "
                                   "ledger detects a record rewritten and rehashed, or cut short, outside these commands.",
                                   "A process running as the same OS user can rewrite both the record and the owner's ledger, "
                                   "or run these commands under any listed name; only separate OS accounts or signed records stop that.",
                                   "ts is the time a caller's --at claims; recorded_at is when the line was written."]}
    if action == "open":
        inc_id, title = need(args, "id"), need(args, "title")
        commander, coordinator = need(args, "commander"), need(args, "comms_coordinator")
        if args.severity not in SEVERITIES:
            raise InputError("--severity must be one of %s" % ", ".join(SEVERITIES))
        if commander != COMMANDER_ROLE and not HUMAN.match(commander):
            raise InputError("--commander must be %s or human:slug" % COMMANDER_ROLE)
        check_principal(coordinator, "--comms-coordinator")
        slo_path = owner_slo(args.slo)

        def make_open(events: List[Dict[str, Any]], stamp: datetime.datetime) -> Tuple[str, Dict[str, Any]]:
            if commander == coordinator:
                raise Refused("roles-must-differ", "the incident commander and the communications coordinator must be different principals")
            data = {"incident_id": inc_id, "title": title, "severity": args.severity, "commander": commander,
                    "comms_coordinator": coordinator, "by": args.by,
                    "slo_name": load_slo(slo_path)["name"], "slo_sha256": sha_file(slo_path)}
            if args.label:
                data["label"] = args.label
            return "declared", data
        ev = append_event(path, anchors, "open", args.at, make_open, creating=inc_id)
        return 0, {"command": "incident open", "state": ev["to"], "sha256": ev["sha256"], "seq": ev["seq"],
                   "slo_sha256": ev.get("slo_sha256"), "backdated_seconds": backdated(ev)}

    text = args.text.strip() if action == "approve" and args.text else "approved" if action == "approve" else need(args, "text")

    def make(events: List[Dict[str, Any]], stamp: datetime.datetime) -> Tuple[Optional[str], Dict[str, Any]]:
        data: Dict[str, Any] = {"text": text, "by": args.by}
        findings = untrusted(text, "%s text" % action)
        to = TRANSITIONS.get(action, {}).get(current_state(events))
        if action == "update":
            if args.kind == "fact":
                data["source"] = need(args, "source")
            data["kind"] = args.kind
        elif action == "resolve":
            data["recovery_evidence"] = derive_recovery(events[0], args, stamp)
            with open(args.recovery_evidence, "r", encoding="utf-8", errors="replace") as efh:
                findings += untrusted(efh.read(), "recovery evidence")
        elif action == "comms":
            if args.approved_by:
                raise Refused("approval-needs-approve-step", "comms records a draft; an owner-listed approver approves it with "
                              "`incident approve --seq N --by human:slug`, never the drafter's own --approved-by")
            if args.audience == "external" and not args.by:
                raise InputError("an external draft needs --by, so its approver can be checked against its drafter")
            data.update(audience=args.audience, published=False, status="recorded" if args.audience == "internal" else "draft")
        elif action == "approve":
            data.update(approve_draft(events, args))
        elif action == "review":
            evidence_status(events)
            data.update(skeleton_path=args.out, **write_skeleton(events, stamp, need(args, "out")))
        if findings:
            data["untrusted_findings"] = findings
        return to, data

    if action == "resolve" and not args.recovery_evidence:
        raise Refused("recovery-evidence-required", "resolve needs --recovery-evidence EVENTS.jsonl (the monitoring events "
                      "after mitigation); resolve derives recovery from them under the SLO pinned at open")
    if action == "resolve":
        owner_slo(args.slo)
    if action == "comms" and args.audience not in ("internal", "external"):
        raise InputError("--audience must be internal or external")
    if action == "update" and args.kind not in ("fact", "hypothesis", "action"):
        raise InputError("--kind must be fact, hypothesis or action")
    ev = append_event(path, anchors, action, args.at, make)
    out = {"command": "incident " + action, "state": ev["to"], "seq": ev["seq"], "sha256": ev["sha256"],
           "untrusted_findings": ev.get("untrusted_findings", []), "backdated_seconds": backdated(ev)}
    if action == "comms":
        out.update(audience=ev["audience"], status=ev["status"], published=False,
                   note="This script never publishes; a human sends approved external text.")
    if action == "approve":
        out.update(approves_seq=ev["approves_seq"], status="approved", approved_by=ev["by"], published=False,
                   note="This script never publishes; a human sends approved external text.")
    if action == "resolve":
        out["recovery_evidence"] = ev["recovery_evidence"]
    if action == "review":
        out.update(skeleton=ev["skeleton_path"], skeleton_sha256=ev["skeleton_sha256"],
                   handoff="Complete the skeleton with the incident-learning skill (templates in %s)." % LEARNING_TEMPLATES)
    return 0, out


def derive_recovery(opened: Dict[str, Any], args: argparse.Namespace, stamp: datetime.datetime) -> Dict[str, Any]:
    """Recovery is computed here from the monitoring events, never read from a verdict someone wrote."""
    if "slo_sha256" not in opened:
        raise Refused("slo-not-recorded", "the incident was opened without a pinned SLO, so there is nothing to judge recovery against")
    slo_path = owner_slo(args.slo)
    if sha_file(slo_path) != opened["slo_sha256"]:
        raise Refused("slo-mismatch", "the owner's SLO %s changed after open (pinned sha256 %s)" % (slo_path, opened["slo_sha256"]))
    slo = load_slo(slo_path)
    try:
        events = load_events(args.recovery_evidence, slo)
    except InputError as exc:
        raise Refused("recovery-evidence-invalid", "recovery evidence must be the monitoring events log: %s" % exc)
    budget_fraction = 1 - slo["target"]

    def outage_at(end: datetime.datetime) -> Tuple[int, int, Optional[Decimal], List[str]]:
        total, bad = tally(events, end - datetime.timedelta(seconds=RECOVERY_WINDOW_S), end)
        rate = Decimal(bad) / Decimal(total) / budget_fraction if total else None
        _, _, alerts = evaluate_alerts(events, end, budget_fraction, None)
        return total, bad, rate, [a["long_window"] for a in alerts if a["severity"] == "page"]

    total, bad, rate, pages = outage_at(stamp)
    if not total:
        raise Refused("no-recent-data", "no monitoring events in the %d seconds before %s; recovery is unmeasured"
                      % (RECOVERY_WINDOW_S, iso(stamp)))
    if rate > 1 or pages:
        raise Refused("not-recovered", "at %s the last %d seconds burn the error budget at %s times its rate and %d page "
                      "alert(s) fire; the outage is not over" % (iso(stamp), RECOVERY_WINDOW_S, num(rate), len(pages)),
                      recent={"total": total, "bad": bad, "burn_rate": num(rate)}, page_alerts=pages)
    later = sorted({e[0] for e in events if e[0] > stamp})
    for when in later:  # recovery must hold for the rest of the log, not only up to the --at the caller picked
        l_total, l_bad, l_rate, l_pages = outage_at(when)
        if l_rate > 1 or l_pages:
            raise Refused("not-recovered", "the log continues after the recovery point %s, and at %s the last %d seconds burn "
                          "the error budget at %s times its rate with %d page alert(s); the outage is not over whatever "
                          "--at says" % (iso(stamp), iso(when), RECOVERY_WINDOW_S, num(l_rate), len(l_pages)),
                          recent={"total": total, "bad": bad, "burn_rate": num(rate)},
                          later_outage={"at": iso(when), "total": l_total, "bad": l_bad, "burn_rate": num(l_rate)},
                          page_alerts=l_pages)
    path = os.path.abspath(args.recovery_evidence)
    return {"path": path, "sha256": sha_file(path), "bytes": os.path.getsize(path), "slo_sha256": opened["slo_sha256"],
            "recent_window_seconds": RECOVERY_WINDOW_S, "recent": {"total": total, "bad": bad, "burn_rate": num(rate)},
            "checked_until": iso(later[-1]) if later else iso(stamp), "later_events_checked": len(later),
            "page_alerts": []}


def approve_draft(events: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    if args.seq is None:
        raise InputError("approve needs --seq N, the external draft to approve")
    draft = next((e for e in events if e["seq"] == args.seq), None)
    if draft is None or draft["command"] != "comms" or draft["audience"] != "external":
        raise Refused("not-an-external-draft", "seq %s is not an external comms draft" % args.seq)
    if any(e["command"] == "approve" and e["approves_seq"] == args.seq for e in events):
        raise Refused("already-approved", "draft %d is already approved" % args.seq)
    if not args.by or not HUMAN.match(args.by):
        raise Refused("approver-must-be-human", "external updates are approved by a human:slug; %r is not a human" % args.by)
    if args.by not in owner_approvers("external"):
        raise Refused("approver-not-authorized", "%s is not an external-comms approver in the owner file %s" % (args.by, COMMS_APPROVERS))
    if args.by == draft.get("by"):
        raise Refused("self-approval", "%s drafted seq %d and cannot approve it" % (args.by, args.seq))
    return {"approves_seq": args.seq, "text_sha256": sha(draft["text"])}


def write_skeleton(events: List[Dict[str, Any]], stamp: datetime.datetime, out_path: str) -> Dict[str, Any]:
    if os.path.exists(out_path):
        raise Refused("output-exists", "%s already exists; review will not overwrite it" % out_path)
    opened = events[0]
    rows = lambda items: items or ["| - | none recorded | - | - |"]  # noqa: E731
    facts = [e for e in events if e.get("kind") == "fact"]
    hyps = [e for e in events if e.get("kind") == "hypothesis"]
    resolved = next((e for e in events if e["command"] == "resolve"), None)
    templates = os.path.join(SKILLS_ROOT, "incident-learning", "templates")
    lines = [
        "# Incident-learning record (seed): %s" % opened["incident_id"], "",
        "Seeded %s from the hash-chained incident record (%d events, head sha256 %s)." % (iso(stamp), len(events), events[-1]["sha256"]),
        "Complete it with the `incident-learning` skill (MIT, Magnus Hedemark), which owns the learning pipeline.",
        "Templates: `%s/incident-learning-record.md`, `causal-evidence-ledger.md`, `follow-up-work-map.md`, `verification-and-closure-record.md`." % LEARNING_TEMPLATES,
        "Roles only, no individuals, no blame. Facts and hypotheses stay in separate tables.", "",
        "## Incident identifier", "", "| Field | Value |", "|---|---|",
        "| Incident ID | %s |" % opened["incident_id"], "| Title | %s |" % opened["title"],
        "| Severity | %s |" % opened["severity"], "| Declared | %s |" % opened["ts"],
        "| Resolved | %s |" % (resolved["ts"] if resolved else "not resolved"),
        "| Incident commander | %s |" % opened["commander"], "| Communications coordinator | %s |" % opened["comms_coordinator"], "",
        "## Observed facts", "", "| # | Fact | Source | Timestamp |", "|---|---|---|---|"]
    lines += rows(["| %d | %s | %s | %s |" % (i, e["text"], e["source"], e["ts"]) for i, e in enumerate(facts, 1)])
    lines += ["", "## Causal hypotheses", "", "| # | Hypothesis | Recorded | Confidence | Alternative explanations |", "|---|---|---|---|---|"]
    lines += rows(["| %d | %s | %s | unrated | to fill in |" % (i, e["text"], e["ts"]) for i, e in enumerate(hyps, 1)])
    lines += ["", "## Unresolved uncertainty", "", "- To fill in: open questions and competing hypotheses.", "",
              "## Timeline from the record", ""]
    lines += ["- %s %s -> %s: %s" % (e["ts"], e["command"], e["to"], summarize(e)) for e in events]
    lines += ["", "## Recovery evidence", ""]
    if resolved:
        evid = resolved["recovery_evidence"]
        lines.append("- %s (sha256 %s, %d bytes)" % (evid["path"], evid["sha256"], evid["bytes"]))
    else:
        lines.append("- none")
    lines += ["", "## Escaped from and follow-up work", "",
              "- To fill in with the incident-learning follow-up work map. Tickets alone don't close learning; closure needs verification evidence.", ""]
    text = "\n".join(lines)
    atomic_write(out_path, text)
    return {"skeleton_sha256": sha_file(out_path), "incident_learning_templates_present": os.path.isdir(templates)}


# ---- CLI -------------------------------------------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # JSON on stdout, exit 2
        emit({"error": message})
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    p = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", parser_class=Parser)
    s = sub.add_parser("slo-check", help="SLI, error budget and burn-rate alerts")
    s.add_argument("--slo", required=True)
    s.add_argument("--events", required=True)
    s.add_argument("--now", required=True)
    s.add_argument("--routing")
    s.add_argument("--claim-availability", action="store_true")
    i = sub.add_parser("incident", help="append-only incident record")
    i.add_argument("action", choices=["open", "update", "mitigate", "monitor", "resolve", "review", "comms", "approve", "show"])
    i.add_argument("--record", required=True)
    i.add_argument("--anchors", help="refused unless it is the owner's fixed ledger; the commands find it themselves")
    i.add_argument("--slo", help="optional; refused unless it is the owner's slo.json, which open pins")
    i.add_argument("--seq", type=int, help="approve: the external draft's seq")
    i.add_argument("--at")
    i.add_argument("--by")
    i.add_argument("--id")
    i.add_argument("--title")
    i.add_argument("--severity", default="sev3")
    i.add_argument("--commander")
    i.add_argument("--comms-coordinator", dest="comms_coordinator")
    i.add_argument("--label")
    i.add_argument("--text")
    i.add_argument("--kind", default="action")
    i.add_argument("--source")
    i.add_argument("--recovery-evidence", dest="recovery_evidence")
    i.add_argument("--audience")
    i.add_argument("--approved-by", dest="approved_by")
    i.add_argument("--out")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.cmd:
        emit({"error": "choose a subcommand: slo-check or incident"})
        return 2
    try:
        code, out = slo_check(args) if args.cmd == "slo-check" else incident_cmd(args)
    except InputError as exc:
        emit({"error": str(exc)})
        return 2
    except Refused as exc:
        emit(exc.payload)
        return 1
    emit(out)
    return code


if __name__ == "__main__":
    sys.exit(main())
