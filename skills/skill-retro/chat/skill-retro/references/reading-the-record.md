# Reading the record

The retro checks the run against what's on the record, so the record has to be something you can quote. Use the first source that has the run in it.

## This conversation (the default)

Read from the first turn that used the skill to the turn that ended the batch. Number user turns as you go (`U1`, `U2`…) so each log entry can cite one. Quote tool errors and the user's corrections word for word; they're the strongest evidence a chat has.

Long chats get compacted: earlier turns can show up only as a summary. A summary is a claim, not a record. If the part you need is summarized, say the log covers only what's visible and ask the user for a transcript of the missing part.

## An uploaded Claude Code transcript (`.jsonl`)

With code execution, uploads are in `/mnt/user-data/uploads/`. One JSON entry per line; tool calls are `tool_use` blocks in `assistant` entries, results are `tool_result` blocks in the following `user` entries; skip entries with `"isSidechain": true`. Files run to several MB, so don't read one whole. Print the run's tool calls first, then read the results you need in full:

```python
import json, sys

path, skill = sys.argv[1], sys.argv[2]
on = False
for n, line in enumerate(open(path), 1):
    e = json.loads(line)
    if e.get("isSidechain"):
        continue
    content = (e.get("message") or {}).get("content")
    if not isinstance(content, list):
        continue
    for b in content:
        if b.get("type") == "tool_use":
            inp = b.get("input", {})
            if b["name"] == "Skill":
                on = inp.get("skill") == skill
            if on:
                print(f"L{n} CALL {b['name']}: {json.dumps(inp)[:160]}")
        elif b.get("type") == "tool_result" and on:
            c = b.get("content")
            text = c if isinstance(c, str) else json.dumps(c)
            print(f"L{n} RESULT{' ERROR' if b.get('is_error') else ''}: {text[:200]}")
```

Run it as `python3 calls.py /mnt/user-data/uploads/<file>.jsonl <skill>`. Cite evidence by line number (`L812`).

## A pasted or exported transcript

Take speaker labels and timestamps as given. If the labels are missing or the paste starts mid-run, ask before building the log; a lesson pinned on the wrong speaker is worse than none.
