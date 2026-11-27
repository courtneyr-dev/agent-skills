"""Build handoff.v1 fixtures for the release gate with company-fleets' own handoff code.

Two separate steps, on purpose:
- write_reviews() stands in for the reviewer role: it writes one review file per gate input naming the exact
  bytes it read (reviewed-sha256), who reviewed (reviewed-by) and the verdict. Fixtures only; never run it over
  real inputs, because a review is a judgment, not a hash.
- build() only binds the current bytes of the inputs and their review files into a handoff. Rebinding after an
  edit without a new review leaves the old review naming the old bytes, and the gate refuses it.

Run as a script to regenerate the fixture reviews, fixtures/handoff.json and fixtures/handoff-stale.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
FLEETLIB = os.path.normpath(os.path.join(SKILL, "..", "company-fleets", "scripts"))
sys.path.insert(0, FLEETLIB)

from fleetlib.handoff import apply_worker_update, key_for, open_handoff  # noqa: E402
from factory_rig.canon import sha_bytes, sha_file  # noqa: E402
from factory_rig.contract import contract_hash  # noqa: E402

REVIEWER = "product.security-maintainer"
PRODUCER = "product.release-engineer"
INPUTS = [("compat-ok.json", "compatibility matrix"), ("CHANGELOG.md", "changelog"), ("sbom.json", "CycloneDX SBOM")]


def outputs_for(candidate):
    return [(candidate, "release candidate")] + INPUTS


def review_path(output):
    return "evidence/%s.review.txt" % output


def write_reviews(base, candidate="candidate-ok.json", reviewer=REVIEWER, verdict="pass"):
    """Fixture stand-in for a reviewer: one review per input, bound to the bytes on disk now."""
    for path, kind in outputs_for(candidate):
        digest = sha_file(os.path.join(base, path))
        with open(os.path.join(base, review_path(path)), "w", encoding="utf-8") as fh:
            fh.write("# SYNTHETIC fixture review of %s (%s), written by the fixture builder standing in for the reviewer.\n"
                     "reviewed-by: %s\nreviewed-sha256: %s\nverdict: %s\n" % (path, kind, reviewer, digest, verdict))


def owner(chash):
    return {
        "handoff_id": "HO-FIX-PROD-REL-2",
        "workload_id": "product.workload.extension-release",
        "tenant_id": "tenant-fixture-co",
        "client_id": None,
        "operating_profile": "product",
        "outcome": "SYNTHETIC: Fixture Co Forms Connector 2.0.0 gate inputs, ready for the release gate.",
        "scope": ["Release candidate, compatibility matrix, changelog and SBOM for 2.0.0"],
        "exclusions": ["Publishing to any marketplace", "Packaging approval"],
        "acceptance_criteria": ["Every gate input has a passing review naming its exact bytes under the current contract"],
        "sources": [{"ref": "fixtures/contract.json", "revision": "FIX-PROD-REL-2 r2"}],
        "producer": PRODUCER,
        "reviewer": REVIEWER,
        "acceptance_owner": "human:release-owner",
        "execution_owner": "product.product-lead",
        "data": {"classification": "internal", "allowed_destinations": ["tenant:tenant-fixture-co", "rig:evidence"]},
        "authority": {"tools": ["release_gate.py"], "mutation": "none", "external_actions": "none", "publication": "none"},
        "budget": {"max_minutes": 30, "max_retries": 1},
        "stop_conditions": ["Gate decision recorded"],
        "cancellation": "Stop, keep the partial gate output labeled partial.",
        "next_consumer": "human:release-owner",
        "readiness_criteria": ["release_gate.py gate prints ready-for-human-approval"],
        "contract_hash": chash,
    }


def build(base, candidate="candidate-ok.json"):
    """Bind the current bytes of the inputs and of their existing review files. Writes no review."""
    with open(os.path.join(base, "contract.json")) as fh:
        chash = contract_hash(json.load(fh))
    h = open_handoff(owner(chash))
    outs = [{"path": p, "sha256": sha_file(os.path.join(base, p)), "artifact_type": t} for p, t in outputs_for(candidate)]
    out_sha = {o["path"]: o["sha256"] for o in outs}
    evidence = [{"path": review_path(p), "sha256": sha_file(os.path.join(base, review_path(p))), "about": p,
                 "about_sha256": out_sha[p], "contract_hash": chash} for p, _ in outputs_for(candidate)]
    h, refused = apply_worker_update(h, {"outputs": outs, "evidence": evidence,
                                         "summary": "SYNTHETIC: candidate, matrix, changelog and SBOM bound to their reviews."})
    assert not refused, refused
    return h


def make_stale(h, base):
    """The compat matrix as reviewed was an earlier draft; the file on disk changed after review."""
    with open(os.path.join(base, "compat-ok.json")) as fh:
        earlier = json.load(fh)
    earlier["declares"]["hosts"]["wordpress"]["min"] = "6.5"
    old = sha_bytes((json.dumps(earlier, indent=2) + "\n").encode("utf-8"))
    for o in h["outputs"]:
        if o["path"] == "compat-ok.json":
            o["sha256"] = old
    for e in h["evidence"]:
        if e["about"] == "compat-ok.json":
            e["about_sha256"] = old
    h["idempotency_key"] = key_for(h)
    return h


def write(path, h):
    with open(path, "w") as fh:
        fh.write(json.dumps(h, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    fx = os.path.join(SKILL, "fixtures")
    write_reviews(fx, "candidate-ok.json")
    write_reviews(fx, "candidate-stale-evidence.json")
    write(os.path.join(fx, "handoff.json"), build(fx, "candidate-ok.json"))
    write(os.path.join(fx, "handoff-stale.json"), make_stale(build(fx, "candidate-stale-evidence.json"), fx))
    print("wrote fixture reviews, fixtures/handoff.json and fixtures/handoff-stale.json")
