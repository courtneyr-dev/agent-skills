# Unknowns mapping and context engineering

## Blind spot pass (before unfamiliar, high-impact work)

Map four quadrants before implementing:

- Known knowns — what the user stated clearly. Freeze these as decisions.
- Known unknowns — flagged open questions. Resolve by targeted retrieval or one question.
- Unknown knowns — things the user probably cares about but didn't spell out (conventions, taste, constraints visible in prior work). Infer from the territory; state assumptions.
- Unknown unknowns — issues nobody has noticed. Probe with a prototype, a read-only exploration pass, or a second-model critique.

Rules:

- Ask one question at a time, and only when the answer could change the architecture. Never ask about wording, formatting, or minor implementation details — make the call and state it.
- When the user will only know what they want after seeing it: propose a prototype or artifact before real implementation.
- When the user can't describe what they want: ask for or find references. Prefer source-code references over prose when behavior must match an existing implementation.
- Plans lead with the decisions the user is most likely to tweak; mechanical steps go last.
- During implementation, log deviations. After, explain what changed in a reviewable form.
- The prompt is the map; the codebase is the territory. When they disagree, trust the territory and say so — don't silently follow the map.

## Context rules (context is a finite budget)

- Load the smallest useful set of files. Grep/glob/index first; targeted reads second; whole files last.
- Progressive disclosure: structure first, then only the relevant details.
- Don't paste full files or summarize huge docs unless the summary will be reused — and if it will, put it in the wiki, not chat.
- Use file paths and index entries as context signals instead of contents.
- Delegate bulk reading to a read-only subagent (Explore) and take back only distilled findings.
- Once a tool result's meaning is captured, its raw output is dead weight — compact or move on.
- Canonical examples beat long edge-case lists. Right-altitude instructions beat brittle if/else rules.
- Prefer "read only these first" over "read everything"; prefer "report back at the first meaningful decision point" over "complete everything autonomously" when uncertainty is high.
- Missing context causes guessing, and guessing is the expensive failure mode: a wrong build plus a rebuild costs more than one clarifying question or one targeted retrieval.
