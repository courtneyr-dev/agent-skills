"""A JSON Schema subset validator (standard library only).

It enforces exactly these keywords: $ref, type, enum, const, pattern, minLength, minItems,
uniqueItems, items, properties, required, additionalProperties, minimum, anyOf. A schema that uses
any other assertion keyword is rejected when loaded, so no rule is silently ignored.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Tuple

ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs"}
ASSERTIONS = {"$ref", "type", "enum", "const", "pattern", "minLength", "minItems", "uniqueItems",
              "items", "properties", "required", "additionalProperties", "minimum", "anyOf"}
TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}
SCHEMA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "schemas"))


class SchemaError(Exception):
    """The schema itself is malformed or uses a keyword this validator does not enforce."""


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


class Schemas:
    def __init__(self, directory: str = SCHEMA_DIR):
        self.directory = directory
        self._docs: Dict[str, Any] = {}

    def doc(self, name: str) -> Any:
        if name not in self._docs:
            with open(os.path.join(self.directory, name), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._audit(data, name)
            self._docs[name] = data
        return self._docs[name]

    def _audit(self, node: Any, name: str) -> None:
        if isinstance(node, dict):
            unknown = set(node) - ANNOTATIONS - ASSERTIONS
            if unknown:
                raise SchemaError("%s uses unsupported keywords: %s" % (name, ", ".join(sorted(unknown))))
            for key in ("items", "additionalProperties"):
                if isinstance(node.get(key), dict):
                    self._audit(node[key], name)
            for sub in (node.get("properties") or {}).values():
                self._audit(sub, name)
            for sub in (node.get("$defs") or {}).values():
                self._audit(sub, name)
            for sub in node.get("anyOf") or []:
                self._audit(sub, name)

    def resolve(self, ref: str, base: str) -> Tuple[str, Any]:
        file_part, _, frag = ref.partition("#")
        name = file_part or base
        node = self.doc(name)
        for part in [p for p in frag.split("/") if p]:
            try:
                node = node[part]
            except (KeyError, TypeError):
                raise SchemaError("unresolvable $ref %s from %s" % (ref, base))
        return name, node

    def validate(self, instance: Any, ref: str) -> List[str]:
        """Validate against a ref like 'role.schema.json' or 'files.schema.json#/$defs/roles'."""
        base, node = self.resolve(ref, "")
        errors: List[str] = []
        self._check(instance, node, base, "", errors)
        return errors

    def _check(self, inst: Any, s: Dict[str, Any], base: str, path: str, errs: List[str]) -> None:
        where = path or "/"
        if "$ref" in s:
            nbase, node = self.resolve(s["$ref"], base)
            self._check(inst, node, nbase, path, errs)
        if "anyOf" in s:
            if not any(not self._sub(inst, sub, base, path) for sub in s["anyOf"]):
                errs.append("%s: matches none of the allowed shapes" % where)
        if "type" in s:
            allowed = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(TYPES[t](inst) for t in allowed):
                errs.append("%s: expected %s" % (where, " or ".join(allowed)))
                return
        if "const" in s and not _same(inst, s["const"]):
            errs.append("%s: must be %s" % (where, json.dumps(s["const"])))
        if "enum" in s and not any(_same(inst, e) for e in s["enum"]):
            errs.append("%s: must be one of %s" % (where, ", ".join(json.dumps(e) for e in s["enum"])))
        if isinstance(inst, str):
            if "minLength" in s and len(inst.strip()) < s["minLength"]:
                errs.append("%s: needs at least %d characters" % (where, s["minLength"]))
            if "pattern" in s and not re.search(s["pattern"], inst):
                errs.append("%s: %r does not match %s" % (where, inst, s["pattern"]))
        if "minimum" in s and TYPES["number"](inst) and inst < s["minimum"]:
            errs.append("%s: must be >= %s" % (where, s["minimum"]))
        if isinstance(inst, list):
            if "minItems" in s and len(inst) < s["minItems"]:
                errs.append("%s: needs at least %d item(s)" % (where, s["minItems"]))
            if s.get("uniqueItems"):
                seen = [json.dumps(x, sort_keys=True) for x in inst]
                if len(set(seen)) != len(seen):
                    errs.append("%s: items must be unique" % where)
            if isinstance(s.get("items"), dict):
                for i, item in enumerate(inst):
                    self._check(item, s["items"], base, "%s/%d" % (path, i), errs)
        if isinstance(inst, dict):
            for key in s.get("required", []):
                if key not in inst:
                    errs.append("%s: missing required field %r" % (where, key))
            props = s.get("properties", {})
            for key, value in inst.items():
                if key in props:
                    self._check(value, props[key], base, "%s/%s" % (path, key), errs)
                elif s.get("additionalProperties") is False:
                    errs.append("%s: unknown field %r" % (where, key))
                elif isinstance(s.get("additionalProperties"), dict):
                    self._check(value, s["additionalProperties"], base, "%s/%s" % (path, key), errs)

    def _sub(self, inst: Any, s: Dict[str, Any], base: str, path: str) -> List[str]:
        errs: List[str] = []
        self._check(inst, s, base, path, errs)
        return errs
