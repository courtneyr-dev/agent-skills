---
name: hosting-dns-cert-lifecycle
description: "Check DNS zones and TLS certificates for a hosted site through create, change, migrate, renew and decommission: apex CNAMEs, CNAMEs sharing a name, MX pointing at an alias, dangling records left after a host is decommissioned (takeover risk), duplicate SPF, CAA that blocks the issuer, high TTLs before a scheduled cutover, certificate expiry, renewal windows and RFC 6125 wildcard name matching. Use whenever someone plans a DNS cutover or migration, asks whether a domain or certificate is ready, wants a renewal plan, or reports a certificate or DNS error on a hosted site. Reads local files only; it never queries live DNS or changes records."
license: MIT
disable-model-invocation: true
---

# hosting-dns-cert-lifecycle

Deterministic checks for a hosted site's DNS zone and TLS certificates, so a cutover doesn't break the
site and a decommissioned host doesn't leave a record someone else can claim. Every rule cites its RFC
or is labeled as local policy.

## When to use

- Before a DNS cutover, migration or decommission: run `zone-check` with the scheduled changes.
- When a certificate is issued, renewed or reported broken: run `cert-check`.
- For a portfolio view of what expires soon: run `renewal-plan`.

## When not to use

- Live DNS lookups or registrar changes: this skill reads files. A human with registrar access, or a
  provider adapter the network edge engineer owns, makes changes.
- Certificate issuance or ACME automation: out of scope; the platform engineer owns the issuer.
- Data migration: use `hosting-data-migration`. Restores: use `hosting-restore-exercise`.

## Inputs and prerequisites

- A zone as structured JSON (`origin`, `records: [{name, type, ttl, value}]`), not BIND text.
  Optional: scheduled changes JSON and `--now`.
- Two owner files at fixed paths in `company-fleets/fleets/hosting/fixtures/dns-cert/`, read on every
  run: `issuer-policy.json` (the CA that CAA must permit) and `decommissioned.json` (released names and
  IP addresses). `--issuer` is refused (`issuer-not-owner-file`), and `--decommissioned` is refused
  (`decommissioned-not-owner-file`) unless it names the owner's own file. A zone's own `issuer` field
  is ignored and reported as `zone-issuer-ignored`.
- A certificate PEM and the host it must serve. `--now` is required so results don't drift with the
  calendar.
- Python 3.9+. `ssl._ssl._test_decode_cert` parses PEM; the `openssl` CLI is the fallback.

## Method

1. Run `scripts/dns_cert.py zone-check --zone Z [--changes C --now T]`.
2. Fix each violation before the change window. A dangling record (a CNAME, ALIAS, MX, NS, A or AAAA
   pointing at a decommissioned name or address) is a takeover risk: remove it or repoint it before the
   target is released. Names are case-folded, the trailing dot is dropped and non-ASCII labels are
   IDNA-encoded, so `bücher.example` and `xn--bcher-kva.example` are one name. An IPv4-mapped AAAA
   value such as `::ffff:198.51.100.7` matches the released IPv4 address. An undotted target such as
   `host.example` is checked both as written and with the origin appended, and a name that already
   ends with the origin is read as absolute. A change's type is trimmed and case-folded before the TTL
   rule, and an unknown type is invalid input.
3. Run `cert-check --cert P --host H --now T [--warn-days 30]` for every name the site serves.
4. Run `renewal-plan --inventory I --now T` and hand the `due` list to the owner roles it names.
5. Record outputs as evidence in the handoff; a zone or certificate edited afterward needs a new run.

## Stopping conditions

- Every zone the change touches passes, and every served name has a `valid` certificate.
- Or a violation remains: stop the cutover and hand the violation list to the DNS/domain engineer.

## Output contract

JSON on stdout. `zone-check`: `verdict` (`pass` or `fail`), `violations` and `warnings` (each with
`rule`, `name`, `detail`), `assumptions`. `cert-check`: `status` (`valid`, `renew`, `expired`,
`name-mismatch`), `days_left`, `not_after`, `parser`. `renewal-plan`: `due` sorted by days left, each
with `owner_role`.

## Failure states

- Exit 1: a zone violation, a certificate that isn't `valid` (renew, expired, mismatch), or a refusal
  (`issuer-not-owner-file`, `decommissioned-not-owner-file`).
- Exit 2: invalid input (unparseable JSON or PEM, unknown record type, a TTL above 2^31-1, an A or
  AAAA value that isn't an IP address, missing `--now`).
- Exit 3: blocked, neither `ssl._ssl._test_decode_cert` nor the `openssl` CLI is available.
- Limit: a process running as the same OS user can rewrite `issuer-policy.json` or `decommissioned.json`.
  Only separate OS accounts or signed records stop that.

## Adapters and missing capability

No live adapter. A registrar or DNS provider API adapter is not built: no provider is selected for
Fixture Co. Without one, export the zone to the JSON shape above by hand and run the checks; mark any
claim about the live zone unverified.

## References

`references/sources.md` lists the RFCs behind each rule, with versions and rights.

## Tests

```bash
cd ~/.claude/skills/hosting-dns-cert-lifecycle/scripts && python3 -W ignore -m unittest discover -s tests
```

## Evaluation cases

Fleet cases in `company-fleets/fleets/hosting/evals.json`: `hosting.eval.dns-cert-valid-zone`,
`hosting.eval.dns-cert-valid-certificate`, `hosting.eval.dns-cert-dangling-cname`,
`hosting.eval.dns-cert-apex-cname`, `hosting.eval.dns-cert-name-mismatch`,
`hosting.eval.dns-cert-renew-window`, `hosting.eval.dns-cert-ttl-before-change`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.dns-cert-undotted-dangling-cname`, `hosting.eval.dns-cert-dangling-mx-ns-a`, `hosting.eval.dns-cert-a-to-cname-cutover-ttl`, `hosting.eval.dns-cert-zone-cannot-name-its-issuer`.

Cases that replay the hosting re-review's probes: `hosting.eval.dns-cert-issuer-flag-refused`, `-padded-change-type-ttl`, `-dangling-checked-without-a-flag`, `-caller-decommission-list-refused`, `-ipv4-mapped-aaaa-dangling`.
