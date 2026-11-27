# Sources

Retrieved or confirmed 2026-11-25. Cite these; don't copy their text into the rig.

| Rule | Title | Location | Version | Rights |
|---|---|---|---|---|
| Apex CNAME, CNAME with other data | RFC 1034, Domain names: concepts and facilities, section 3.6.2 | https://www.rfc-editor.org/rfc/rfc1034 | November 1987 | IETF RFC; BCP 78 rights |
| CNAME with other data, MX target not an alias | RFC 2181, Clarifications to the DNS specification, sections 10.1 and 10.3 | https://www.rfc-editor.org/rfc/rfc2181 | July 1997 | IETF RFC; BCP 78 rights |
| One SPF record per name | RFC 7208, Sender Policy Framework, section 3.2 | https://www.rfc-editor.org/rfc/rfc7208 | April 2014 | IETF RFC; BCP 78 rights |
| CAA permits the issuer | RFC 8659, DNS Certification Authority Authorization | https://www.rfc-editor.org/rfc/rfc8659 | November 2019 | IETF RFC; BCP 78 rights |
| Wildcard name matching | RFC 6125, Representation and verification of domain-based application service identity, section 6.4.3 | https://www.rfc-editor.org/rfc/rfc6125 | March 2011 | IETF RFC; BCP 78 rights |
| Reserved example names | RFC 2606, Reserved top level DNS names | https://www.rfc-editor.org/rfc/rfc2606 | June 1999 | IETF RFC; BCP 78 rights |
| Dangling record takeover risk | OWASP Web Security Testing Guide, Test for subdomain takeover (WSTG-CONF-10) | https://owasp.org/www-project-web-security-testing-guide/ | v4.2 | CC BY-SA 4.0; cite, don't copy |
| TTL at or below 300 s within 48 h of a change | Local policy of this skill, not a standard | `scripts/dns_cert.py` (`TTL_LIMIT`, `CHANGE_WINDOW_HOURS`) | 0.1.0 | agent-skills (MIT) |
| 30-day renewal warning | Local default, adjustable with `--warn-days` | `scripts/dns_cert.py` | 0.1.0 | agent-skills (MIT) |
