SYNTHETIC FIXTURE: Fixture Co DNS zones and self-signed certificates for tenant-a.example (RFC 2606 names). No real domain, issuer or customer.

# DNS and certificate fixtures

The three certificates are self-signed with fixed validity dates so evaluations pass `--now` and never
drift with the calendar. Their private keys were deleted after signing and are not in the rig.

| File | Subject alternative names | Not after |
|---|---|---|
| `tenant-a-apex.pem` | tenant-a.example, www.tenant-a.example | 2027-01-15 |
| `tenant-a-wildcard.pem` | *.tenant-a.example | 2027-03-01 |
| `tenant-a-other.pem` | mail.tenant-a.example | 2027-03-01 |

To regenerate one, with OpenSSL 3.4 or later (for `-not_before` and `-not_after`):

```bash
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout /tmp/fixture.key \
  -subj "/CN=tenant-a.example" -addext "subjectAltName=DNS:tenant-a.example,DNS:www.tenant-a.example" \
  -not_before 20261001000000Z -not_after 20270115000000Z -out tenant-a-apex.pem
rm /tmp/fixture.key
```

Zones: `zone-valid.json` passes every rule; each other `zone-*.json` breaks the rule in its name.
`changes-www-cutover.json` schedules a www change for 2026-12-01T12:00:00Z; `decommissioned.json`
lists released hosts; `inventory.json` feeds `renewal-plan`. `issuer-policy.json` is the owner's
issuer record: `zone-check` checks CAA against it (or `--issuer`), never against a zone's own `issuer`.
