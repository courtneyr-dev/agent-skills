"""fleetlib: registry, validation, resolution and handoff guards for company fleets.

Python 3.9+, standard library only. Hashing, atomic writes, contracts and leases come from the
sibling skill factory-rig (imported, never copied), so one implementation owns each mechanism.
"""
import os
import sys

SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FACTORY_RIG_SCRIPTS = os.path.normpath(os.path.join(SKILL_DIR, "..", "factory-rig", "scripts"))

if not os.path.isdir(os.path.join(FACTORY_RIG_SCRIPTS, "factory_rig")):
    raise ImportError("company-fleets needs skills/factory-rig beside it (looked in %s)" % FACTORY_RIG_SCRIPTS)
if FACTORY_RIG_SCRIPTS not in sys.path:
    sys.path.insert(0, FACTORY_RIG_SCRIPTS)

__version__ = "0.1.0"
