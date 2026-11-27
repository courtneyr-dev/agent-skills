#!/usr/bin/env python3
"""dns_cert: check DNS zones and TLS certificates through their lifecycle.

  zone-check    --zone ZONE.json [--changes CHANGES.json --now ISO]

The CA that CAA must permit comes only from the owner file issuer-policy.json, and the released hosts
the dangling check uses come only from the owner file decommissioned.json, both at fixed paths in the
fleet's dns-cert fixtures, never from the zone or a flag. --issuer is refused, and --decommissioned is
refused by name unless it names the owner's own file. Names are compared case-folded, trailing dot
dropped and IDNA-encoded, so a U-label and its punycode are one name; an IPv4-mapped IPv6 address is its
IPv4 address.
  cert-check    --cert PEM --host NAME --now ISO [--warn-days 30] [--parser auto|ssl|openssl]
  renewal-plan  --inventory CERTS.json --now ISO [--warn-days 30]

Stdout is JSON. Exit 0 ok, 1 a violation or a non-valid certificate, 2 invalid input, 3 blocked by a
missing capability. Python 3.9+ standard library only. The script reads local files and never opens a
network connection.
"""
from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import os
import re
import ssl
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

TTL_LIMIT = 300
TTL_MAX = 2 ** 31 - 1
CHANGE_WINDOW_HOURS = 48
DNSSEC_TYPES = {"RRSIG", "NSEC", "NSEC3"}
ALIAS_TYPES = {"CNAME", "ALIAS"}
TARGET_TYPES = ALIAS_TYPES | {"MX", "NS"}
KNOWN_TYPES = TARGET_TYPES | DNSSEC_TYPES | {"A", "AAAA", "TXT", "CAA", "SRV", "PTR", "SOA", "DS", "DNSKEY",
                                             "NSEC3PARAM", "TLSA", "HTTPS", "SVCB", "SSHFP", "NAPTR"}
HERE = os.path.dirname(os.path.abspath(__file__))
OWNER_FILES = os.path.normpath(os.path.join(HERE, "..", "..", "company-fleets", "fleets", "hosting", "fixtures", "dns-cert"))
ISSUER_POLICY = os.path.join(OWNER_FILES, "issuer-policy.json")
DECOMMISSIONED = os.path.join(OWNER_FILES, "decommissioned.json")


class InputError(Exception):
    """Invalid input; exit 2."""


class Refused(Exception):
    """A named refusal; exit 1."""

    def __init__(self, refusal: str, detail: str) -> None:
        super().__init__(detail)
        self.payload = {"verdict": "refused", "refusal": refusal, "detail": detail}


def ascii_name(name: str) -> str:
    """One spelling per name: case-folded, trailing dot dropped, each non-ASCII label IDNA-encoded (punycode)."""
    n = name.strip().lower().rstrip(".")
    if n.isascii():
        return n
    try:
        return ".".join(label.encode("idna").decode("ascii") if not label.isascii() else label for label in n.split("."))
    except UnicodeError:
        raise InputError("%r is not a valid internationalized domain name" % name)


class Blocked(Exception):
    """A required capability is missing; exit 3."""


def parse_now(text: str) -> datetime.datetime:
    try:
        value = datetime.datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise InputError("not an ISO 8601 timestamp: %r" % text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def load_json(path: str, what: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise InputError("%s file not found: %s" % (what, path))
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InputError("%s is not valid JSON: %s" % (what, exc))
    if not isinstance(doc, dict):
        raise InputError("%s must be a JSON object" % what)
    return doc


def need(doc: Dict[str, Any], key: str, kind: type, where: str) -> Any:
    value = doc.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) or (kind is str and not value.strip()):
        raise InputError("%s needs %r as %s" % (where, key, kind.__name__))
    return value


def fqdn(name: str, origin: str) -> str:
    """'@' is the origin and a trailing dot is absolute. A name that already equals or ends with the
    origin is read as absolute too (BIND would append the origin again); anything else is relative."""
    n = name.strip().lower()
    if n in ("", "@"):
        return origin
    if n.endswith("."):
        return ascii_name(n)
    n = ascii_name(n)
    if n == origin or n.endswith("." + origin):
        return n
    return n + "." + origin


def target_names(value: str, origin: str) -> List[str]:
    """Every name a target can mean. An undotted multi-label target outside the origin is ambiguous:
    BIND reads it as relative, a person usually means absolute, so both readings are checked."""
    n = value.strip().lower()
    if n.endswith(".") or n in ("", "@") or "." not in n:
        return [fqdn(n, origin)]
    n = ascii_name(n)
    if n == origin or n.endswith("." + origin):
        return [n]
    return [n, n + "." + origin]


def in_zone(name: str, origin: str) -> bool:
    return name == origin or name.endswith("." + origin)


# ---------------------------------------------------------------- zone-check

def load_zone(path: str) -> Dict[str, Any]:
    zone = load_json(path, "zone")
    origin = ascii_name(need(zone, "origin", str, "zone"))
    records = need(zone, "records", list, "zone")
    norm = []
    for i, rec in enumerate(records):
        where = "records[%d]" % i
        if not isinstance(rec, dict):
            raise InputError("%s must be an object" % where)
        name = need(rec, "name", str, where)
        rtype = need(rec, "type", str, where).strip().upper()
        ttl = need(rec, "ttl", int, where)
        value = need(rec, "value", str, where)
        if rtype not in KNOWN_TYPES:
            raise InputError("%s has unknown record type %r" % (where, rtype))
        if ttl < 0 or ttl > TTL_MAX:
            raise InputError("%s ttl must be 0 to %d (RFC 2181 section 8)" % (where, TTL_MAX))
        entry = {"name": fqdn(name, origin), "type": rtype, "ttl": ttl, "value": value.strip(),
                 "relative_name": name.strip()}
        if rtype == "MX":
            parts = entry["value"].split()
            if len(parts) != 2 or not parts[0].isdigit():
                raise InputError("%s MX value must be '<preference> <host>'" % where)
            entry["targets"] = target_names(parts[1], origin)
        elif rtype in TARGET_TYPES:
            entry["targets"] = target_names(entry["value"], origin)
        elif rtype in ("A", "AAAA"):
            try:
                entry["address"] = ipaddress.ip_address(entry["value"])
            except ValueError:
                raise InputError("%s %s value is not an IP address: %r" % (where, rtype, entry["value"]))
        elif rtype == "CAA":
            m = re.match(r'^(\d+)\s+([A-Za-z0-9]+)\s+"?([^"]*)"?$', entry["value"])
            if not m:
                raise InputError('%s CAA value must be \'<flags> <tag> "<value>"\'' % where)
            entry["caa_tag"] = m.group(2).lower()
            entry["caa_value"] = m.group(3).strip().lower()
        norm.append(entry)
    issuer = ascii_name(need(load_json(ISSUER_POLICY, "issuer policy"), "issuer", str, "issuer policy"))
    claimed = zone.get("issuer")
    notes = []
    if claimed is not None and str(claimed).strip().lower().rstrip(".") != issuer:
        notes.append({"rule": "zone-issuer-ignored", "name": origin,
                      "detail": "the zone names issuer %r; CAA is checked against the owner's issuer %r" % (claimed, issuer)})
    return {"origin": origin, "records": norm, "issuer": issuer, "notes": notes}


def load_hosts(named: Optional[str]) -> List[str]:
    """The owner's list of released hosts and addresses, at its fixed path."""
    if named and os.path.realpath(named) != os.path.realpath(DECOMMISSIONED):
        raise Refused("decommissioned-not-owner-file", "released hosts come only from the owner's %s; the caller-named %s is "
                      "refused" % (DECOMMISSIONED, named))
    doc = load_json(DECOMMISSIONED, "decommissioned list")
    hosts = need(doc, "hosts", list, "decommissioned list")
    if not all(isinstance(h, str) and h.strip() for h in hosts):
        raise InputError("decommissioned list 'hosts' must hold non-empty strings")
    return [ascii_name(h) for h in hosts]


def host_matches(target: str, host: str) -> bool:
    return target == host or target.endswith("." + host)


def plain_address(address: Any) -> Any:
    """An IPv4-mapped IPv6 address (::ffff:a.b.c.d) is the IPv4 address it carries."""
    mapped = getattr(address, "ipv4_mapped", None)
    return mapped if mapped is not None else address


def same_address(address: Any, host: str) -> bool:
    try:
        return plain_address(address) == plain_address(ipaddress.ip_address(host))
    except ValueError:
        return False


def load_changes(path: str, origin: str) -> List[Dict[str, Any]]:
    doc = load_json(path, "changes")
    out = []
    for i, ch in enumerate(need(doc, "changes", list, "changes")):
        where = "changes[%d]" % i
        if not isinstance(ch, dict):
            raise InputError("%s must be an object" % where)
        rtype = need(ch, "type", str, where).strip().upper()
        if rtype not in KNOWN_TYPES:
            raise InputError("%s has unknown record type %r" % (where, ch["type"]))
        out.append({"name": fqdn(need(ch, "name", str, where), origin), "type": rtype,
                    "at": parse_now(need(ch, "at", str, where))})
    return out


def zone_check(zone: Dict[str, Any], hosts: List[str], changes: Optional[List[Dict[str, Any]]],
               now: Optional[datetime.datetime]) -> Dict[str, Any]:
    origin, records = zone["origin"], zone["records"]
    violations: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = list(zone.get("notes", []))
    assumptions = [
        "Targets are resolved inside the zone only; an MX, NS or CNAME target in another zone is not followed.",
        "Released hosts come from the owner's decommissioned.json and the CAA issuer from its issuer-policy.json, both at "
        "fixed paths; a process running as the same OS user can rewrite those files, which only separate OS accounts or "
        "signed records stop.",
        "An undotted target such as 'host.example' is checked both as written and with the origin appended.",
        "The TTL rule is a local policy (TTL at or below %d seconds when a change is due within %d hours), "
        "not an RFC requirement." % (TTL_LIMIT, CHANGE_WINDOW_HOURS),
        "CAA is checked per name that carries a CAA set; issuewild and critical-flag handling are not modeled.",
    ]

    def add(rule: str, name: str, detail: str, ref: str) -> None:
        violations.append({"rule": rule, "name": name, "detail": detail, "ref": ref})

    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        by_name.setdefault(rec["name"], []).append(rec)
        rel = rec["relative_name"].lower()
        if not rel.endswith(".") and in_zone(rel, origin):
            warnings.append({"rule": "name-contains-origin", "name": rec["name"],
                             "detail": "name %r has no trailing dot but already ends with the origin; read as %s" % (rec["relative_name"], rec["name"])})
        if len(rec.get("targets", [])) > 1:
            warnings.append({"rule": "target-without-trailing-dot", "name": rec["name"],
                             "detail": "%s target %r has no trailing dot; checked as %s" % (rec["type"], rec["value"], " and ".join(rec["targets"]))})
        if rec["type"] == "ALIAS":
            warnings.append({"rule": "alias-is-provider-specific", "name": rec["name"],
                             "detail": "ALIAS (apex flattening) is a provider feature, not an RFC record type"})

    # CNAME rules.
    for name, recs in sorted(by_name.items()):
        cnames = [r for r in recs if r["type"] == "CNAME"]
        if not cnames:
            continue
        if name == origin:
            add("apex-cname", name, "a CNAME at the zone apex cannot coexist with the SOA and NS records",
                "RFC 1034 section 3.6.2; RFC 2181 section 10.1")
        others = [r for r in recs if r["type"] != "CNAME" and r["type"] not in DNSSEC_TYPES]
        if len(cnames) > 1:
            add("cname-conflict", name, "%d CNAME records at one name; only one is allowed" % len(cnames),
                "RFC 1034 section 3.6.2")
        if others:
            add("cname-conflict", name, "CNAME shares its name with %s" % ", ".join(sorted({r["type"] for r in others})),
                "RFC 1034 section 3.6.2; RFC 2181 section 10.1")

    # MX target must not be an alias.
    for rec in records:
        if rec["type"] == "MX":
            for target in rec["targets"]:
                if any(r["type"] == "CNAME" for r in by_name.get(target, [])):
                    add("mx-target-cname", rec["name"], "MX target %s is a CNAME alias" % target,
                        "RFC 2181 section 10.3")

    # In-zone targets must exist.
    for rec in records:
        for target in rec.get("targets", []):
            if len(rec["targets"]) == 1 and in_zone(target, origin) and target not in by_name \
                    and "*." + target.split(".", 1)[-1] not in by_name:
                add("missing-target", rec["name"], "%s target %s has no records in this zone" % (rec["type"], target),
                    "RFC 1034 section 3.6.2")

    # Dangling aliases, against the owner's list of released hosts.
    for rec in records:
        hit = next((h for h in hosts if any(host_matches(t, h) for t in rec.get("targets", []))
                    or ("address" in rec and same_address(rec["address"], h))), None)
        if hit:
            add("dangling-record", rec["name"],
                "%s points at decommissioned host %s; whoever holds that name or address next can serve or "
                "receive this zone's traffic" % (rec["type"], hit), "subdomain takeover risk")

    # SPF.
    for name, recs in sorted(by_name.items()):
        spf = [r for r in recs if r["type"] == "TXT" and r["value"].strip('"').lower().startswith("v=spf1")]
        if len(spf) > 1:
            add("multiple-spf", name, "%d SPF records; receivers return permerror" % len(spf), "RFC 7208 section 3.2")

    # CAA.
    for name, recs in sorted(by_name.items()):
        issue = [r for r in recs if r["type"] == "CAA" and r["caa_tag"] == "issue"]
        if not issue:
            continue
        allowed = {r["caa_value"].split(";")[0].strip().rstrip(".") for r in issue}
        if zone["issuer"] not in allowed:
            add("caa-blocks-issuer", name, "CAA issue set %s does not permit %s" % (sorted(allowed), zone["issuer"]),
                "RFC 8659 section 4")

    # TTL before a scheduled change.
    if changes:
        for ch in changes:
            hours = (ch["at"] - now).total_seconds() / 3600.0
            if hours < 0 or hours > CHANGE_WINDOW_HOURS:
                continue
            # A CNAME replaces every other type at its name, so an A-to-CNAME cutover waits on the A TTL.
            current = [r for r in by_name.get(ch["name"], []) if r["type"] not in DNSSEC_TYPES and (
                r["type"] == ch["type"] or r["type"] in ALIAS_TYPES or ch["type"] in ALIAS_TYPES)]
            high = [r for r in current if r["ttl"] > TTL_LIMIT]
            if high:
                add("ttl-before-change", ch["name"],
                    "%s change due in %.1f hours but TTL is %d seconds; resolvers keep the old answer up to that long"
                    % (ch["type"], hours, max(r["ttl"] for r in high)), "local policy: TTL <= %d within %d hours" % (TTL_LIMIT, CHANGE_WINDOW_HOURS))

    violations.sort(key=lambda v: (v["rule"], v["name"]))
    return {"verdict": "fail" if violations else "pass", "origin": origin, "record_count": len(records),
            "violations": violations, "warnings": warnings, "assumptions": assumptions}


# ---------------------------------------------------------------- cert-check

def _read_pem(path: str) -> None:
    if not os.path.isfile(path):
        raise InputError("certificate file not found: %s" % path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if "PRIVATE KEY" in text:
        raise InputError("file contains a private key; refusing to read it")
    if "-----BEGIN CERTIFICATE-----" not in text:
        raise InputError("not a PEM certificate: no BEGIN CERTIFICATE block")


def _decode_ssl(path: str) -> Dict[str, Any]:
    decode = getattr(getattr(ssl, "_ssl", None), "_test_decode_cert", None)
    if decode is None:
        raise Blocked("ssl._ssl._test_decode_cert is missing")
    try:
        info = decode(path)
    except (ssl.SSLError, ValueError, OSError) as exc:
        raise InputError("invalid PEM certificate: %s" % exc)
    return {"not_before": ssl.cert_time_to_seconds(info["notBefore"]),
            "not_after": ssl.cert_time_to_seconds(info["notAfter"]),
            "sans": [v for k, v in info.get("subjectAltName", ()) if k == "DNS"]}


def _decode_openssl(path: str) -> Dict[str, Any]:
    try:
        proc = subprocess.run(["openssl", "x509", "-in", path, "-noout", "-startdate", "-enddate",
                               "-ext", "subjectAltName"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise Blocked("the openssl CLI is not available")
    if proc.returncode != 0:
        raise InputError("invalid PEM certificate: openssl exited %d" % proc.returncode)
    start = re.search(r"notBefore=(.+)", proc.stdout)
    end = re.search(r"notAfter=(.+)", proc.stdout)
    if not (start and end):
        raise InputError("openssl output has no validity dates")
    return {"not_before": ssl.cert_time_to_seconds(start.group(1).strip()),
            "not_after": ssl.cert_time_to_seconds(end.group(1).strip()),
            "sans": re.findall(r"DNS:([^,\s]+)", proc.stdout)}


def decode_cert(path: str, parser: str) -> Tuple[Dict[str, Any], str]:
    _read_pem(path)
    if parser in ("auto", "ssl"):
        try:
            return _decode_ssl(path), "ssl._ssl._test_decode_cert"
        except Blocked:
            if parser == "ssl":
                raise
    return _decode_openssl(path), "openssl x509"


def name_matches(host: str, san: str) -> bool:
    """Exact match, or a wildcard that is a whole leftmost label and covers exactly one label. A wildcard
    needs at least two labels after '*.' ('*.example' matches nothing); no public suffix list is loaded."""
    host, san = host.lower().rstrip("."), san.lower().rstrip(".")
    if host == san:
        return True
    if not san.startswith("*.") or "*" in host or "*" in san[2:] or "." not in san[2:]:
        return False
    labels = host.split(".")
    return len(labels) >= 2 and all(labels) and ".".join(labels[1:]) == san[2:]


def utc(epoch: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)


def cert_check(cert: str, host: str, now: datetime.datetime, warn_days: float, parser: str) -> Dict[str, Any]:
    info, ran = decode_cert(cert, parser)
    not_before, not_after = utc(info["not_before"]), utc(info["not_after"])
    days_left = (not_after - now).total_seconds() / 86400.0
    problems = []
    if not any(name_matches(host, san) for san in info["sans"]):
        problems.append("name-mismatch")
    if now >= not_after:
        problems.append("expired")
    elif now < not_before:
        problems.append("not-yet-valid")
    elif days_left <= warn_days:
        problems.append("renew")
    status = problems[0] if problems else "valid"
    return {"status": status, "problems": problems, "host": host, "sans": info["sans"],
            "not_before": not_before.isoformat(), "not_after": not_after.isoformat(),
            "days_left": round(days_left, 4), "warn_days": warn_days, "parser": ran,
            "assumptions": ["Only DNS subject alternative names are matched; the subject CN is ignored (RFC 9525 dropped CN-ID).",
                            "A wildcard must be the whole leftmost label and covers exactly one label (RFC 6125 section 6.4.3).",
                            "Self-signed or private-CA chains are not validated; this checks name and dates only.",
                            "renew means days left is at or below warn-days."]}


# ------------------------------------------------------------- renewal-plan

def renewal_plan(path: str, now: datetime.datetime, warn_days: float) -> Dict[str, Any]:
    doc = load_json(path, "inventory")
    due, ok = [], 0
    for i, c in enumerate(need(doc, "certificates", list, "inventory")):
        where = "certificates[%d]" % i
        if not isinstance(c, dict):
            raise InputError("%s must be an object" % where)
        ident, host = need(c, "id", str, where), need(c, "host", str, where)
        owner, expires = need(c, "owner_role", str, where), parse_now(need(c, "not_after", str, where))
        days_left = (expires - now).total_seconds() / 86400.0
        if days_left <= 0:
            status = "expired"
        elif days_left <= warn_days:
            status = "renew"
        else:
            ok += 1
            continue
        due.append({"id": ident, "host": host, "owner_role": owner, "not_after": expires.isoformat(),
                    "days_left": round(days_left, 4), "status": status})
    due.sort(key=lambda d: (d["days_left"], d["id"]))
    expired = sum(1 for d in due if d["status"] == "expired")
    return {"verdict": "expired" if expired else "renew" if due else "ok", "due": due, "expired_count": expired,
            "ok_count": ok, "warn_days": warn_days, "now": now.isoformat(),
            "assumptions": ["Expiry dates come from the inventory file, not from the live certificates."]}


# --------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("zone-check")
    z.add_argument("--zone", required=True)
    z.add_argument("--decommissioned", help="refused unless it is the owner's decommissioned.json, which is always read")
    z.add_argument("--changes")
    z.add_argument("--now")
    z.add_argument("--issuer", help="refused: the issuer comes only from the owner's issuer-policy.json")
    c = sub.add_parser("cert-check")
    c.add_argument("--cert", required=True)
    c.add_argument("--host", required=True)
    c.add_argument("--now", required=True)
    c.add_argument("--warn-days", type=float, default=30)
    c.add_argument("--parser", choices=["auto", "ssl", "openssl"], default="auto")
    r = sub.add_parser("renewal-plan")
    r.add_argument("--inventory", required=True)
    r.add_argument("--now", required=True)
    r.add_argument("--warn-days", type=float, default=30)
    return p


def run(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    if args.cmd == "zone-check":
        if args.changes and not args.now:
            raise InputError("--changes needs --now")
        if args.issuer is not None:
            raise Refused("issuer-not-owner-file", "the CA that CAA must permit comes only from the owner's %s; --issuer %r is "
                          "refused" % (ISSUER_POLICY, args.issuer))
        zone = load_zone(args.zone)
        hosts = load_hosts(args.decommissioned)
        changes = load_changes(args.changes, zone["origin"]) if args.changes else None
        result = zone_check(zone, hosts, changes, parse_now(args.now) if args.now else None)
        return result, 0 if result["verdict"] == "pass" else 1
    if args.warn_days < 0:
        raise InputError("--warn-days must be 0 or more")
    now = parse_now(args.now)
    if args.cmd == "cert-check":
        host = args.host.strip().lower().rstrip(".")
        if not host or re.search(r"[\s/]", host):
            raise InputError("--host is not a host name: %r" % args.host)
        result = cert_check(args.cert, host, now, args.warn_days, args.parser)
        return result, 0 if result["status"] == "valid" else 1
    result = renewal_plan(args.inventory, now, args.warn_days)
    return result, 1 if result["expired_count"] else 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    except Refused as exc:
        print(json.dumps(exc.payload, indent=2, sort_keys=True))
        return 1
    except Blocked as exc:
        print(json.dumps({"blocked": str(exc)}, indent=2, sort_keys=True))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
