#!/usr/bin/env python3
"""Send gate for staged email. The only transport is a local fake outbox directory.

  email_guard.py stage --campaign C.json --contacts CONTACTS.csv --out STAGED.json
  email_guard.py send  --staged STAGED.json --outbox DIR

The suppression list and the send approval are owner values: they come only from the owner log of the
campaign's instance (its campaign_id), which company-fleets keeps at fleets/corporate/owner/<campaign_id>.
The contract owner pins the list (`fleet owner-record --kind pin`, name suppression-list) and records a named
human's approval bound to the staged campaign and recipient hashes (`--kind send-approval`). No flag or file
the caller passes supplies either.

Exit 0 = pass, 1 = refused, 2 = usage error or invalid input, 3 = blocked (company-fleets and factory-rig
not found beside this skill). Contact notes and campaign text are data: nothing in them changes a verdict.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FLEET_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "company-fleets", "scripts"))

REASONS = ("unsubscribed", "bounced", "complaint", "do-not-contact", "legal-hold")
CONTACT_HEADER = ["email", "name", "list", "notes"]
SUPPRESSION_HEADER = ["email", "reason", "recorded_on"]
CAMPAIGN_KEYS = ("campaign_id", "subject", "body", "audience", "channel")
TRANSPORT = "fake-outbox"
REFUSE_TRANSPORT = ("no real transport exists in this rig; an external send needs a person holding "
                    "send authority outside it")

LIMITS = [
    "Normalizes emails by trimming, dropping zero-width characters and a trailing dot, and lowercasing. To match suppression it also drops a +tag on any domain and the dots of a gmail.com or googlemail.com local part; other providers' aliases are not folded.",
    "Checks address syntax with one local pattern; it does not check that a mailbox or domain exists.",
    "The suppression list and the approval come only from the owner ledger of the campaign's instance (company-fleets fleets/corporate/owner/<campaign_id>), recorded under the claim token. Not stopped: a same-user process that writes the owner root, reads the owner's token, or claims a campaign id first (company-fleets references/authoring-guide.md, Owner path).",
    "Does not check message content, an unsubscribe mechanism, a postal address or consent records; it enforces a local policy and does not establish legal compliance.",
    "Suppression is as current as the list it reads; a message already in the outbox stays there when a contact is suppressed later.",
]

_EMAIL = re.compile(
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)
_HASH = re.compile(r"^[0-9a-f]{64}$")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- pure functions

def canonical_sha256(obj):
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"))


def normalize_email(raw):
    """Trim, drop zero-width characters and one trailing dot, lowercase. Applied to contacts and suppression alike."""
    addr = raw.translate(ZERO_WIDTH).strip().lower()
    return addr[:-1] if addr.endswith(".") else addr


GMAIL = ("gmail.com", "googlemail.com")


def suppression_key(addr):
    """The mailbox a normalized address reaches, for suppression matching: a +tag dropped on any domain, and for
    Gmail the dots in the local part dropped and googlemail.com read as gmail.com."""
    local, _, domain = addr.rpartition("@")
    local = local.split("+", 1)[0]
    if domain in GMAIL:
        local, domain = local.replace(".", ""), "gmail.com"
    return "%s@%s" % (local, domain)


def valid_email(addr):
    return len(addr) <= 254 and addr.count("@") == 1 and len(addr.split("@")[0]) <= 64 and bool(_EMAIL.match(addr))


def stage_recipients(contacts, suppressed, audience):
    """contacts: list of dicts with email and list; suppressed: set of suppression keys.

    Returns (sorted recipient list, excluded counts). A row is judged in this order: invalid,
    suppressed, other-list, duplicate. Duplicate means the address already became a recipient.
    """
    excluded = {"suppressed": 0, "invalid": 0, "duplicate": 0, "other-list": 0}
    chosen = set()
    for row in contacts:
        addr = normalize_email(row["email"])
        if not valid_email(addr):
            excluded["invalid"] += 1
        elif suppression_key(addr) in suppressed:
            excluded["suppressed"] += 1
        elif row["list"].strip() != audience:
            excluded["other-list"] += 1
        elif addr in chosen:
            excluded["duplicate"] += 1
        else:
            chosen.add(addr)
    return sorted(chosen), excluded


def build_staged(campaign, contacts, suppressed):
    recipients, excluded = stage_recipients(contacts, suppressed, campaign["audience"])
    return {
        "campaign": campaign,
        "campaign_sha256": canonical_sha256(campaign),
        "recipients": recipients,
        "recipient_sha256": canonical_sha256(recipients),
        "excluded": excluded,
        "send_authority": "none",
    }


def message_id(campaign_sha, email):
    return hashlib.sha256((campaign_sha + ":" + email).encode("utf-8")).hexdigest()


def refusal_reason(staged, approval):
    """Return why an approval does not authorize this staged send, or None."""
    if approval is None:
        return "no approval in the campaign's owner log for these campaign and recipient hashes; a named human approves this exact list and the contract owner records it with fleet owner-record --kind send-approval"
    who = approval.get("approved_by")
    if not isinstance(who, str) or not who.startswith("human:") or not who[len("human:"):].strip():
        return "approved_by must be 'human:<title>'; an automated or unnamed approver can't release a send"
    if approval.get("channel") != TRANSPORT or staged["campaign"].get("channel") != TRANSPORT:
        return REFUSE_TRANSPORT
    try:
        datetime.strptime(str(approval.get("approved_on")), "%Y-%m-%d")
    except ValueError:
        return "approval needs approved_on as YYYY-MM-DD"
    if canonical_sha256(staged["campaign"]) != staged.get("campaign_sha256") \
            or canonical_sha256(staged["recipients"]) != staged.get("recipient_sha256"):
        return "staged file does not match its own hashes; stage again and get a new approval"
    if approval.get("campaign_sha256") != staged["campaign_sha256"]:
        return "approval campaign_sha256 differs from the staged campaign"
    if approval.get("recipient_sha256") != staged["recipient_sha256"]:
        return "approval recipient_sha256 differs from the staged recipient list"
    return None


# ---------------------------------------------------------------- boundary readers

def _read_text(path, what):
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError("cannot read %s %s: %s" % (what, path, exc))


def read_json(path, what):
    try:
        return json.loads(_read_text(path, what))
    except json.JSONDecodeError as exc:
        raise InputError("%s is not valid JSON: %s" % (what, exc))


def read_csv(path, header, what):
    return parse_csv(_read_text(path, what), header, what)


def parse_csv(text, header, what):
    """Rows as dicts. Leading '#' comment lines are skipped; the header must match exactly."""
    lines = text.lstrip("\ufeff").splitlines()
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    if not lines:
        raise InputError("%s has no header" % what)
    rows = list(csv.reader(lines))
    if [h.strip() for h in rows[0]] != header:
        raise InputError("%s header must be exactly: %s" % (what, ",".join(header)))
    out = []
    for n, row in enumerate(rows[1:], 2):
        if not row:
            continue
        if len(row) != len(header):
            raise InputError("%s row %d has %d fields, expected %d" % (what, n, len(row), len(header)))
        out.append(dict(zip(header, row)))
    return out


def read_suppression(text):
    """The suppression keys of the owner-pinned list's text. A row that isn't an address stops the run (exit 2)."""
    rows = parse_csv(text, SUPPRESSION_HEADER, "suppression list")
    out = set()
    for n, row in enumerate(rows, 2):
        addr = normalize_email(row["email"])
        if not valid_email(addr):
            raise InputError("suppression list row %d has %r, which is not an email address even after trimming; fix the row so it suppresses the contact it names" % (n, row["email"]))
        if row["reason"].strip() not in REASONS:
            raise InputError("suppression list row %d has reason %r; allowed: %s" % (n, row["reason"], ", ".join(REASONS)))
        try:
            datetime.strptime(row["recorded_on"].strip(), "%Y-%m-%d")
        except ValueError:
            raise InputError("suppression list row %d recorded_on must be YYYY-MM-DD" % n)
        out.add(suppression_key(addr))
    return out


def read_campaign(path):
    camp = read_json(path, "campaign")
    if not isinstance(camp, dict):
        raise InputError("campaign must be a JSON object")
    for key in CAMPAIGN_KEYS:
        if not isinstance(camp.get(key), str) or not camp[key].strip():
            raise InputError("campaign is missing a non-empty '%s'" % key)
    return camp


def read_staged(path):
    staged = read_json(path, "staged file")
    need = ("campaign", "campaign_sha256", "recipients", "recipient_sha256")
    if not isinstance(staged, dict) or any(k not in staged for k in need) \
            or not isinstance(staged["campaign"], dict) or not isinstance(staged["recipients"], list):
        raise InputError("staged file is missing campaign, campaign_sha256, recipients or recipient_sha256")
    return staged


def write_atomic(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def dump(obj):
    return json.dumps(obj, indent=2, sort_keys=True)


# ---------------------------------------------------------------- owner values

def fleet_tools():
    """company-fleets' owner log, or None when it is not beside this skill."""
    if not os.path.isdir(os.path.join(FLEET_SCRIPTS, "fleetlib")):
        return None
    sys.path.insert(0, FLEET_SCRIPTS)
    try:
        from fleetlib import ownerlog
        from fleetlib.registry import Registry
    except ImportError:
        return None
    return {"ownerlog": ownerlog, "registry": Registry()}


class Refused(Exception):
    pass


def owner_entries(fr, campaign):
    """The verified owner log of the campaign's instance; a missing or broken one refuses the run by name."""
    ol = fr["ownerlog"]
    try:
        return ol.read_for("corporate", campaign.get("campaign_id"), {}, fr["registry"])[1]
    except ol.OwnerLogError as exc:
        raise Refused("%s: %s" % (exc.reason, exc.detail))


def pinned_suppression(fr, entries):
    pin = fr["ownerlog"].effective(entries, "pin", "suppression-list")
    if pin is None or not isinstance(pin["body"]["content"], str):
        raise Refused("suppression-not-pinned: the campaign's owner log has no suppression-list pin; the contract owner pins the current list with fleet owner-record --kind pin")
    return read_suppression(pin["body"]["content"])


# ---------------------------------------------------------------- commands

def cmd_stage(args, fr):
    campaign = read_campaign(args.campaign)
    suppressed = pinned_suppression(fr, owner_entries(fr, campaign))
    contacts = read_csv(args.contacts, CONTACT_HEADER, "contacts file")
    staged = build_staged(campaign, contacts, suppressed)
    write_atomic(args.out, dump(staged) + "\n")
    result = dict(staged, ok=True, limits=LIMITS)
    return 0, result


def _result(refused, sent=0, already=0, suppressed_at_send=()):
    return {"ok": refused is None, "sent": sent, "already_sent": already,
            "suppressed_at_send": list(suppressed_at_send), "refused": refused,
            "transport": TRANSPORT, "limits": LIMITS}


def cmd_send(args, fr):
    staged = read_staged(args.staged)
    entries = owner_entries(fr, staged["campaign"])
    suppressed_now = pinned_suppression(fr, entries)
    rec = fr["ownerlog"].effective(entries, "send-approval", "%s:%s" % (staged.get("campaign_sha256"), staged.get("recipient_sha256")))
    approval = dict(rec["body"], owner_log_seq=rec["seq"]) if rec else None
    refused = refusal_reason(staged, approval)
    if refused:
        return 1, _result(refused)

    recipients = sorted({normalize_email(e) for e in staged["recipients"]})
    dropped = [e for e in recipients if suppression_key(e) in suppressed_now]
    to_send = [e for e in recipients if suppression_key(e) not in suppressed_now]

    if os.path.exists(args.outbox) and not os.path.isdir(args.outbox):
        raise InputError("outbox %s exists and is not a directory" % args.outbox)
    os.makedirs(args.outbox, exist_ok=True)
    sent = already = 0
    for email in to_send:
        mid = message_id(staged["campaign_sha256"], email)
        final = os.path.join(args.outbox, mid + ".json")
        message = {
            "approved_by": approval["approved_by"],
            "body": staged["campaign"]["body"],
            "campaign_id": staged["campaign"]["campaign_id"],
            "campaign_sha256": staged["campaign_sha256"],
            "message_id": mid,
            "subject": staged["campaign"]["subject"],
            "to": email,
            "transport": TRANSPORT,
        }
        fd, tmp = tempfile.mkstemp(dir=args.outbox, prefix=".tmp-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(dump(message) + "\n")
            try:
                os.link(tmp, final)  # fails when the message exists, so a rerun writes nothing
                sent += 1
            except FileExistsError:
                already += 1
        finally:
            os.unlink(tmp)
    return 0, _result(None, sent, already, dropped)


def build_parser():
    parser = argparse.ArgumentParser(description="Send gate for staged email (fake outbox only).")
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("stage")
    st.add_argument("--campaign", required=True, help="campaign JSON; its campaign_id names the owner ledger that pins the suppression list")
    st.add_argument("--contacts", required=True)
    st.add_argument("--out", required=True)
    sd = sub.add_parser("send")
    sd.add_argument("--staged", required=True)
    sd.add_argument("--outbox", required=True)
    return parser


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(dump({"error": "usage: email_guard.py stage|send with the required options"}))
            return 2
        raise
    fr = fleet_tools()
    if fr is None:
        print(dump({"ok": False, "status": "blocked", "reason": "company-fleets and factory-rig must sit beside this skill (looked in %s)" % FLEET_SCRIPTS}))
        return 3
    try:
        code, result = cmd_stage(args, fr) if args.command == "stage" else cmd_send(args, fr)
    except InputError as exc:
        print(dump({"error": str(exc)}))
        return 2
    except Refused as exc:
        code, result = 1, _result(str(exc))
    print(dump(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
