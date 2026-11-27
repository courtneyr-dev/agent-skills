#!/usr/bin/env python3
"""Build the fixture owner ledgers that the agency and corporate gates read in their evals and examples.

Each ledger goes through the owner path: open it with the coordinator claim (fleets/<fleet>/owner/<instance>),
record the values with ownerlog.append under that claim's token, then close it on release. An instance gets
one ledger, so an existing ledger is left as it is and reported; nothing is deleted. To rebuild one, move its
folder out of the owner root first.

  python3 scripts/owner-fixtures.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fleetlib import ownerlog  # noqa: E402
from fleetlib.registry import Registry, fleet_of  # noqa: E402

SKILLS = os.path.normpath(os.path.join(HERE, "..", ".."))
LABEL = "SYNTHETIC FIXTURE (Fixture Co): recorded by scripts/owner-fixtures.py as a stand-in for the named owner."
LEDGERS = [
    {"base": "agency-engagement-gate/fixtures", "role": "agency.engagement-director",
     "lease": ("tenant-a", "agency.workload.qualification-and-estimate", "FIX-AG-GATE-1"),
     "records": [("pin", {"name": "margin-policy", "path": "margin-policy.json", "label": LABEL}),
                 ("pin", {"name": "rate-card", "path": "rates.json", "label": LABEL})]},
    {"base": "corporate-claims-check/fixtures", "role": "corporate.chief-of-staff",
     "lease": ("fixture-co", "corporate.workload.campaign-staging", "FIX-CORP-CLAIMS-1"),
     "records": [("claims-sign-off", {"register": "sources.json", "signed_off_by": "human:claims-reviewer", "author": "human:content-author",
                                      "signed_on": "2026-11-26", "label": LABEL + " The reviewer checked each excerpt against the live page."})]},
    {"base": "corporate-email-guard/fixtures", "role": "corporate.chief-of-staff",
     "lease": ("fixture-co", "corporate.workload.campaign-staging", "fixture-news-2026-11"),
     "records": [("pin", {"name": "suppression-list", "path": "suppression.csv", "label": LABEL}),
                 ("send-approval", "approval-valid.json")]},
]


def build(spec):
    tenant, workload, instance = spec["lease"]
    root, base = ownerlog.owner_dir(fleet_of(workload), instance), os.path.join(SKILLS, spec["base"])
    rel = os.path.relpath(root, SKILLS)
    try:
        lease = ownerlog.open_ledger(root, Registry(), tenant, workload, instance, spec["role"], os.getpid(),
                                     "no-factory-rig-contract", exclusive=True, label=LABEL)
    except ownerlog.OwnerLogError as exc:
        return {"ledger": rel, "left-as-is": exc.reason}
    out = []
    for kind, rec in spec["records"]:
        if isinstance(rec, str):
            with open(os.path.join(base, rec), encoding="utf-8") as fh:
                rec = json.load(fh)
        out.append(ownerlog.append(root, kind, rec, tenant, workload, instance, lease["epoch"], lease["token"], base=base)[0])
    ownerlog.close_ledger(root, tenant, workload, instance, lease["epoch"], lease["token"], "fixture recorded")
    return {"ledger": rel, "epoch": lease["epoch"], "records": out, "closed": True}


if __name__ == "__main__":
    print(json.dumps([build(s) for s in LEDGERS], indent=2))
