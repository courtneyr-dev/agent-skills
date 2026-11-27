#!/usr/bin/env python3
"""Deterministic pre-send gate for one email campaign. Stages a send; never sends.

Reads a campaign, a consent ledger, a sender-authentication fixture and an optional
send authorization. Prints one JSON object. Standard library only; no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

DISPATCH_ROUTE = "the tenant's existing authorized email system, by a human"
ALWAYS_BLOCKING = ("hard-bounce", "complaint", "legal-hold")
SUPPRESSION_REASONS = ("unsubscribed", "hard-bounce", "complaint", "manual", "legal-hold")
PERMISSIONS = ("opted-in", "none", "withdrawn")
ONE_CLICK = "List-Unsubscribe=One-Click"

NOT_CHECKED = [
    "live DNS: SPF, DKIM and DMARC come from the fixture, not from the domain",
    "DKIM signature validity and SPF alignment with the sending IP",
    "whether the consent ledger matches the tenant's live email system",
    "copy quality, claims, legal and CAN-SPAM or GDPR footer content",
    "colour contrast, reading order and link text in the rendered email",
    "that the unsubscribe endpoint exists and honors a one-click POST",
    "provider reputation and complaint rates",
]
HUMAN_REVIEW = [
    "a named human approves dispatch in the tenant's existing authorized email system",
    "the consent steward confirms the ledger is current; only the steward removes a suppression",
    "a human reviews the rendered email with a screen reader or equivalent",
]


class InputError(Exception):
    """Invalid input; the CLI reports it and exits 2."""


# ---------- parsing and validation ----------

def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise InputError(msg)


def _is_str(v: Any) -> bool:
    return isinstance(v, str)


def parse_time(value: Any, what: str) -> datetime:
    _need(_is_str(value), "%s must be an ISO 8601 UTC string" % what)
    try:
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise InputError("%s is not a valid ISO 8601 timestamp: %r" % (what, value))
    _need(dt.tzinfo is not None, "%s needs a timezone, for example Z" % what)
    return dt.astimezone(timezone.utc)


def load_json(path: str, what: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise InputError("cannot read %s file %s: %s" % (what, path, exc.strerror))
    except ValueError as exc:
        raise InputError("%s file is not valid JSON: %s" % (what, exc))
    _need(isinstance(data, dict), "%s file must hold a JSON object" % what)
    return data


def check_schema(data: Dict[str, Any], tag: str, what: str) -> None:
    _need(data.get("schema") == tag, "%s needs schema %r, got %r" % (what, tag, data.get("schema")))


def validate_campaign(c: Dict[str, Any]) -> None:
    check_schema(c, "email-campaign.v1", "campaign")
    for key in ("campaign_id", "tenant_id", "from_domain", "subject"):
        _need(_is_str(c.get(key)) and c[key].strip() != "", "campaign.%s must be a non-empty string" % key)
    _need(c.get("kind") in ("marketing", "transactional"), "campaign.kind must be marketing or transactional")
    content = c.get("content")
    _need(isinstance(content, dict), "campaign.content must be an object")
    for key in ("html", "text", "lang"):
        _need(_is_str(content.get(key)), "campaign.content.%s must be a string" % key)
    headers = c.get("headers")
    _need(isinstance(headers, dict) and all(_is_str(k) and _is_str(v) for k, v in headers.items()),
          "campaign.headers must be an object of strings")
    aud = c.get("audience")
    _need(isinstance(aud, list) and all(_is_str(a) for a in aud), "campaign.audience must be a list of contact ids")


def validate_ledger(ledger: Dict[str, Any]) -> None:
    check_schema(ledger, "consent-ledger.v1", "ledger")
    _need(_is_str(ledger.get("tenant_id")) and ledger["tenant_id"], "ledger.tenant_id must be a non-empty string")
    contacts = ledger.get("contacts")
    _need(isinstance(contacts, list), "ledger.contacts must be a list")
    for i, ct in enumerate(contacts):
        _need(isinstance(ct, dict), "ledger.contacts[%d] must be an object" % i)
        for key in ("id", "email", "tenant_id"):
            _need(_is_str(ct.get(key)) and ct[key].strip() != "", "ledger.contacts[%d].%s must be a non-empty string" % (i, key))
        perm = ct.get("permission")
        _need(isinstance(perm, dict) and perm.get("marketing") in PERMISSIONS,
              "ledger.contacts[%d].permission.marketing must be one of %s" % (i, ", ".join(PERMISSIONS)))
    sups = ledger.get("suppressions")
    _need(isinstance(sups, list), "ledger.suppressions must be a list")
    for i, s in enumerate(sups):
        _need(isinstance(s, dict) and _is_str(s.get("email")) and s["email"].strip() != "",
              "ledger.suppressions[%d].email must be a non-empty string" % i)
        _need(s.get("reason") in SUPPRESSION_REASONS,
              "ledger.suppressions[%d].reason must be one of %s" % (i, ", ".join(SUPPRESSION_REASONS)))


def validate_sender_auth(a: Dict[str, Any]) -> None:
    check_schema(a, "sender-auth.v1", "sender-auth")
    _need(_is_str(a.get("domain")) and a["domain"], "sender-auth.domain must be a non-empty string")
    for key in ("spf", "dmarc"):
        _need(a.get(key) is None or _is_str(a.get(key)), "sender-auth.%s must be a string or null" % key)
    dkim = a.get("dkim")
    _need(isinstance(dkim, list) and all(
        isinstance(d, dict) and _is_str(d.get("selector")) and isinstance(d.get("present"), bool) for d in dkim),
        "sender-auth.dkim must be a list of {selector, present}")


def validate_authorization(z: Dict[str, Any]) -> None:
    if z.get("schema") == "send-authorization.v1":
        raise InputError("authorization: send-authorization.v1 bound only the content; re-approve with send-authorization.v2 "
                         "and the approval_sha256 this gate prints")
    check_schema(z, "send-authorization.v2", "authorization")
    for key in ("campaign_id", "approval_sha256", "approved_by", "approved_at", "expires_at"):
        _need(_is_str(z.get(key)) and z[key] != "", "authorization.%s must be a non-empty string" % key)
    parse_time(z["approved_at"], "authorization.approved_at")
    parse_time(z["expires_at"], "authorization.expires_at")


# ---------- rules (pure) ----------

def norm_email(email: str) -> str:
    """Mailbox key for suppression and dedupe: trimmed, lowercased, trailing dots off the domain, and any
    +tag off the local part. A suppression on any variant of a mailbox suppresses every variant. Provider
    rules beyond +tags (Gmail dot-insensitivity, other separators) are not applied."""
    local, at, domain = email.strip().lower().rpartition("@")
    if not at:
        return email.strip().lower()
    return "%s@%s" % (local.split("+", 1)[0], domain.rstrip("."))


def defect(code: str, severity: str, message: str, location: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "message": message, "location": location}


APPROVAL_FIELDS = ("campaign_id", "tenant_id", "kind", "from_domain", "subject", "headers", "content")


def approval_sha256(campaign: Dict[str, Any], recipients: List[str]) -> str:
    """What a human approves: every campaign field that changes who receives what, plus the resolved
    recipient mailboxes. Changing any of them after approval invalidates the authorization."""
    bound = {k: campaign[k] for k in APPROVAL_FIELDS}
    bound["recipients"] = sorted(recipients)
    blob = json.dumps(bound, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def select_audience(campaign: Dict[str, Any], ledger: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, str]], List[Dict[str, str]]]:
    """Return (eligible ids, excluded, defects). Suppression always wins."""
    kind = campaign["kind"]
    by_id = {ct["id"]: ct for ct in ledger["contacts"]}
    suppressed: Dict[str, List[str]] = {}
    for s in ledger["suppressions"]:
        suppressed.setdefault(norm_email(s["email"]), []).append(s["reason"])
    eligible: List[str] = []
    excluded: List[Dict[str, str]] = []
    defects: List[Dict[str, str]] = []
    sent_to = set()
    ledger_foreign = ledger["tenant_id"] != campaign["tenant_id"]
    if ledger_foreign:
        defects.append(defect("tenant-mismatch", "error",
                              "ledger tenant %s differs from campaign tenant %s" % (ledger["tenant_id"], campaign["tenant_id"]),
                              "ledger.tenant_id"))
    for cid in campaign["audience"]:
        ct = by_id.get(cid)
        if ct is None:
            excluded.append({"id": cid, "reason": "contact-not-in-ledger"})
            defects.append(defect("contact-not-in-ledger", "error", "audience id %s is not in the ledger" % cid, "audience:" + cid))
            continue
        if ledger_foreign or ct["tenant_id"] != campaign["tenant_id"]:
            excluded.append({"id": cid, "reason": "tenant-mismatch"})
            if not ledger_foreign:
                defects.append(defect("tenant-mismatch", "error",
                                      "contact %s belongs to tenant %s, not %s" % (cid, ct["tenant_id"], campaign["tenant_id"]),
                                      "audience:" + cid))
            continue
        email = norm_email(ct["email"])
        reasons = suppressed.get(email, [])
        blocking = [r for r in reasons if kind == "marketing" or r in ALWAYS_BLOCKING]
        if blocking:
            excluded.append({"id": cid, "reason": "suppressed:" + blocking[0]})
            continue
        if kind == "marketing":
            perm = ct["permission"]
            if perm["marketing"] != "opted-in":
                excluded.append({"id": cid, "reason": "permission-" + perm["marketing"]})
                continue
            if not perm.get("source") or not perm.get("at"):
                excluded.append({"id": cid, "reason": "permission-incomplete"})
                continue
        if email in sent_to:
            excluded.append({"id": cid, "reason": "duplicate-address"})
            continue
        sent_to.add(email)
        eligible.append(cid)
    return eligible, excluded, defects


def check_sender_auth(campaign: Dict[str, Any], auth: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if auth["domain"].strip().lower() != campaign["from_domain"].strip().lower():
        out.append(defect("sender-auth-domain-mismatch", "error",
                          "sender-auth is for %s but the campaign sends from %s" % (auth["domain"], campaign["from_domain"]),
                          "sender-auth.domain"))
    spf = (auth.get("spf") or "").strip().lower()
    if not spf.startswith("v=spf1"):
        out.append(defect("sender-auth-missing", "error", "no SPF record (v=spf1 ...)", "sender-auth.spf"))
    if not any(d["present"] for d in auth["dkim"]):
        out.append(defect("sender-auth-missing", "error", "no DKIM selector is present", "sender-auth.dkim"))
    dmarc = (auth.get("dmarc") or "").strip()
    if not dmarc.lower().startswith("v=dmarc1"):
        out.append(defect("sender-auth-missing", "error", "no DMARC record (v=DMARC1; ...)", "sender-auth.dmarc"))
    else:
        tags = {}
        for part in dmarc.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                tags[k.strip().lower()] = v.strip().lower()
        if tags.get("p") == "none":
            out.append(defect("dmarc-policy-none", "warning", "DMARC policy is p=none, which monitors but does not enforce", "sender-auth.dmarc"))
    return out


def check_unsubscribe(campaign: Dict[str, Any]) -> List[Dict[str, str]]:
    if campaign["kind"] != "marketing":
        return []
    headers = {k.strip().lower(): v for k, v in campaign["headers"].items()}
    out: List[Dict[str, str]] = []
    lu = headers.get("list-unsubscribe", "")
    uris = [p.strip().strip("<>").strip() for p in lu.split(",") if p.strip()]
    if not any(u.lower().startswith("https://") for u in uris):
        out.append(defect("one-click-unsubscribe-missing", "error",
                          "List-Unsubscribe needs an https URI (RFC 8058)", "headers.List-Unsubscribe"))
    if headers.get("list-unsubscribe-post", "") != ONE_CLICK:
        out.append(defect("one-click-unsubscribe-missing", "error",
                          'List-Unsubscribe-Post must be exactly "%s" (RFC 8058)' % ONE_CLICK, "headers.List-Unsubscribe-Post"))
    return out


class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.imgs: List[Dict[str, Optional[str]]] = []
        self.text = ""
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        a = dict(attrs)
        if tag == "html":
            self.html_lang = (a.get("lang") or "").strip()
        elif tag == "img":
            self.imgs.append(a)
        elif tag in ("script", "style", "title"):
            self._skip += 1

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "title") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.text += data


def check_accessibility(campaign: Dict[str, Any]) -> List[Dict[str, str]]:
    content = campaign["content"]
    scan = _Scan()
    scan.feed(content["html"])
    scan.close()
    out: List[Dict[str, str]] = []
    if not content["text"].strip():
        out.append(defect("a11y-text-part-missing", "error", "no plain-text part", "content.text"))
    if not scan.html_lang and not content["lang"].strip():
        out.append(defect("a11y-lang-missing", "error", "no lang on <html> and no content.lang", "content.lang"))
    for i, img in enumerate(scan.imgs):
        if "alt" not in img:
            out.append(defect("a11y-img-alt-missing", "error",
                              "img #%d has no alt attribute (WCAG 2.2 SC 1.1.1)" % (i + 1), "content.html:img[%d]" % i))
    if scan.imgs and not scan.text.strip():
        out.append(defect("a11y-image-only", "error", "html has images and no text", "content.html"))
    return out


def check_authorization(campaign: Dict[str, Any], z: Optional[Dict[str, Any]], now: datetime,
                        approval: str) -> Tuple[bool, List[Dict[str, str]]]:
    if z is None:
        return False, []
    reasons: List[str] = []
    if not z["approved_by"].startswith("human:") or z["approved_by"] == "human:":
        reasons.append("approved_by must start with human: and name a person")
    if z["campaign_id"] != campaign["campaign_id"]:
        reasons.append("authorization is for campaign %s, not %s" % (z["campaign_id"], campaign["campaign_id"]))
    if z["approval_sha256"] != approval:
        reasons.append("approval_sha256 does not match; kind, sender, subject, headers, content or recipients changed after approval")
    if not now < parse_time(z["expires_at"], "authorization.expires_at"):
        reasons.append("authorization expired at %s" % z["expires_at"])
    return (not reasons), [defect("authorization-invalid", "error", r, "authorization") for r in reasons]


def run_gate(campaign: Dict[str, Any], ledger: Dict[str, Any], auth: Dict[str, Any],
             z: Optional[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    eligible, excluded, defects = select_audience(campaign, ledger)
    defects += check_sender_auth(campaign, auth)
    defects += check_unsubscribe(campaign)
    defects += check_accessibility(campaign)
    by_id = {ct["id"]: ct for ct in ledger["contacts"]}
    approval = approval_sha256(campaign, [norm_email(by_id[cid]["email"]) for cid in eligible])
    z_ok, z_defects = check_authorization(campaign, z, now, approval)
    defects += z_defects
    has_error = any(d["severity"] == "error" for d in defects)
    return {
        "campaign_id": campaign["campaign_id"],
        "mode": "staged",
        "eligible": eligible,
        "excluded": excluded,
        "defects": defects,
        "approval_sha256": approval,
        "authorized_for_dispatch": bool(z_ok and not has_error),
        "sends_performed": 0,
        "dispatch_route": DISPATCH_ROUTE,
        "human_review_required": HUMAN_REVIEW,
        "not_checked": NOT_CHECKED,
    }


# ---------- CLI ----------

class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise InputError("usage: " + message)


def main(argv: Optional[List[str]] = None) -> int:
    p = _Parser(description="Pre-send gate. Stages a send; never sends.")
    p.add_argument("--campaign", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--sender-auth", required=True, dest="sender_auth")
    p.add_argument("--now", required=True)
    p.add_argument("--authorization")
    try:
        args = p.parse_args(argv)
        now = parse_time(args.now, "--now")
        campaign = load_json(args.campaign, "campaign")
        validate_campaign(campaign)
        ledger = load_json(args.ledger, "ledger")
        validate_ledger(ledger)
        auth = load_json(args.sender_auth, "sender-auth")
        validate_sender_auth(auth)
        z = None
        if args.authorization:
            z = load_json(args.authorization, "authorization")
            validate_authorization(z)
        result = run_gate(campaign, ledger, auth, z, now)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if any(d["severity"] == "error" for d in result["defects"]) else 0


if __name__ == "__main__":
    sys.exit(main())
