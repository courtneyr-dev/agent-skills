#!/usr/bin/env python3
"""answer_key: execute spreadsheet formulas, SQL queries, Python code and worked calculations, then
compare each result with the stated key and with an optional submitted answer.

  python3 answer_key.py check FILE

Prints JSON. Exit 0 when every key matches its executed result and every submitted answer matches,
1 for any mismatch, execution error, unsupported construct or invalid input, 2 for a usage error.
Python 3.9+ standard library only. The spreadsheet engine is a declared subset, not Excel or Sheets.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

KINDS = ("spreadsheet", "sql", "python", "calc")
DEFAULT_TOL = 1e-6
PY_TIMEOUT = 10
SQL_STEP_LIMIT = 2_000_000
FUNCTIONS = ("SUM", "AVERAGE", "MIN", "MAX", "COUNT", "ROUND", "ABS", "IF", "PMT", "FV")


class Unsupported(Exception):
    pass


class EvalError(Exception):
    pass


# ---------------------------------------------------------------- formula subset

TOKEN = re.compile(r"""\s*(?:
    (?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<str>"(?:[^"]|"")*")
  | (?P<range>\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+)
  | (?P<func>[A-Z][A-Z0-9.]*)\s*\(
  | (?P<ref>\$?[A-Z]{1,3}\$?\d+)
  | (?P<bool>TRUE|FALSE)\b
  | (?P<op><>|<=|>=|[-+*/^&=<>(),%])
)""", re.X)


def tokenize(src: str) -> List[Tuple[str, str]]:
    out, pos, src = [], 0, src.strip()
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise Unsupported("cannot read formula near %r" % src[pos:pos + 12])
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


def _cell_key(ref: str) -> str:
    return ref.replace("$", "").upper()


def _col_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def _col_name(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def expand_range(rng: str) -> List[str]:
    a, b = (_cell_key(x) for x in rng.split(":"))
    ma, mb = re.match(r"([A-Z]+)(\d+)", a), re.match(r"([A-Z]+)(\d+)", b)
    c1, c2 = sorted((_col_num(ma.group(1)), _col_num(mb.group(1))))
    r1, r2 = sorted((int(ma.group(2)), int(mb.group(2))))
    return ["%s%d" % (_col_name(c), r) for c in range(c1, c2 + 1) for r in range(r1, r2 + 1)]


class Parser:
    """Recursive descent with spreadsheet precedence: comparison < & < +- < */ < ^ < unary < %."""

    def __init__(self, tokens: List[Tuple[str, str]]):
        self.t, self.i = tokens, 0

    def peek(self) -> Optional[Tuple[str, str]]:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, value: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None or (value is not None and tok[1] != value):
            raise Unsupported("expected %r" % value if value else "unexpected end of formula")
        self.i += 1
        return tok

    def parse(self):
        node = self.comparison()
        if self.peek() is not None:
            raise Unsupported("unexpected %r" % self.peek()[1])
        return node

    def _binary(self, ops, nxt):
        node = nxt()
        while self.peek() and self.peek()[0] == "op" and self.peek()[1] in ops:
            op = self.take()[1]
            node = ("bin", op, node, nxt())
        return node

    def comparison(self):
        return self._binary(("=", "<>", "<", ">", "<=", ">="), self.concat)

    def concat(self):
        return self._binary(("&",), self.additive)

    def additive(self):
        return self._binary(("+", "-"), self.term)

    def term(self):
        return self._binary(("*", "/"), self.power)

    def power(self):
        return self._binary(("^",), self.unary)

    def unary(self):
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] in "+-":
            self.take()
            return ("neg", self.unary()) if tok[1] == "-" else self.unary()
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while self.peek() == ("op", "%"):
            self.take()
            node = ("bin", "/", node, ("num", 100.0))
        return node

    def primary(self):
        tok = self.take()
        kind, val = tok
        if kind == "num":
            return ("num", float(val))
        if kind == "str":
            return ("str", val[1:-1].replace('""', '"'))
        if kind == "bool":
            return ("bool", val == "TRUE")
        if kind == "ref":
            return ("ref", _cell_key(val))
        if kind == "range":
            return ("range", val)
        if kind == "func":
            if val not in FUNCTIONS:
                raise Unsupported("function %s is outside the supported subset (%s)" % (val, ", ".join(FUNCTIONS)))
            args = []
            if self.peek() != ("op", ")"):
                args.append(self.comparison())
                while self.peek() == ("op", ","):
                    self.take()
                    args.append(self.comparison())
            self.take(")")
            return ("call", val, args)
        if tok == ("op", "("):
            node = self.comparison()
            self.take(")")
            return node
        raise Unsupported("unexpected %r" % val)


def _num(v: Any) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return 0.0
    raise EvalError("#VALUE! text %r used as a number" % v)


def excel_round(x: float, digits: float) -> float:
    q = Decimal(1).scaleb(-int(digits))
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def pmt(rate, nper, pv, fv=0.0, typ=0.0):
    if nper == 0:
        raise EvalError("#NUM! PMT with zero periods")
    if rate == 0:
        return -(pv + fv) / nper
    g = (1 + rate) ** nper
    return -(rate * (pv * g + fv)) / ((1 + rate * typ) * (g - 1))


def fv_fn(rate, nper, payment, pv=0.0, typ=0.0):
    if rate == 0:
        return -(pv + payment * nper)
    g = (1 + rate) ** nper
    return -(pv * g + payment * (1 + rate * typ) * (g - 1) / rate)


class Sheet:
    def __init__(self, cells: Dict[str, Any], allow_refs: bool = True):
        self.raw = {_cell_key(k): v for k, v in cells.items()}
        self.cache: Dict[str, Any] = {}
        self.active: List[str] = []
        self.allow_refs = allow_refs

    def value(self, ref: str) -> Any:
        if not self.allow_refs:
            raise EvalError("a calculation cannot reference cell %s" % ref)
        if ref in self.cache:
            return self.cache[ref]
        if ref in self.active:
            raise EvalError("circular reference through %s" % " -> ".join(self.active + [ref]))
        raw = self.raw.get(ref)
        self.active.append(ref)
        try:
            if raw is None or raw == "":
                val = None
            elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
                val = float(raw)
            elif isinstance(raw, str) and raw.startswith("="):
                val = self.formula(raw[1:])
            else:
                try:
                    val = float(str(raw).replace(",", ""))
                except ValueError:
                    val = str(raw)
        finally:
            self.active.pop()
        self.cache[ref] = val
        return val

    def formula(self, src: str) -> Any:
        return self.ev(Parser(tokenize(src)).parse())

    def _flat(self, nodes) -> List[Any]:
        out = []
        for n in nodes:
            if n[0] == "range":
                out += [("cell", self.value(r)) for r in expand_range(n[1])]
            else:
                out.append(("arg", self.ev(n)))
        return out

    def _numbers(self, nodes) -> List[float]:
        # Spreadsheet rule: text and blanks inside ranges are skipped; direct text arguments are errors.
        nums = []
        for origin, v in self._flat(nodes):
            if origin == "cell" and (v is None or isinstance(v, str)):
                continue
            nums.append(_num(v))
        return nums

    def ev(self, n) -> Any:
        tag = n[0]
        if tag in ("num", "str", "bool"):
            return n[1]
        if tag == "ref":
            return self.value(n[1])
        if tag == "range":
            raise Unsupported("a range is only allowed inside a function")
        if tag == "neg":
            return -_num(self.ev(n[1]))
        if tag == "bin":
            op, a, b = n[1], self.ev(n[2]), self.ev(n[3])
            if op == "&":
                return "%s%s" % ("" if a is None else a, "" if b is None else b)
            if op in ("=", "<>", "<", ">", "<=", ">="):
                if isinstance(a, str) or isinstance(b, str):
                    a, b = str(a).lower(), str(b).lower()
                else:
                    a, b = _num(a), _num(b)
                return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
            x, y = _num(a), _num(b)
            if op == "+":
                return x + y
            if op == "-":
                return x - y
            if op == "*":
                return x * y
            if op == "/":
                if y == 0:
                    raise EvalError("#DIV/0!")
                return x / y
            if op == "^":
                return x ** y
        if tag == "call":
            name, args = n[1], n[2]
            if name in ("SUM", "AVERAGE", "MIN", "MAX", "COUNT"):
                nums = self._numbers(args)
                if name == "COUNT":
                    return float(len(nums))
                if name == "SUM":
                    return float(sum(nums))
                if not nums:
                    if name == "AVERAGE":
                        raise EvalError("#DIV/0! AVERAGE of no numbers")
                    return 0.0
                return {"AVERAGE": sum(nums) / len(nums), "MIN": min(nums), "MAX": max(nums)}[name]
            vals = [self.ev(a) for a in args] if name != "IF" else None
            if name == "ROUND":
                self._arity(name, args, 2, 2)
                return excel_round(_num(vals[0]), _num(vals[1]))
            if name == "ABS":
                self._arity(name, args, 1, 1)
                return abs(_num(vals[0]))
            if name == "IF":
                self._arity(name, args, 2, 3)
                cond = self.ev(args[0])
                if isinstance(cond, str):
                    raise EvalError("#VALUE! IF condition is text")
                if _num(cond) != 0:
                    return self.ev(args[1])
                return self.ev(args[2]) if len(args) == 3 else False
            if name == "PMT":
                self._arity(name, args, 3, 5)
                return pmt(*[_num(v) for v in vals])
            if name == "FV":
                self._arity(name, args, 3, 5)
                return fv_fn(*[_num(v) for v in vals])
        raise Unsupported("cannot evaluate %r" % (tag,))

    @staticmethod
    def _arity(name: str, args: list, lo: int, hi: int) -> None:
        if not lo <= len(args) <= hi:
            raise EvalError("%s takes %d to %d arguments, got %d" % (name, lo, hi, len(args)))


# ---------------------------------------------------------------- executors

def run_spreadsheet(item: Dict[str, Any]) -> Any:
    sheet = Sheet(item["cells"])
    return sheet.value(_cell_key(item["target"]))


def run_calc(item: Dict[str, Any]) -> Any:
    return Sheet({}, allow_refs=False).formula(item["expression"].lstrip("="))


def run_sql(item: Dict[str, Any]) -> Any:
    con = sqlite3.connect(":memory:")
    steps = [0]

    def guard():
        steps[0] += 1
        return 1 if steps[0] > SQL_STEP_LIMIT // 1000 else 0

    con.set_progress_handler(guard, 1000)
    try:
        con.executescript(item.get("setup", ""))
        rows = con.execute(item["query"]).fetchall()
    except sqlite3.Error as exc:
        raise EvalError("SQL error: %s" % exc)
    finally:
        con.close()
    return [list(r) for r in rows]


def run_python(item: Dict[str, Any]) -> Any:
    with tempfile.TemporaryDirectory(prefix="answer-key-") as tmp:
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": tmp, "LANG": "C.UTF-8"}
        try:
            proc = subprocess.run([sys.executable, "-I", "-c", item["code"]], input=item.get("stdin", ""),
                                  capture_output=True, text=True, timeout=PY_TIMEOUT, cwd=tmp, env=env)
        except subprocess.TimeoutExpired:
            raise EvalError("python timed out after %ds" % PY_TIMEOUT)
    if proc.returncode != 0:
        raise EvalError("python exited %d: %s" % (proc.returncode, proc.stderr.strip().splitlines()[-1:] or ""))
    return "\n".join(line.rstrip() for line in proc.stdout.strip().splitlines())


RUNNERS = {"spreadsheet": run_spreadsheet, "sql": run_sql, "python": run_python, "calc": run_calc}


# ---------------------------------------------------------------- comparison and validation

def same(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)
    if isinstance(a, str) and isinstance(b, str):
        return "\n".join(x.rstrip() for x in a.strip().splitlines()) == "\n".join(x.rstrip() for x in b.strip().splitlines())
    return a == b


def _sort_rows(rows: Any) -> Any:
    if isinstance(rows, list) and all(isinstance(r, list) for r in rows):
        return sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, default=str))
    return rows


def validate(doc: Any) -> List[str]:
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list) or not doc["items"]:
        return ["the file must be an object with a non-empty items list"]
    errors, seen = [], set()
    need = {"spreadsheet": ("cells", "target"), "sql": ("query",), "python": ("code",), "calc": ("expression",)}
    for n, item in enumerate(doc["items"]):
        where = "items[%d]" % n
        if not isinstance(item, dict):
            errors.append("%s is not an object" % where)
            continue
        iid = item.get("id")
        if not isinstance(iid, str) or not iid:
            errors.append("%s has no id" % where)
        elif iid in seen:
            errors.append("duplicate item id %s" % iid)
        seen.add(iid)
        kind = item.get("kind")
        if kind not in KINDS:
            errors.append("%s kind %r is not one of %s" % (iid or where, kind, ", ".join(KINDS)))
            continue
        if "key" not in item:
            errors.append("%s has no key; an answer key item needs the expected answer" % (iid or where))
        for field in need[kind]:
            if field not in item:
                errors.append("%s (%s) is missing %s" % (iid or where, kind, field))
        if kind == "spreadsheet" and not isinstance(item.get("cells"), dict):
            errors.append("%s cells must be an object of cell -> value or formula" % (iid or where))
        tol = item.get("tolerance", DEFAULT_TOL)
        if not isinstance(tol, (int, float)) or isinstance(tol, bool) or tol < 0:
            errors.append("%s tolerance must be a non-negative number" % (iid or where))
    return errors


def check_item(item: Dict[str, Any]) -> Dict[str, Any]:
    tol = float(item.get("tolerance", DEFAULT_TOL))
    res: Dict[str, Any] = {"id": item["id"], "kind": item["kind"], "key": item["key"]}
    try:
        computed = RUNNERS[item["kind"]](item)
    except Unsupported as exc:
        res.update(key_status="unsupported", detail=str(exc))
        return res
    except (EvalError, RecursionError) as exc:
        res.update(key_status="error", detail=str(exc))
        return res
    res["computed"] = computed
    key, comp = item["key"], computed
    if item["kind"] == "sql" and not item.get("ordered", False):
        key, comp = _sort_rows(key), _sort_rows(comp)
    res["key_status"] = "match" if same(comp, key, tol) else "mismatch"
    if res["key_status"] == "mismatch":
        res["detail"] = "executed result differs from the stated key; check the key and the formula, query or code"
    if "submitted" in item:
        sub = item["submitted"]
        if item["kind"] == "sql" and not item.get("ordered", False):
            sub = _sort_rows(sub)
        res["submitted"] = item["submitted"]
        res["submitted_status"] = "match" if same(comp, sub, tol) else "mismatch"
    return res


def check(doc: Dict[str, Any]) -> Dict[str, Any]:
    results = [check_item(i) for i in doc["items"]]
    summary = {s: sum(1 for r in results if r["key_status"] == s) for s in ("match", "mismatch", "error", "unsupported")}
    summary["submitted_mismatch"] = sum(1 for r in results if r.get("submitted_status") == "mismatch")
    ok = summary["match"] == len(results) and summary["submitted_mismatch"] == 0
    flagged = [r["id"] for r in results if r["key_status"] != "match" or r.get("submitted_status") == "mismatch"]
    return {"ok": ok, "engine": "edu-answer-key-check subset evaluator 0.1.0 (not Excel or Sheets); sqlite3 %s; python %s"
            % (sqlite3.sqlite_version, sys.version.split()[0]), "label": doc.get("label", ""),
            "summary": summary, "flagged": flagged, "items": results}


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "check":
        sys.stderr.write("usage: answer_key.py check FILE\n")
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "status": "invalid", "errors": ["cannot read %s: %s" % (argv[1], exc)]}, indent=2))
        return 1
    errors = validate(doc)
    if errors:
        print(json.dumps({"ok": False, "status": "invalid", "errors": errors}, indent=2))
        return 1
    result = check(doc)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
