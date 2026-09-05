#!/usr/bin/env python3
"""Readwise Synthesis Pass — deterministic discovery + state for the weekly maker run.

This is the on-disk spine for the synthesis-pass loop (Osmani: "the agent forgets, the
repo doesn't"). It does NOT write notes — it computes the work queue and tracks state so
coverage rotates between runs. The judgment (what to actually write, which connections are
real) lives in SKILL.md and is done by Claude in-context.

Commands:
  sweep.py plan   [--sweep-size N]      → JSON work queue for this run (no writes)
  sweep.py record --created N --updated N --links N --mocs N [--report PATH]
                                        → advance state after a run (watermark + cursor + log)
  sweep.py status                       → show last run + cursor position

State lives in state.json beside this script. The run watermark drives "new arrivals";
the cursor round-robins the rotating sweep across Permanent + Literature notes.
"""
import argparse
import datetime
import json
import os
import re

VAULT = os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes"))
READWISE_DIR = os.path.join(VAULT, "Resources/Readwise")
LIT_DIR = os.path.join(VAULT, "Resources/Literature Notes")
PERM_DIR = os.path.join(VAULT, "Resources/Permanent Notes")
MOC_DIR = os.path.join(VAULT, "Resources/MOCs")
BACKLOG = os.path.join(VAULT, "_Synthesis Backlog.md")
REPORTS_DIR = os.path.join(VAULT, os.environ.get("REPORTS_DIR", "Reports"))
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

DEFAULT_SWEEP = 10
# First run has no watermark — only count backlog rows logged this recently as "new".
# Matches the weekly cadence with a little overlap.
FIRST_RUN_LOOKBACK_DAYS = 10
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_run": None, "sweep_cursor": 0, "runs": []}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def md_files(root):
    out = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.endswith(".md"):
                out.append(os.path.join(dirpath, n))
    return out


def rel(p):
    return p.replace(VAULT + "/", "")


def stable_note_list():
    """Permanent + Literature notes, stable-sorted by path — the rotating-sweep universe."""
    notes = md_files(PERM_DIR) + md_files(LIT_DIR)
    return sorted(notes)


def build_link_index(all_notes):
    """Map basename(lower) -> set of notes that link TO it; and note -> outbound count."""
    inbound = {}
    outbound = {}
    basenames = {os.path.splitext(os.path.basename(p))[0]: p for p in all_notes}
    for p in all_notes:
        try:
            text = open(p, encoding="utf-8").read()
        except Exception:
            text = ""
        links = [m.strip() for m in WIKILINK.findall(text)]
        outbound[p] = len(links)
        for l in links:
            inbound.setdefault(l.lower(), set()).add(p)
    return inbound, outbound, basenames


# Files that are legitimately link-less and always will be. Reporting them as
# orphans every run is noise that crowds out real ones — flagged in the
# 2026-08-01 run reports two passes running before being excluded here.
#   Drawing YYYY-MM-DD HH.MM.SS.md — Excalidraw canvases stored in Literature
#   Notes. They are drawings, not notes; they have no prose to link from.
ORPHAN_EXCLUDE = (
    re.compile(r"^Drawing \d{4}-\d{2}-\d{2}[ .\d]*$"),
)


def is_excluded_from_orphans(basename):
    return any(pat.match(basename) for pat in ORPHAN_EXCLUDE)


def find_orphans(all_notes, inbound, outbound):
    """A note is an orphan if it has no outbound links AND nothing links to it.

    Excalidraw drawings are excluded — see ORPHAN_EXCLUDE. They cannot hold
    links, so counting them as orphans permanently inflates the number and
    hides the notes that actually need wiring.
    """
    orphans = []
    for p in all_notes:
        base = os.path.splitext(os.path.basename(p))[0]
        if is_excluded_from_orphans(base):
            continue
        has_inbound = bool(inbound.get(base.lower()))
        has_outbound = outbound.get(p, 0) > 0
        if not has_inbound and not has_outbound:
            orphans.append(rel(p))
    return orphans


def backlog_unsynthesized():
    """Rows in the active backlog table still needing atoms/MOC/read."""
    if not os.path.exists(BACKLOG):
        return []
    rows = []
    in_active = False
    for line in open(BACKLOG, encoding="utf-8"):
        if "BACKLOG:ACTIVE:START" in line:
            in_active = True
            continue
        if "BACKLOG:ACTIVE:END" in line:
            break
        if not in_active or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[0] in ("Date", "---"):
            continue
        # COLS: Date, Title, doc_id, Type, Atoms, MOC, Read, Notes
        atoms, moc, read = cells[4], cells[5], cells[6]
        if atoms == "pending" or moc == "pending" or read.lower() == "no":
            rows.append({"date": cells[0], "title": cells[1], "doc_id": cells[2],
                         "type": cells[3], "atoms": atoms, "moc": moc, "read": read})
    return rows


def plan(sweep_size):
    state = load_state()
    last_run = state.get("last_run")
    if last_run:
        cutoff = last_run[:10]
    else:
        cutoff = (datetime.date.today()
                  - datetime.timedelta(days=FIRST_RUN_LOOKBACK_DAYS)).isoformat()

    backlog = backlog_unsynthesized()
    # "New arrivals" = backlog rows logged since the last run. The backlog Date is the
    # reliable signal (deep-read logs each processed doc); filesystem mtime is not,
    # because the Readwise plugin batch-rewrites hundreds of notes per sync.
    new_arrivals = [r for r in backlog if r.get("date", "") >= cutoff]
    # read:no alone is comprehension debt, not synthesis work — counting those rows
    # as "unsynthesized" inflated the 2026-08-24 plan to 819 when the real queue
    # was 37 atoms-pending + 46 moc-pending. Keep the two statuses separate.
    synth_queue = [r for r in backlog if r["atoms"] == "pending" or r["moc"] == "pending"]
    read_only = len(backlog) - len(synth_queue)

    all_notes = stable_note_list()
    inbound, outbound, _ = build_link_index(all_notes)
    orphans = find_orphans(all_notes, inbound, outbound)

    # Rotating sweep slice
    cursor = state.get("sweep_cursor", 0)
    total = len(all_notes)
    sweep = []
    if total:
        cursor %= total
        for i in range(min(sweep_size, total)):
            sweep.append(rel(all_notes[(cursor + i) % total]))

    return {
        "last_run": last_run,
        "sweep_cursor": cursor,
        "sweep_size": sweep_size,
        "counts": {
            "new_arrivals": len(new_arrivals),
            "backlog_unsynthesized": None,
            "backlog_atoms_pending": sum(1 for r in synth_queue if r["atoms"] == "pending"),
            "backlog_moc_pending": sum(1 for r in synth_queue if r["moc"] == "pending"),
            "backlog_read_only": read_only,
            "orphans": len(orphans),
            "total_notes": total,
            "mocs": len(md_files(MOC_DIR)),
        },
        "new_arrivals": new_arrivals,
        "backlog_unsynthesized": synth_queue,
        "sweep_slice": sweep,
        "orphans": orphans,
        "mocs": [rel(p) for p in sorted(md_files(MOC_DIR))],
    }


def cmd_plan(args):
    out = plan(args.sweep_size)
    out["counts"]["backlog_unsynthesized"] = len(out["backlog_unsynthesized"])
    print(json.dumps(out, indent=2))


def cmd_record(args):
    state = load_state()
    all_notes = stable_note_list()
    total = len(all_notes) or 1
    state["sweep_cursor"] = (state.get("sweep_cursor", 0) + args.swept) % total
    state["last_run"] = datetime.datetime.now().isoformat(timespec="seconds")
    state.setdefault("runs", []).append({
        "at": state["last_run"],
        "created": args.created, "updated": args.updated,
        "links": args.links, "mocs": args.mocs, "orphans_fixed": args.orphans_fixed,
        "report": args.report or "",
    })
    save_state(state)
    print(f"recorded: cursor→{state['sweep_cursor']}/{total} last_run={state['last_run']}")


def cmd_status(args):
    state = load_state()
    print(json.dumps({"last_run": state.get("last_run"),
                      "sweep_cursor": state.get("sweep_cursor", 0),
                      "runs_logged": len(state.get("runs", [])),
                      "last_3": state.get("runs", [])[-3:]}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--sweep-size", type=int, default=DEFAULT_SWEEP); p.set_defaults(fn=cmd_plan)
    r = sub.add_parser("record")
    r.add_argument("--created", type=int, default=0); r.add_argument("--updated", type=int, default=0)
    r.add_argument("--links", type=int, default=0); r.add_argument("--mocs", type=int, default=0)
    r.add_argument("--orphans-fixed", dest="orphans_fixed", type=int, default=0)
    r.add_argument("--swept", type=int, default=DEFAULT_SWEEP); r.add_argument("--report", default="")
    r.set_defaults(fn=cmd_record)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
