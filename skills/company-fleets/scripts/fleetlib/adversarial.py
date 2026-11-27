"""Shared adversarial probes for any gate that declares skills/<id>/evals/adversarial.json.

Each probe runs in a fresh copy of the gate's declared inputs: setup, then a chain of transforms from
TRANSFORMS, then the gate's command. The probe holds when the result matches any refused_when set.
The same setup and command on unaltered inputs must match accepted_when first, so a probe that
nothing would accept can't count as held. The transforms cover the defect classes independent fleet
reviews found: relabeled kinds, grown audiences, recomputed hashes, deleted or padded principals,
address variants, flipped headers, paths outside the base, and negative or empty numbers.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

from factory_rig.canon import sha_bytes, sha_file

from .evalrun import _expect, judge
from .handoff import key_for
from .schema import Schemas

TIMEOUT = 300


class TransformError(Exception):
    pass


# ---------------------------------------------------------------- JSON pointer helpers

def _parts(pointer: str) -> List[str]:
    if not pointer.startswith("/"):
        raise TransformError("pointer %r must start with /" % pointer)
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def _parent(doc: Any, pointer: str) -> Tuple[Any, Any]:
    parts = _parts(pointer)
    node = doc
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    last = parts[-1]
    return node, (int(last) if isinstance(node, list) else last)


def _get(doc: Any, pointer: str) -> Any:
    node, key = _parent(doc, pointer)
    return node[key]


def _set(doc: Any, pointer: str, value: Any) -> None:
    node, key = _parent(doc, pointer)
    node[key] = value


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save(path: str, doc: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


def _text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _edit_json(path: str, fn: Callable[[Any], None]) -> None:
    doc = _load(path)
    fn(doc)
    _save(path, doc)


# ---------------------------------------------------------------- the transform library

def address_variant(addr: str, variant: str) -> str:
    local, _, domain = addr.partition("@")
    return {
        "plus-tag": "%s+probe@%s" % (local, domain),
        "trailing-dot": addr + ".",
        "zero-width": addr + "\u200b",
        "gmail-dot": "%s.%s@%s" % (local[:1], local[1:], domain) if len(local) > 1 else addr,
        "upper": addr.upper(),
    }[variant]


def _number_edge(value: Any, variant: str) -> Any:
    if variant == "negative":
        return -abs(value) if isinstance(value, (int, float)) and value else -1
    return {"zero": 0, "empty": "", "null": None, "huge": 10 ** 12}[variant]


def _canon_hash(obj: Any) -> str:
    return sha_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _op_set(work: str, t: Dict[str, Any]) -> None:
    _edit_json(os.path.join(work, t["file"]), lambda d: _set(d, t["pointer"], t["value"]))


def _op_delete(work: str, t: Dict[str, Any]) -> None:
    def fn(d):
        node, key = _parent(d, t["pointer"])
        del node[key]
    _edit_json(os.path.join(work, t["file"]), fn)


def _op_pad(work: str, t: Dict[str, Any]) -> None:
    _edit_json(os.path.join(work, t["file"]), lambda d: _set(d, t["pointer"], _get(d, t["pointer"]) + t.get("with", " ")))


def _op_grow(work: str, t: Dict[str, Any]) -> None:
    _edit_json(os.path.join(work, t["file"]), lambda d: _get(d, t["pointer"]).extend(t["add"]))


def _op_csv_add(work: str, t: Dict[str, Any]) -> None:
    path = os.path.join(work, t["file"])
    text = _text(path)
    header = next(r for r in csv.reader(io.StringIO(text)) if r and not r[0].startswith("#"))
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow([t["row"].get(h.strip(), "") for h in header])
    _write(path, text + ("" if text.endswith("\n") else "\n") + buf.getvalue())


def _op_address(work: str, t: Dict[str, Any]) -> None:
    path = os.path.join(work, t["file"])
    text = _text(path)
    if t["match"] not in text:
        raise TransformError("%s does not contain %s" % (t["file"], t["match"]))
    _write(path, text.replace(t["match"], address_variant(t["match"], t["variant"])))


def _op_rehash(work: str, t: Dict[str, Any]) -> None:
    src = t["of"]
    if "pointer" in src:
        digest = _canon_hash(_get(_load(os.path.join(work, src["file"])), src["pointer"]))
    else:
        digest = sha_file(os.path.join(work, src["file"]))
    _edit_json(os.path.join(work, t["file"]), lambda d: _set(d, t["pointer"], digest))


def _op_rehash_handoff(work: str, t: Dict[str, Any]) -> None:
    """Recompute every hash a handoff.v1 holds for the named outputs, as an attacker would after editing them."""
    base = os.path.join(work, t["base"])

    def fn(h):
        new = {o["path"]: sha_file(os.path.join(base, o["path"])) for o in h["outputs"] if o["path"] in t["outputs"]}
        for o in h["outputs"]:
            o["sha256"] = new.get(o["path"], o["sha256"])
        for ev in h["evidence"]:
            ev["about_sha256"] = new.get(ev["about"], ev["about_sha256"])
        h["idempotency_key"] = key_for(h)
    _edit_json(os.path.join(work, t["file"]), fn)


def _op_header(work: str, t: Dict[str, Any]) -> None:
    path = os.path.join(work, t["file"])
    text, n = re.subn(r"(?m)^(\W*%s:\s*)[^\n\\\"]*" % re.escape(t["header"]), lambda m: m.group(1) + t["value"], _text(path))
    if not n:
        raise TransformError("%s has no %s header" % (t["file"], t["header"]))
    _write(path, text)


def _op_outside(work: str, t: Dict[str, Any]) -> None:
    path = os.path.join(work, t["file"])
    target = t.get("target", "../../../../../../etc/hosts")

    def fn(d):
        _set(d, t["pointer"], target)
        if "hash_pointer" in t:
            real = os.path.normpath(os.path.join(os.path.dirname(path), target))
            _set(d, t["hash_pointer"], sha_file(real) if os.path.isfile(real) else "0" * 64)
    _edit_json(path, fn)


def _op_number(work: str, t: Dict[str, Any]) -> None:
    _edit_json(os.path.join(work, t["file"]), lambda d: _set(d, t["pointer"], _number_edge(_get(d, t["pointer"]), t["variant"])))


def _op_replace(work: str, t: Dict[str, Any]) -> None:
    path = os.path.join(work, t["file"])
    text = _text(path)
    if t["old"] not in text:
        raise TransformError("%s does not contain %r" % (t["file"], t["old"]))
    _write(path, text.replace(t["old"], t["new"], 1))


# op -> (function, required parameters beside op and file)
TRANSFORMS: Dict[str, Tuple[Callable[[str, Dict[str, Any]], None], Tuple[str, ...]]] = {
    "relabel": (_op_set, ("pointer", "value")),
    "json-set": (_op_set, ("pointer", "value")),
    "json-delete": (_op_delete, ("pointer",)),
    "pad": (_op_pad, ("pointer",)),
    "grow-list": (_op_grow, ("pointer", "add")),
    "csv-add-row": (_op_csv_add, ("row",)),
    "address-variant": (_op_address, ("match", "variant")),
    "rehash": (_op_rehash, ("pointer", "of")),
    "rehash-handoff": (_op_rehash_handoff, ("base", "outputs")),
    "header-flip": (_op_header, ("header", "value")),
    "path-outside-base": (_op_outside, ("pointer",)),
    "number-edge": (_op_number, ("pointer", "variant")),
    "text-replace": (_op_replace, ("old", "new")),
}


def apply(work: str, t: Dict[str, Any]) -> None:
    fn, params = TRANSFORMS[t["op"]]
    missing = [p for p in params if p not in t]
    if missing:
        raise TransformError("%s needs %s" % (t["op"], ", ".join(missing)))
    try:
        fn(work, t)
    except (KeyError, IndexError, ValueError, TypeError, AttributeError, OSError) as exc:
        raise TransformError("%s on %s failed: %s" % (t["op"], t["file"], exc))


# ---------------------------------------------------------------- running a declaration

def _fill(argv: List[str], ctx: Dict[str, str]) -> List[str]:
    out = []
    for a in argv:
        for k, v in ctx.items():
            a = a.replace("{%s}" % k, v)
        out.append(a)
    return out


def _run(argv: List[str], cwd: str) -> Dict[str, Any]:
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
        return {"exit": p.returncode, "stdout": p.stdout, "out": p.stdout + p.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit": 127, "stdout": "", "out": "runner error: %s" % exc}


def _attempt(skill_dir: str, decl: Dict[str, Any], probe: Optional[Dict[str, Any]], transforms: List[Dict[str, Any]]):
    """Copy inputs, run setup, apply transforms, run the command. Returns the command result."""
    src = probe or {}
    work = tempfile.mkdtemp(prefix="fleet-adversarial-")
    try:
        ctx = {"python": sys.executable, "skill": skill_dir, "skills": os.path.dirname(skill_dir), "work": work}
        for rel in decl["copy"]:
            s, d = os.path.join(skill_dir, rel), os.path.join(work, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            (shutil.copytree(s, d) if os.path.isdir(s) else shutil.copyfile(s, d))
        for argv in src.get("setup", decl.get("setup", [])):
            r = _run(_fill(argv, ctx), work)
            if r["exit"] != 0:
                return {"exit": r["exit"], "stdout": "", "out": "setup failed: %s\n%s" % (" ".join(argv), r["out"]), "setup_failed": True}
        for t in transforms:
            apply(work, t)
        return _run(_fill(src.get("command", decl["command"]), ctx), work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _norm(e: Dict[str, Any]) -> Dict[str, Any]:
    return _expect(e.get("exit") or list(range(256)), e.get("contains"), e.get("absent"), e.get("json"))


def run(skill_dir: str, decl_path: Optional[str] = None) -> Dict[str, Any]:
    skill_dir = os.path.abspath(skill_dir)
    decl_path = decl_path or os.path.join(skill_dir, "evals", "adversarial.json")
    decl = _load(decl_path)
    errors = Schemas().validate(decl, "adversarial.schema.json")
    for i, p in enumerate(decl.get("probes") if isinstance(decl.get("probes"), list) else []):
        for t in p.get("transforms", []) if isinstance(p, dict) else []:
            if isinstance(t, dict) and t.get("op") in TRANSFORMS:
                missing = [k for k in TRANSFORMS[t["op"]][1] if k not in t]
                if missing:
                    errors.append("/probes/%d (%s): %s needs %s" % (i, p.get("name"), t["op"], ", ".join(missing)))
    if errors:
        return {"skill": decl.get("skill"), "ok": False, "errors": errors, "probes": []}
    baselines: Dict[str, Tuple[bool, List[str]]] = {}
    results = []
    for p in decl["probes"]:
        key = json.dumps([p.get("setup", decl.get("setup", [])), p.get("command", decl["command"]),
                          p.get("accepted_when", decl["accepted_when"])])
        if key not in baselines:
            r = _attempt(skill_dir, decl, p, [])
            problems = judge(_norm(p.get("accepted_when", decl["accepted_when"])), r["exit"], r["stdout"], r["out"])
            baselines[key] = (not problems, problems)
        accepted, why = baselines[key]
        entry = {"name": p["name"], "class": p["class"]}
        if not accepted:
            entry.update(result="bad-baseline", detail="unaltered inputs were not accepted: " + "; ".join(why))
            results.append(entry)
            continue
        try:
            r = _attempt(skill_dir, decl, p, p["transforms"])
        except TransformError as exc:
            entry.update(result="transform-error", detail=str(exc))
            results.append(entry)
            continue
        refused = any(not judge(_norm(e), r["exit"], r["stdout"], r["out"]) for e in p["refused_when"])
        if "known_gap" in p:
            entry["result"] = "gap-closed" if refused else "known-gap"
            entry["known_gap"] = p["known_gap"]
        else:
            entry["result"] = "held" if refused else "hole"
        entry["exit"] = r["exit"]
        if not refused:
            entry["detail"] = r["out"][-400:]
        results.append(entry)
    bad = [x for x in results if x["result"] in ("hole", "bad-baseline", "transform-error")]
    counts = {k: sum(1 for x in results if x["result"] == k)
              for k in ("held", "hole", "known-gap", "gap-closed", "bad-baseline", "transform-error")}
    return {"skill": decl["skill"], "ok": not bad, "counts": counts, "probes": results}
