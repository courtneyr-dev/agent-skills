#!/usr/bin/env python3
"""Claude Code Stop hook: offer a skill-retro once a skill has driven a batch of work.

Reads the hook input on stdin, counts the tool calls that followed each Skill invocation in the
session transcript (main thread only, until the next Skill invocation), and when a skill reaches
the threshold, blocks the stop once with a reason telling Claude to ask the user whether to run
the retro. Each skill is offered at most once per session.

Stays silent when: stop_hook_active is set (no loops), background tasks are still running (the
batch isn't over), SKILL_RETRO_OFF=1 (unattended `claude -p` runs), or the skill is excluded.
Settings (threshold, exclude, state_dir) come from config.local.json beside this script.

Wire it in ~/.claude/settings.json:
  "Stop": [{"hooks": [{"type": "command", "command": "python3 /abs/path/to/retro_offer_hook.py"}]}]
"""

import fnmatch
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULTS = {"threshold": 15, "exclude": ["skill-retro"], "state_dir": "~/.claude/skill-retro/offered"}


def load_config():
    cfg = dict(DEFAULTS)
    p = Path(os.environ.get("SKILL_RETRO_CONFIG") or HERE / "config.local.json")
    if p.is_file():
        cfg.update({k: v for k, v in json.loads(p.read_text()).items() if k in DEFAULTS})
    return cfg


def batches(transcript_path):
    """[(skill, tool calls after it)] in invocation order, main thread only."""
    out = []
    with open(transcript_path) as f:
        for line in f:
            if '"tool_use"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "assistant" or entry.get("isSidechain"):
                continue
            content = (entry.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") == "Skill":
                    out.append([(block.get("input") or {}).get("skill", "?"), 0])
                elif out:
                    out[-1][1] += 1
    return out


def due(transcript_path, threshold, exclude, offered):
    """Up to 3 skills (AskUserQuestion holds 4 options, one is Skip) whose largest batch reached the
    threshold, not excluded (glob patterns allowed, e.g. "superpowers:*") and not yet offered; biggest first."""
    best = {}
    for skill, calls in batches(transcript_path):
        best[skill] = max(best.get(skill, 0), calls)
    keep = [(s, n) for s, n in best.items()
            if n >= threshold and s not in offered and not any(fnmatch.fnmatchcase(s, p) for p in exclude)]
    return sorted(keep, key=lambda x: -x[1])[:3]


def reason(skills):
    listed = ", ".join(f"{s} ({n} tool calls)" for s, n in skills)
    names = [s for s, _ in skills]
    return (
        f"skill-retro: this session ran a batch under {listed}. Before you end the turn, ask the user once "
        "with AskUserQuestion (header \"Retro\"): \"Run a retro on " + " / ".join(names) + "?\" Options: "
        "\"Run retro (Recommended)\": loads skill-retro, drafts edits, nothing is opened without your yes; "
        "\"Skip\": no retro for this run. With several skills, offer one option per skill, multiSelect. "
        "If they choose to run it, invoke the skill-retro skill for the chosen skill(s). Don't ask again this session."
    )


def main():
    if os.environ.get("SKILL_RETRO_OFF") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("stop_hook_active") or data.get("background_tasks"):
        return 0
    path, session = data.get("transcript_path"), data.get("session_id")
    if not path or not session or not os.path.isfile(path):
        return 0
    cfg = load_config()
    state = Path(os.path.expanduser(cfg["state_dir"])) / f"{session}.json"
    offered = json.loads(state.read_text()) if state.is_file() else []
    skills = due(path, cfg["threshold"], cfg["exclude"], offered)
    if not skills:
        return 0
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(offered + [s for s, _ in skills]))
    print(json.dumps({"decision": "block", "reason": reason(skills)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
