"""factory_rig: thin deterministic adapters between the rig router and execution backends.

Python 3.9+, standard library only. No scheduler lives here: these modules validate, lease,
gate and reconcile. Dispatch decisions come from the router (Claude Code plus the credit-routing
policy); backends (Noodle, PMO, Curia, Matt's implement-spec) only execute.
"""

__version__ = "0.1.0"
