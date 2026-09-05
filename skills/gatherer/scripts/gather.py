#!/usr/bin/env python3
"""Gather the user's open work into today's daily note.

Sources: GitHub (via the gh CLI), WordPress core Trac (via the wordpress-trac
MCP endpoint, called over plain JSON-RPC), and Things 3 (via AppleScript).
Writes one `## Gathered` section into Review/Daily/YYYY-MM-DD.md, replacing
the previous one on rerun and leaving every other section untouched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

VAULT = pathlib.Path(os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes")))
DAILY_DIR = VAULT / "Review" / "Daily"
STATE_PATH = VAULT / "Reports" / "_gatherer-state.json"
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
WATCHLIST_PATH = SKILL_DIR / "trac-watchlist.txt"

TRAC_MCP_URL = "https://mcp-server-wporg-trac-staging.a8cai.workers.dev/mcp"
TRAC_TICKET_URL = "https://core.trac.wordpress.org/ticket/{id}"
TRAC_USER = "you"

HEADING = "## Gathered"
START = "<!-- gathered:start -->"
END = "<!-- gathered:end -->"
ANCHORS = ("## 📥 Daily Inboxes", "## 🌅 Daily Routine", "## ⏱ Time Log", "## 📊 Metadata")
H1_OR_H2 = re.compile(r"#{1,2} ")

SOURCES = ("github", "trac", "things")
LABELS = {"github": "GitHub", "trac": "WordPress Trac", "things": "Things"}
THINGS_LISTS = {"today": "Today", "inbox": "Inbox", "anytime": "Anytime",
                "upcoming": "Upcoming", "someday": "Someday"}
MAX_ATTEMPTS = 5
PAGE_SIZE = 100
US, RS = "\x1f", "\x1e"


class SourceError(Exception):
    """A source could not be collected; the run continues with the others."""


def log(msg: str) -> None:
    print(f"gather: {msg}", file=sys.stderr)


# --- rate limiting -----------------------------------------------------------

def backoff_seconds(status: int, headers: dict, attempt: int):
    """Seconds to wait before retrying, or None when the call should not be retried."""
    if attempt >= MAX_ATTEMPTS - 1:
        return None
    rate_limited = status == 429 or (status == 403 and headers.get("x-ratelimit-remaining") == "0")
    if rate_limited:
        retry_after = headers.get("retry-after", "").strip()
        if retry_after.isdigit():
            return float(retry_after)
        reset = headers.get("x-ratelimit-reset", "").strip()
        if reset.isdigit():
            return float(min(max(int(reset) - time.time() + 1, 1), 120))
        return float(2 ** attempt)
    if status >= 500:
        return float(2 ** attempt)
    return None


# --- GitHub ------------------------------------------------------------------

def parse_gh_response(raw: str):
    """Split `gh api --include` output into (status, lower-cased headers, body)."""
    if not raw.strip():
        return 0, {}, ""
    head, sep, body = raw.partition("\r\n\r\n")
    if not sep:
        head, sep, body = raw.partition("\n\n")
    lines = head.splitlines()
    match = re.match(r"HTTP/\S+\s+(\d{3})", lines[0]) if lines else None
    status = int(match.group(1)) if match else 0
    headers = {}
    for line in lines[1:]:
        key, colon, value = line.partition(":")
        if colon:
            headers[key.strip().lower()] = value.strip()
    return status, headers, body


def gh_api(path: str, params: dict | None = None):
    cmd = ["gh", "api", "--include", "--method", "GET", path]
    for key, value in (params or {}).items():
        cmd += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
    last = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except FileNotFoundError:
            raise SourceError("gh is not installed")
        except subprocess.TimeoutExpired:
            raise SourceError(f"gh timed out on {path}")
        status, headers, body = parse_gh_response(proc.stdout)
        if 200 <= status < 300:
            return json.loads(body)
        last = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"HTTP {status}"
        if status == 0:
            break  # gh itself failed (auth, network); retrying won't help
        delay = backoff_seconds(status, headers, attempt)
        if delay is None:
            break
        log(f"github: {path} returned HTTP {status}; retrying in {delay:.0f}s")
        time.sleep(delay)
    raise SourceError(last)


def gh_pages(path: str, params: dict, key: str | None = None) -> list:
    items: list = []
    for page in range(1, 11):
        data = gh_api(path, {**params, "per_page": PAGE_SIZE, "page": page})
        batch = data[key] if key else data
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
    return items


def gather_github() -> tuple[list, dict]:
    items: list = []
    seen: set = set()

    def add(raw: dict, kind: str, role: str) -> None:
        url = raw.get("html_url", "")
        if not url or url in seen:
            return
        seen.add(url)
        repo = (raw.get("repository") or {}).get("full_name") \
            or "/".join(raw.get("repository_url", "").split("/")[-2:])
        items.append({"ref": f"{repo}#{raw['number']}", "title": raw.get("title", ""), "url": url,
                      "updated": raw.get("updated_at", ""), "kind": kind, "role": role})

    for raw in gh_pages("/search/issues", {"q": "is:pr is:open author:@me"}, key="items"):
        add(raw, "pr", "authored")
    for raw in gh_pages("/search/issues", {"q": "is:pr is:open review-requested:@me"}, key="items"):
        add(raw, "pr", "review requested")
    for raw in gh_pages("/issues", {"filter": "assigned", "state": "open"}):
        add(raw, "pr" if raw.get("pull_request") else "issue", "assigned")
    return items, {}


# --- WordPress Trac ----------------------------------------------------------

def parse_watchlist(text: str) -> list[int]:
    ids = []
    for line in text.splitlines():
        match = re.match(r"\s*(\d+)", line)
        if match and not line.lstrip().startswith("#"):
            ids.append(int(match.group(1)))
    return ids


def trac_call(tool: str, arguments: dict) -> dict:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": tool, "arguments": arguments}}).encode()
    last = ""
    for attempt in range(MAX_ATTEMPTS):
        req = urllib.request.Request(TRAC_MCP_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "gatherer/1.0 (example.com daily note)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise SourceError(str(data["error"])[:200])
            return json.loads(data["result"]["content"][0]["text"])
        except urllib.error.HTTPError as err:
            status = err.code
            headers = {k.lower(): v for k, v in err.headers.items()}
            last = f"HTTP {status}"
        except OSError as err:  # URLError, timeouts, connection resets
            status, headers, last = 503, {}, f"network: {err}"[:200]
        except (KeyError, IndexError, ValueError) as err:
            raise SourceError(f"unexpected MCP reply: {err}")
        delay = backoff_seconds(status, headers, attempt)
        if delay is None:
            break
        log(f"trac: {tool} got {last}; retrying in {delay:.0f}s")
        time.sleep(delay)
    raise SourceError(last)


def parse_trac_ticket(ticket_id: int, payload: dict, user: str) -> dict:
    ticket = ((payload or {}).get("metadata") or {}).get("ticket") or {}
    owner = (ticket.get("owner") or "").strip()
    return {"id": ticket_id, "ref": f"#{ticket_id}", "title": ticket.get("summary") or "",
            "url": TRAC_TICKET_URL.format(id=ticket_id), "updated": "",
            "status": (ticket.get("status") or "").strip(), "milestone": (ticket.get("milestone") or "").strip(),
            "owner": owner, "relation": "owned" if owner and owner == user else "following"}


def gather_trac(watchlist_path: pathlib.Path, user: str) -> tuple[list, dict]:
    try:
        ids = parse_watchlist(watchlist_path.read_text(encoding="utf-8"))
    except OSError as err:
        raise SourceError(f"watchlist unreadable: {err}")
    items, failures, last = [], 0, ""
    for ticket_id in ids:
        try:
            payload = trac_call("getTicket", {"id": ticket_id, "includeComments": False})
        except SourceError as err:
            failures += 1
            last = str(err)
            log(f"trac: #{ticket_id} lookup failed: {err}")
            payload = {}
        item = parse_trac_ticket(ticket_id, payload, user)
        if not item["title"]:
            item["title"] = f"(lookup failed: {last or 'empty reply'})"
        items.append(item)
    if ids and failures == len(ids):
        raise SourceError(f"all {len(ids)} lookups failed: {last}")
    return [i for i in items if i["status"] != "closed"], {"watched": len(ids)}


# --- Things 3 ----------------------------------------------------------------

THINGS_SCRIPT = """
on iso(d)
	if d is missing value then return ""
	set secs to time of d
	return (year of d as text) & "-" & my pad(month of d as integer) & "-" & my pad(day of d) & "T" & my pad(secs div 3600) & ":" & my pad((secs mod 3600) div 60) & ":" & my pad(secs mod 60)
end iso
on pad(n)
	if n < 10 then return "0" & (n as text)
	return n as text
end pad
on txt(v)
	if v is missing value then return ""
	return v as text
end txt
on aslist(v)
	if class of v is list then return v
	return {v}
end aslist
set us to character id 31
set rs to character id 30
tell application "Things3"
	set ids to my aslist(id of every to do of list "__LIST__")
	set names to my aslist(name of every to do of list "__LIST__")
	set mods to my aslist(modification date of every to do of list "__LIST__")
	set dues to my aslist(due date of every to do of list "__LIST__")
	set projs to my aslist(name of project of every to do of list "__LIST__")
	set ars to my aslist(name of area of every to do of list "__LIST__")
end tell
set out to ""
repeat with i from 1 to (count of ids)
	set out to out & (item i of ids) & us & (item i of names) & us & my iso(item i of mods) & us & my iso(item i of dues) & us & my txt(item i of projs) & us & my txt(item i of ars) & rs
end repeat
return out
"""


def parse_things_output(raw: str, list_name: str) -> list:
    items = []
    for record in raw.split(RS):
        fields = record.split(US)
        if len(fields) < 6:
            continue
        task_id, name, modified, due, project, area = (f.strip() for f in fields[:6])
        if not task_id:
            continue
        items.append({"id": task_id, "title": name, "url": f"things:///show?id={task_id}",
                      "updated": modified, "due": due[:10], "project": project, "area": area,
                      "list": list_name})
    return items


def gather_things(lists: list[str]) -> tuple[list, dict]:
    items: list = []
    seen: set = set()
    for name in lists:
        script = THINGS_SCRIPT.replace("__LIST__", THINGS_LISTS[name])
        try:
            proc = subprocess.run(["osascript"], input=script, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=180)
        except FileNotFoundError:
            raise SourceError("osascript not found (macOS only)")
        except subprocess.TimeoutExpired:
            raise SourceError(f"AppleScript timed out reading the {name} list")
        if proc.returncode != 0:
            raise SourceError(proc.stderr.strip()[-200:] or f"osascript exit {proc.returncode}")
        for item in parse_things_output(proc.stdout, name):
            if item["id"] not in seen:
                seen.add(item["id"])
                items.append(item)
    return items, {}


# --- rendering ---------------------------------------------------------------

def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _link_text(text: str) -> str:
    return _clean(text).replace("[", "(").replace("]", ")")


def _sort_key(source: str):
    if source == "trac":
        return lambda i: i.get("id", 0)
    return lambda i: (i.get("updated") or "", _clean(i.get("title", "")))


def format_item(source: str, item: dict) -> str:
    url = item["url"]
    if source == "github":
        role = {"authored": "PR you opened", "review requested": "PR, review requested",
                "assigned": "PR assigned to you"}.get(item.get("role"), "PR")
        kind = "issue" if item.get("kind") == "issue" else role
        parts = [_clean(item.get("title", "")), kind, (item.get("updated") or "")[:10]]
        return f"- [{_link_text(item['ref'])}]({url}) " + " · ".join(p for p in parts if p)
    if source == "trac":
        parts = [_clean(item.get("title", "")), item.get("status", ""), item.get("milestone", ""),
                 item.get("relation", "")]
        return f"- [{item['ref']}]({url}) " + " · ".join(p for p in parts if p)
    where = item.get("project") or item.get("area") or ""
    due = f"due {item['due']}" if item.get("due") else ""
    parts = [THINGS_LISTS.get(item.get("list", ""), item.get("list", "")), where, due]
    return f"- [{_link_text(item.get('title', ''))}]({url})" + "".join(f" · {p}" for p in parts if p)


def _summary_part(source: str, result: dict) -> str:
    items = result.get("items", [])
    label = f"{LABELS[source]} {len(items)}"
    if source == "github" and items:
        issues = sum(1 for i in items if i.get("kind") == "issue")
        label += f" ({_plural(issues, 'issue')}, {len(items) - issues} PR{'' if len(items) - issues == 1 else 's'})"
    watched = (result.get("meta") or {}).get("watched")
    if source == "trac" and watched is not None:
        label += f" (of {watched} watched)" if watched else " (0 watched)"
    if result.get("error"):
        if result.get("stale_from"):
            label += f", stale from {result['stale_from'][:16].replace('T', ' ')} (refresh failed: {result['error']})"
        else:
            label += f", failed: {result['error']}"
    return label


def render_section(gathered: dict, now: dt.datetime) -> str:
    sources = [s for s in SOURCES if s in gathered]
    total = sum(len(gathered[s].get("items", [])) for s in sources)
    summary = " · ".join(_summary_part(s, gathered[s]) for s in sources)
    lines = [HEADING, START, f"_{now:%Y-%m-%d %H:%M} · {_plural(total, 'open item')} · {summary}_"]
    for source in sources:
        result = gathered[source]
        items = sorted(result.get("items", []), key=_sort_key(source), reverse=True)
        lines += ["", f"### {LABELS[source]}", ""]
        if not items:
            if result.get("error"):
                lines.append(f"_failed: {result['error']}, no earlier list to fall back on_")
            elif source == "trac" and (result.get("meta") or {}).get("watched") == 0:
                lines.append("_no tickets on the watchlist yet_")
            else:
                lines.append("_nothing open_")
            continue
        if result.get("stale_from"):
            lines.append(f"_stale list from {result['stale_from'][:16].replace('T', ' ')}; refresh failed: {result['error']}_")
            lines.append("")
        lines += [format_item(source, item) for item in items]
    lines.append(END)
    return "\n".join(lines) + "\n"


# --- daily note --------------------------------------------------------------

def _join(before: list, section: str, after: list) -> str:
    head = "".join(before).rstrip("\n")
    tail = "".join(after).lstrip("\n")
    out = (head + "\n\n" if head else "") + section
    if tail:
        out += "\n" + tail
    return out


def splice_section(note: str, section: str) -> str:
    """Replace the existing `## Gathered` section or insert one before the first anchor heading."""
    section = section.rstrip("\n") + "\n"
    lines = note.splitlines(keepends=True)
    stripped = [line.rstrip("\r\n") for line in lines]
    if HEADING in stripped:
        start = stripped.index(HEADING)
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if stripped[j] == END:
                end = j + 1
                break
            if H1_OR_H2.match(stripped[j]):
                end = j
                break
        return _join(lines[:start], section, lines[end:])
    for anchor in ANCHORS:
        if anchor in stripped:
            idx = stripped.index(anchor)
            return _join(lines[:idx], section, lines[idx:])
    return _join(lines, section, [])


def write_note(path: pathlib.Path, section: str) -> str:
    """Read-modify-write with an atomic replace; recompute if the note changed underneath."""
    for _ in range(3):
        stat = path.stat()
        note = path.read_text(encoding="utf-8")
        new = splice_section(note, section)
        if new == note:
            return "unchanged"
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".gather-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(new)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, stat.st_mode & 0o777)
            if path.stat().st_mtime_ns != stat.st_mtime_ns:
                os.unlink(tmp)
                log("note changed while gathering; recomputing")
                continue
            os.replace(tmp, path)
            return "written"
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    raise RuntimeError("the note kept changing underneath; gave up after 3 attempts")


# --- state -------------------------------------------------------------------

def load_state(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(path: pathlib.Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_with_state(fresh: dict, state: dict) -> dict:
    """A source that failed with nothing to show falls back to its last good list, marked stale."""
    previous = (state or {}).get("sources") or {}
    for source, result in fresh.items():
        prior = previous.get(source) or {}
        if result.get("error") and not result.get("items") and prior.get("items"):
            result["items"] = prior["items"]
            result["stale_from"] = prior.get("fetched_at") or state.get("last_run", "")
    return fresh


# --- main --------------------------------------------------------------------

def collect(source: str, args) -> tuple[list, dict]:
    if source == "github":
        return gather_github()
    if source == "trac":
        return gather_trac(args.trac_watchlist, args.trac_user)
    return gather_things(args.things_lists)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gather open work into today's daily note.")
    ap.add_argument("--date", help="daily note date, YYYY-MM-DD (default: today)")
    ap.add_argument("--note", type=pathlib.Path, help="daily note path (default: Review/Daily/<date>.md)")
    ap.add_argument("--sources", default=",".join(SOURCES), help="comma list of github,trac,things")
    ap.add_argument("--things-lists", default="today,inbox",
                    help="comma list of " + ",".join(THINGS_LISTS))
    ap.add_argument("--trac-watchlist", type=pathlib.Path, default=WATCHLIST_PATH)
    ap.add_argument("--trac-user", default=TRAC_USER)
    ap.add_argument("--state", type=pathlib.Path, default=STATE_PATH)
    ap.add_argument("--dry-run", action="store_true", help="print the section; write nothing")
    ap.add_argument("--print", action="store_true", help="also print the section after writing")
    args = ap.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [s for s in sources if s not in SOURCES]
    args.things_lists = [s.strip() for s in args.things_lists.split(",") if s.strip()]
    bad += [s for s in args.things_lists if s not in THINGS_LISTS]
    if bad:
        log(f"unknown source or list: {', '.join(bad)}")
        return 2

    now = dt.datetime.now()
    date = args.date or now.strftime("%Y-%m-%d")
    note_path = args.note or DAILY_DIR / f"{date}.md"
    state = load_state(args.state)

    gathered: dict = {}
    for source in sources:
        try:
            items, meta = collect(source, args)
            gathered[source] = {"items": items, "error": None, "meta": meta,
                                "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%S")}
            log(f"{source}: {len(items)} open")
        except SourceError as err:
            log(f"{source}: FAILED: {err}")
            gathered[source] = {"items": [], "error": str(err)}
    gathered = merge_with_state(gathered, state)
    for source, result in gathered.items():
        if result.get("stale_from"):
            result["fetched_at"] = result["stale_from"]

    section = render_section(gathered, now)
    summary = section.splitlines()[2].strip("_")
    all_failed = sources and all(gathered[s].get("error") and not gathered[s].get("items") for s in sources)

    if args.dry_run:
        print(section, end="")
        log(f"dry run, nothing written · {summary}")
        return 2 if all_failed else 0

    if not note_path.exists():
        print(section, end="")
        log(f"daily note not found: {note_path} (section printed above, nothing written)")
        return 1
    try:
        outcome = write_note(note_path, section)
    except (OSError, RuntimeError) as err:
        log(f"could not write {note_path}: {err}")
        return 1
    save_state(args.state, {
        "last_run": now.strftime("%Y-%m-%dT%H:%M:%S"), "date": date, "note": str(note_path),
        "counts": {s: len(gathered[s].get("items", [])) for s in sources},
        "sources": {s: {k: gathered[s].get(k) for k in ("items", "error", "fetched_at", "stale_from")
                        if gathered[s].get(k) is not None} for s in sources},
    })
    if args.print:
        print(section, end="")
    print(f"{HEADING} {outcome} → {note_path}\n{summary}")
    return 2 if all_failed else 0


if __name__ == "__main__":
    sys.exit(main())
