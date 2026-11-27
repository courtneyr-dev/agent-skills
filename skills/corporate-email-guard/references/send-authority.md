# Send authority and suppression

Source: US Federal Trade Commission, "CAN-SPAM Act: A Compliance Guide for Business"
Location: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
Version or retrieved date: not re-fetched at authoring time (ftc.gov answered a plain curl request with HTTP 403 on 2026-11-25)
Rights: US government work; cited by title and URL, not copied

Source: IETF RFC 2606, "Reserved Top Level DNS Names"
Location: https://www.rfc-editor.org/rfc/rfc2606
Version or retrieved date: RFC 2606 (June 1999), Best Current Practice 32
Rights: IETF Trust; cited, not copied

## What the guard enforces

This is a local policy for the rig. It doesn't establish compliance with CAN-SPAM, GDPR or any other law; the company's counsel and its email platform own that.

- **Suppression wins.** A contact on the suppression list never reaches the staged list or the outbox. The list is an owner value: the contract owner pins it in the campaign's owner ledger (`fleet owner-record --kind pin`, name `suppression-list`), and the guard reads the latest pin, never a file the caller passes. The guard checks twice: at staging and again at send, against the list pinned at send time. The FTC guide says opt-out requests must be honored; checking at send time means an unsubscribe recorded between staging and send still holds.
- **Normalization is conservative.** Trim, drop zero-width characters (U+200B, U+200C, U+200D, U+2060, U+FEFF) and one trailing dot, then lowercase, on contacts and suppression rows alike. A suppression row that still fails the address check exits 2, so a malformed row can't load and suppress nothing. To match suppression, the guard also drops a `+tag` on every domain and, for `gmail.com` and `googlemail.com`, the dots in the local part, so `carol+news@example.com` and `v.ictim@gmail.com` stay suppressed when the list holds `carol@example.com` and `victim@gmail.com`. Other providers' aliases aren't folded.
- **Approval lives in the owner log and binds to hashes.** A named human's approval is recorded by the contract owner (`fleet owner-record --kind send-approval`, write-once), and the guard looks it up by the staged campaign and recipient hashes; an approval file the caller passes counts for nothing. `campaign_sha256` is the SHA-256 of the campaign JSON with sorted keys and compact separators; `recipient_sha256` hashes the sorted recipient list the same way. An approval for an earlier draft or a different list doesn't match, so it can't release this send.
- **Only a named human approves.** `approved_by` must start with `human:`. An agent role id is refused, which keeps the producer of a campaign from accepting its own send.
- **The transport is fake.** Messages land as JSON files in a local directory named by `sha256(campaign_sha256 + ":" + email)`, and `os.link` refuses an existing name, so a retry never writes a second copy. No SMTP client or provider API exists in the script.

## Why fixtures use example domains

RFC 2606 reserves `example.com`, `example.org` and `example.net` for documentation, so fixture addresses can't belong to a real mailbox.
