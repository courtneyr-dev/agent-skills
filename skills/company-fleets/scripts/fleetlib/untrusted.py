"""Untrusted-content inspector.

Client files, issues, community text, lesson resources and fetched pages are data. scan() flags lines
that read as instructions to the agent so a reviewer sees them; enforcement does not depend on the
scan catching everything, because handoff.apply_worker_update refuses protected fields whatever the
worker was told. guarded_update() runs both and attaches the findings to the handoff.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

from factory_rig.canon import sha_bytes

from .handoff import apply_worker_update

# (category, pattern), matched per line, case-insensitive, first match wins: specific categories before override.
RULES: List[Tuple[str, "re.Pattern[str]"]] = [(c, re.compile(p, re.I)) for c, p in (
    ("authority", r"\b(approve|accept|sign off|certify)\b.{0,40}\b(your own|its own|own output|own work|yourself)\b"),
    ("authority", r"\b(you are|act as|become)\b.{0,20}\b(the )?(acceptance owner|approver|reviewer|admin(istrator)?|teacher of record)\b"),
    ("authority", r"\b(grant|give|elevate|escalate)\b.{0,30}\b(yourself|your)\b.{0,30}\b(access|permissions?|privileges?|authority|role)\b"),
    ("exfiltration", r"\b(send|e-?mail|upload|post|forward|transmit|export|copy)\b.{0,60}\b(records?|database|data ?base|files?|credentials?|passwords?|tokens?|secrets?|roster|grades?)\b.{0,80}\b(to|at|into)\b\s*\S*(@|https?://)"),
    ("tenant-access", r"\b(client|tenant|customer|classroom|school|community|organi[sz]ation)\s+[b-z](?:'s)?\b.{0,40}\b(records?|data|files?|accounts?|grades?|cases?)\b"),
    ("tenant-access", r"\b(all|every|other)\s+(clients?|tenants?|customers?|classrooms?|students?|communit(?:y|ies)|organi[sz]ations?)'?\b.{0,40}\b(records?|data|files?|accounts?|grades?|cases?)\b"),
    ("evidence", r"\b(skip|bypass|disable|waive|ignore)\b.{0,30}\b(tests?|review|verification|checks?|gate|evidence|qa|scan)\b"),
    ("evidence", r"\b(mark|report|record|set)\b.{0,40}\b(as )?(passed|passing|verified|approved|accepted|green)\b"),
    ("evidence", r"\b(change|edit|lower|relax|loosen|rewrite|remove|drop|delete)\b.{0,40}\b(acceptance criteria|criteria|threshold|rubric|exclusions?)\b"),
    # A strong trigger gets a wide window. A bare "now" counts only in a command ("Post the fix now"),
    # so ordinary prose such as "the release is out now" stays clean.
    ("publication", r"\b(publish|go live|deploy|post|announce|release|send)\b.{0,80}\b(immediately|right away|without (review|approval|sign-?off))\b"),
    ("publication", r"^\W*(?:(?:please|also|then|and)\s+)*(publish|go live|deploy|post|announce|release|send)\b.{0,40}\bnow\b"),
    ("override", r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,30}\b(instructions?|rules?|guidelines?|prompts?|policy|policies)\b"),
    ("override", r"\b(you are now|new instructions?|system prompt|developer message|assistant:|ai assistant\b.{0,20}\b(must|should|will))"),
)]


def scan(text: str, ref: str) -> List[Dict[str, Any]]:
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        for category, pattern in RULES:
            if pattern.search(line):
                findings.append({"ref": ref, "line": n, "category": category, "excerpt": line.strip()[:160]})
                break
    return findings


def describe_source(text: str, ref: str, tenant_id: str, classification: str, source_kind: str) -> Dict[str, Any]:
    """The handoff input entry for a piece of untrusted content, hash included."""
    return {"ref": ref, "tenant_id": tenant_id, "classification": classification, "trust": "untrusted",
            "source_kind": source_kind, "sha256": sha_bytes(text.encode("utf-8"))}


def guarded_update(h: Dict[str, Any], update: Dict[str, Any],
                   sources: Iterable[Tuple[str, str]]) -> Tuple[Dict[str, Any], List[Dict[str, str]], List[Dict[str, Any]]]:
    """Scan each (ref, text) source, apply only worker-writable fields, and attach the findings.

    Returns (new handoff, refused fields, findings). The legitimate analysis in update['summary'],
    update['outputs'] and update['evidence'] goes through; protected fields never change.
    """
    findings = [f for ref, text in sources for f in scan(text, ref)]
    update = dict(update)
    update["untrusted_findings"] = list(update.get("untrusted_findings", [])) + findings
    new, refused = apply_worker_update(h, update)
    return new, refused, findings
