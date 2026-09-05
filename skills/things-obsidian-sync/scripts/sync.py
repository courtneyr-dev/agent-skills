#!/usr/bin/env python3
"""Synchronize completion for Things tasks linked from approved Obsidian notes."""

import argparse
import fcntl
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


OBSIDIAN_VAULT = Path(os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes")))
DAILY_NOTES_DIR = OBSIDIAN_VAULT / "Review" / "Daily"
LINKED_NOTE_ROOTS = (
    OBSIDIAN_VAULT / "Areas" / "Content Strategy",
)
LOCK_PATH = Path("/tmp/com.example.things-obsidian-sync.lock")

TASK_LINE_PATTERN = re.compile(
    r"^(?P<prefix>\s*[-*+] \[)(?P<check>[ xX])(?P<after>\]\s+)"
    r"(?P<open_strike>~~)?"
    r"(?P<link>\[(?P<name>.+?)\]\(things:///show\?id=(?P<id>[A-Za-z0-9]+)\))"
    r"(?P<close_strike>~~)?(?P<suffix>.*)$"
)


def run_jxa(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown osascript error"
        raise RuntimeError(message)
    return result.stdout.strip()


def get_things_tasks(task_ids: list[str]) -> dict[str, dict]:
    if not task_ids:
        return {}

    ids_json = json.dumps(sorted(set(task_ids)))
    script = f'''\
const things = Application("Things3");
const ids = {ids_json};
const result = ids.map(id => {{
    try {{
        const task = things.toDos.byId(id);
        return {{
            id,
            actualId: task.id(),
            name: task.name(),
            status: task.status(),
            exists: true
        }};
    }} catch (error) {{
        return {{ id, exists: false, error: String(error) }};
    }}
}});
JSON.stringify(result);
'''
    tasks = json.loads(run_jxa(script))
    return {task["id"]: task for task in tasks}


def complete_things_tasks(task_ids: list[str]) -> dict[str, bool]:
    if not task_ids:
        return {}

    ids_json = json.dumps(sorted(set(task_ids)))
    script = f'''\
const things = Application("Things3");
const ids = {ids_json};
const result = ids.map(id => {{
    try {{
        const task = things.toDos.byId(id);
        task.status = "completed";
        return {{ id, success: task.status() === "completed" }};
    }} catch (error) {{
        return {{ id, success: false, error: String(error) }};
    }}
}});
JSON.stringify(result);
'''
    results = json.loads(run_jxa(script))
    return {result["id"]: result.get("success", False) for result in results}


def discover_notes(date_str: str, extra_roots: list[Path]) -> list[Path]:
    paths = set()
    daily_note = DAILY_NOTES_DIR / f"{date_str}.md"
    if daily_note.is_file():
        paths.add(daily_note)

    for root in (*LINKED_NOTE_ROOTS, *extra_roots):
        if not root.exists():
            raise RuntimeError(f"Configured sync root is unavailable: {root}")
        if root.is_file() and root.suffix.lower() == ".md":
            paths.add(root)
        elif root.is_dir():
            root_notes = [path for path in root.rglob("*.md") if path.is_file()]
            if root in LINKED_NOTE_ROOTS and not root_notes:
                raise RuntimeError(f"No Markdown notes are readable under: {root}")
            paths.update(root_notes)

    return sorted(paths)


def parse_note(path: Path) -> tuple[list[str], list[dict]]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    tasks = []

    for line_number, raw_line in enumerate(lines):
        line = raw_line.rstrip("\r\n")
        match = TASK_LINE_PATTERN.match(line)
        if not match:
            continue
        tasks.append(
            {
                "id": match.group("id"),
                "name": match.group("name"),
                "completed": match.group("check").lower() == "x",
                "line_number": line_number,
            }
        )

    return lines, tasks


def completed_line(raw_line: str) -> str:
    newline = "\n" if raw_line.endswith("\n") else ""
    line = raw_line.rstrip("\r\n")
    match = TASK_LINE_PATTERN.match(line)
    if not match:
        return raw_line
    return (
        f'{match.group("prefix")}x{match.group("after")}~~'
        f'{match.group("link")}~~{match.group("suffix")}{newline}'
    )


def atomic_write(path: Path, lines: list[str]) -> None:
    content = "".join(lines)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.chmod(temp_path, stat.S_IMODE(path.stat().st_mode))
    os.replace(temp_path, path)


def sync(
    date_str: str,
    direction: str,
    dry_run: bool,
    extra_roots: list[Path],
) -> int:
    try:
        note_paths = discover_notes(date_str, extra_roots)
    except (OSError, RuntimeError) as error:
        print(f"ERROR: Could not access configured Obsidian notes: {error}")
        return 2
    notes = {}
    references_by_id: dict[str, list[dict]] = {}

    for path in note_paths:
        lines, tasks = parse_note(path)
        notes[path] = {"lines": lines, "tasks": tasks, "changed": False}
        for task in tasks:
            reference = {**task, "path": path}
            references_by_id.setdefault(task["id"], []).append(reference)

    print(f"Scanning {len(note_paths)} notes with {len(references_by_id)} linked Things tasks")
    if not references_by_id:
        print("No linked Things checkboxes found")
        return 0

    try:
        things_tasks = get_things_tasks(list(references_by_id))
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"ERROR: Could not read Things tasks: {error}")
        return 2

    missing_ids = [
        task_id
        for task_id, task in things_tasks.items()
        if not task.get("exists", False)
    ]
    for task_id in missing_ids:
        print(f"WARNING: Things task not found: {task_id}")

    to_complete = []
    if direction in ("both", "obsidian-to-things"):
        for task_id, references in references_by_id.items():
            task = things_tasks.get(task_id, {})
            if not task.get("exists", False) or task.get("status") != "open":
                continue
            if any(reference["completed"] for reference in references):
                to_complete.append(task_id)

    completion_results: dict[str, bool] = {}
    if to_complete:
        for task_id in to_complete:
            task_name = things_tasks[task_id].get("name", task_id)
            prefix = "Would complete" if dry_run else "Completing"
            print(f"{prefix} in Things: {task_name}")
        if dry_run:
            completion_results = {task_id: True for task_id in to_complete}
        else:
            try:
                completion_results = complete_things_tasks(to_complete)
            except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                print(f"ERROR: Could not complete Things tasks: {error}")
                return 2
            failed_ids = [task_id for task_id, success in completion_results.items() if not success]
            if failed_ids:
                for task_id in failed_ids:
                    print(f"ERROR: Things completion failed: {task_id}")
                return 2

    effective_completed = {
        task_id
        for task_id, task in things_tasks.items()
        if task.get("exists", False) and task.get("status") == "completed"
    }
    effective_completed.update(
        task_id for task_id, success in completion_results.items() if success
    )

    obsidian_changes = 0
    if direction in ("both", "things-to-obsidian"):
        for task_id in effective_completed:
            for reference in references_by_id.get(task_id, []):
                if reference["completed"]:
                    continue
                note = notes[reference["path"]]
                line_number = reference["line_number"]
                note["lines"][line_number] = completed_line(note["lines"][line_number])
                note["changed"] = True
                obsidian_changes += 1
                prefix = "Would mark" if dry_run else "Marking"
                relative_path = reference["path"].relative_to(OBSIDIAN_VAULT)
                print(f"{prefix} complete in Obsidian: {relative_path} :: {reference['name']}")

    if not dry_run:
        for path, note in notes.items():
            if note["changed"]:
                atomic_write(path, note["lines"])

    print(
        f"Sync complete: {len(to_complete)} Things completions, "
        f"{obsidian_changes} Obsidian updates"
        + (" (dry run)" if dry_run else "")
    )
    return 0


def resolve_extra_roots(values: list[str]) -> list[Path]:
    roots = []
    for value in values:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = OBSIDIAN_VAULT / path
        roots.append(path)
    return roots


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync completion for Things tasks linked from approved Obsidian notes"
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Daily note date to include (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--direction",
        choices=("both", "things-to-obsidian", "obsidian-to-things"),
        default="both",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Extra vault-relative or absolute note root to scan; repeat as needed",
    )
    args = parser.parse_args()

    LOCK_PATH.touch(exist_ok=True)
    with LOCK_PATH.open("r+") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another Things and Obsidian sync is already running")
            return 0
        return sync(
            date_str=args.date,
            direction=args.direction,
            dry_run=args.dry_run,
            extra_roots=resolve_extra_roots(args.root),
        )


if __name__ == "__main__":
    raise SystemExit(main())
