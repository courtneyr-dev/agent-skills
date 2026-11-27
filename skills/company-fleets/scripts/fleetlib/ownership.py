"""One coordinator per workload instance, enforced with factory-rig leases.

The router dispatches; a fleet coordinator only claims the workload it was handed. claim() refuses a
role that is not that workload's coordinator, then takes a factory-rig lease keyed on the tenant and
workload instance, so a second coordinator (another fleet's, or a second copy of the same one) gets
LeaseDenied until the holder releases with its fencing epoch or is fenced.

claim() also returns a one-time token to the claimant and stores only its hash beside the lease, in
<lease key>.owner-seal.json. The owner path (ownerlog.append) needs that token, so knowing the epoch number
alone can't write owner records. An owner ledger is claimed through ownerlog.open_ledger, which calls this.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from typing import Any, Dict, Optional

from factory_rig.canon import atomic_write
from factory_rig.lease import LeaseStore, lease_key

from .registry import Registry, fleet_file, fleet_of


class ClaimRefused(Exception):
    pass


def lease_identity(tenant_id: str, workload_id: str, instance: str):
    return "company-fleets/" + tenant_id, "%s#%s" % (workload_id, instance)


def token_path(lease_root: str, tenant_id: str, workload_id: str, instance: str) -> str:
    return os.path.join(lease_root, lease_key(*lease_identity(tenant_id, workload_id, instance)) + ".owner-seal.json")


def workload_coordinators(reg: Registry, workload_id: str) -> set:
    home = fleet_of(workload_id)
    docs = {home: reg.load(fleet_file(home, "roles"))}
    workload = next((w for w in docs[home]["workloads"] if w["id"] == workload_id), None)
    if workload is None:
        raise ClaimRefused("fleet %s has no workload %s" % (home, workload_id))
    ids = set(workload["roles"]).union(*workload.get("by_profile", {}).values())
    found = set()
    for rid in ids:
        fleet = fleet_of(rid)
        if fleet not in docs:
            docs[fleet] = reg.load(fleet_file(fleet, "roles"))
        role = next((r for r in docs[fleet]["roles"] if r["id"] == rid), None)
        if role and role["kind"] == "coordinator" and role["dispatch"] is False:
            found.add(rid)
    return found


def claim(store: LeaseStore, reg: Registry, tenant_id: str, workload_id: str, instance: str, role_id: str,
          owner_pid: int, contract_hash: str, ttl: float = 600.0, now: Optional[float] = None) -> Dict[str, Any]:
    coordinators = workload_coordinators(reg, workload_id)
    if role_id not in coordinators:
        raise ClaimRefused("%s is not the coordinator of %s (coordinator: %s); it cannot claim or dispatch it"
                           % (role_id, workload_id, ", ".join(sorted(coordinators)) or "none"))
    repo, task = lease_identity(tenant_id, workload_id, instance)
    lease = store.acquire(repo, task, contract_hash, "fleet:" + fleet_of(role_id), role_id, "", owner_pid, ttl=ttl, now=now)
    token = secrets.token_hex(16)
    atomic_write(token_path(store.root, tenant_id, workload_id, instance),
                 json.dumps({"epoch": lease["epoch"], "sha256": hashlib.sha256(token.encode()).hexdigest()}) + "\n")
    return dict(lease, token=token)


def release(store: LeaseStore, tenant_id: str, workload_id: str, instance: str, epoch: int, outcome: str) -> Dict[str, Any]:
    repo, task = lease_identity(tenant_id, workload_id, instance)
    return store.release(repo, task, epoch, outcome)
