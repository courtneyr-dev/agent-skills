"""Provider launch wrapper for Noodle (override NOODLE-PROVIDER-LAUNCH).

Noodle's dispatcher hardcodes `codex exec --dangerously-bypass-approvals-and-sandbox` and
`claude --permission-mode bypassPermissions`, then appends `[agents.<p>].args` after them, so extra
arguments cannot remove those flags. Noodle resolves `[agents.<p>].path` as a directory holding an
executable named `codex` or `claude`. This module is what those two executables run.

It rewrites argv to the rig's own unattended policy,
refuses any attempt to restore a bypass, records the decision, and then `exec`s the real provider
by absolute path. exec (not spawn) keeps stdin, exit status, signals and the process group identical
to a direct launch, so cancellation reaches the real provider unchanged. HOME, CODEX_HOME and every
other environment variable pass through untouched.

Policy file (default <skill>/config/provider-policy.json, override FRIG_POLICY; template in
config/provider-policy.example.json):
{"codex": {"real": "/abs/codex", "sandbox": "workspace-write", "ignore_user_config": true},
 "claude": {"real": "/abs/claude", "permission_mode": "acceptEdits",
            "allowed_tools": "Bash Read Edit Write Glob Grep"},
 "audit": "/abs/path/audit.jsonl"}
`FRIG_REAL_CODEX` / `FRIG_REAL_CLAUDE` override `real` (used by the fake-provider tests).
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

DEFAULT_POLICY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "config", "provider-policy.json")

CODEX_DENY_FLAGS = {"--dangerously-bypass-approvals-and-sandbox", "--yolo"}
CODEX_DENY_SANDBOX = {"danger-full-access"}
CLAUDE_DENY_FLAGS = {"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions"}
CLAUDE_DENY_MODES = {"bypassPermissions", "dontAsk", "auto"}


class PolicyViolation(Exception):
    pass


def load_policy() -> Dict[str, Any]:
    path = os.environ.get("FRIG_POLICY", DEFAULT_POLICY)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def rewrite_codex(argv: List[str], pol: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    dropped: List[str] = []
    out: List[str] = []
    sandbox_seen = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in CODEX_DENY_FLAGS:
            dropped.append(a)
            i += 1
            continue
        if a in ("-s", "--sandbox") and i + 1 < len(argv):
            if argv[i + 1] in CODEX_DENY_SANDBOX:
                raise PolicyViolation("sandbox %s is not allowed" % argv[i + 1])
            sandbox_seen = argv[i + 1]
            out += [a, argv[i + 1]]
            i += 2
            continue
        if a.startswith("--sandbox="):
            if a.split("=", 1)[1] in CODEX_DENY_SANDBOX:
                raise PolicyViolation("sandbox %s is not allowed" % a.split("=", 1)[1])
            sandbox_seen = a.split("=", 1)[1]
        out.append(a)
        i += 1
    inject: List[str] = []
    model = None
    for j, tok in enumerate(out):
        if tok == "--model" and j + 1 < len(out):
            model = out[j + 1]
    effort = (pol.get("effort_by_model") or {}).get(model)
    if effort and not any("model_reasoning_effort" in t for t in out):
        inject += ["-c", 'model_reasoning_effort="%s"' % effort]
    if sandbox_seen is None:
        inject += ["-s", pol.get("sandbox", "workspace-write")]
    if pol.get("ignore_user_config", True) and "--ignore-user-config" not in out:
        inject.append("--ignore-user-config")
    # codex exec [OPTIONS]: options may sit right after the subcommand.
    if out and out[0] == "exec":
        out = [out[0]] + inject + out[1:]
    else:
        raise PolicyViolation("expected `exec` as the first codex argument, got %r" % (out[:1],))
    return out, dropped


def rewrite_claude(argv: List[str], pol: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    dropped: List[str] = []
    out: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in CLAUDE_DENY_FLAGS:
            dropped.append(a)
            i += 1
            continue
        if a == "--permission-mode" and i + 1 < len(argv):
            if argv[i + 1] in CLAUDE_DENY_MODES:
                dropped += [a, argv[i + 1]]
            else:
                out += [a, argv[i + 1]]
            i += 2
            continue
        if a.startswith("--permission-mode="):
            if a.split("=", 1)[1] in CLAUDE_DENY_MODES:
                dropped.append(a)
                i += 1
                continue
        if a in ("--allowedTools", "--allowed-tools", "--tools") and i + 1 < len(argv):
            # Noodle never sends these; an explicit one from args is honored only if the policy allows it.
            out += [a, argv[i + 1]]
            i += 2
            continue
        out.append(a)
        i += 1
    if "--permission-mode" not in out and not any(x.startswith("--permission-mode=") for x in out):
        out += ["--permission-mode", pol.get("permission_mode", "acceptEdits")]
    if not any(x in ("--allowedTools", "--allowed-tools") for x in out):
        out += ["--allowedTools", pol.get("allowed_tools", "Bash Read Edit Write Glob Grep")]
    return out, dropped


def resolve_real(name: str, pol: Dict[str, Any]) -> str:
    real = os.environ.get("FRIG_REAL_" + name.upper()) or pol.get("real")
    if not real or not os.path.isabs(real):
        raise PolicyViolation("policy for %s needs an absolute `real` path" % name)
    if not (os.path.isfile(real) and os.access(real, os.X_OK)):
        raise PolicyViolation("real %s not executable: %s" % (name, real))
    me = os.path.realpath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if os.path.realpath(real) == me or os.environ.get("FRIG_WRAPPER_ACTIVE") == name:
        raise PolicyViolation("recursive invocation: %s resolves to the wrapper itself" % name)
    return real


def audit(path: str, record: Dict[str, Any]) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def main(name: str, argv: List[str]) -> int:
    try:
        policy = load_policy()
        pol = policy.get(name, {})
        real = resolve_real(name, pol)
        if name == "codex":
            new, dropped = rewrite_codex(argv, pol)
        elif name == "claude":
            new, dropped = rewrite_claude(argv, pol)
        else:
            raise PolicyViolation("unsupported provider %s" % name)
    except (PolicyViolation, OSError, ValueError) as exc:
        sys.stderr.write("factory-rig provider wrapper refused %s launch: %s\n" % (name, exc))
        return 64
    audit(os.environ.get("FRIG_AUDIT") or policy.get("audit", ""), {
        "at": time.time(), "provider": name, "real": real, "cwd": os.getcwd(),
        "original_argv": argv, "rewritten_argv": new, "dropped": dropped,
    })
    env = dict(os.environ)
    env["FRIG_WRAPPER_ACTIVE"] = name
    os.execve(real, [real] + new, env)
    return 70  # unreachable


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2:]))
