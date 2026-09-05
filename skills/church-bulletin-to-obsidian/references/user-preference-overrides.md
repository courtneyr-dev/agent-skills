# User preference overrides

## USER PREFERENCE OVERRIDES (authoritative — read last, apply first)

These preferences supersede any earlier instruction in this file. Added 2026-04-18 after repeated correction.

### Vault Path — PARA prefix is required

The vault uses PARA numbering prefixes: `Projects/`, `Areas/`, `Resources/`, `Archives/`, `Inbox/`, `6. Templates/`.

**Always write sermon notes to:**

```
Areas/Sermon Notes/YYYY-MM-DD.md
```

Not `Areas/Sermon Notes/`. The `2. ` prefix is mandatory.

The canonical host vault path is `$VAULT_DIR/Areas/Sermon Notes/YYYY-MM-DD.md`. Use Desktop Commander `write_file` to write directly to the canonical Mac path when the Obsidian MCP is unavailable.

### Hymn Lyrics — INLINE in Order of Worship, not in a separate section

**Do NOT create a separate `## Hymns` section at the bottom of the document.**

Hymn lyrics are personal devotional notes. Place the full lyrics (with attribution) **inline at the exact position each hymn appears in the Order of Worship**. This mirrors the experience of following along during the service and lets the reader read the order of worship top-to-bottom with everything in context.

**Pattern for every musical element in the Order of Worship** — Gathering Song, Processional Hymn, Hymn of Praise, Response of Praise (Gloria Patri, #704), Offertory Response (Doxology, #706), Sermon Hymn, Hymn of Dedication, Recessional Hymn, Postlude, and anything else sung:

```markdown
#### Hymn of Praise — "Christ Is Alive" (No. 205)

**Author:** Brian Wren, 1968
**Tune:** TRURO
**Composer:** Thomas Williams's *Psalmodia Evangelica*, 1789
**Copyright:** © 1975 Hope Publishing Co.

1. Christ is alive! Let Christians sing.
   The cross stands empty to the sky.
   Let streets and homes with praises ring.
   Love, drowned in death, shall never die.

2. Christ is alive! No longer bound
   to distant years in Palestine,
   but saving, healing, here and now,
   and touching every place and time.

[...all verses...]
```

**Short responses** (Gloria Patri #704, Doxology #706, Amens, etc.) still get their inline mini-block with the full text, author/composer, and tune name — even though they are brief.

### Reference example — last week's note (2026-04-12)

`Areas/Sermon Notes/2026-04-12.md` is the reference for hymn-inline style. Match that structure for every new bulletin.

### Updated Quality Checklist additions

- [ ] Vault path is `Areas/Sermon Notes/YYYY-MM-DD.md` with the PARA `2. ` prefix
- [ ] Every hymn, response, and sung element has its full lyrics + attribution **inline at the point it appears in the Order of Worship**
- [ ] There is NO standalone `## Hymns` section at the bottom of the document
- [ ] Short responses (Gloria Patri, Doxology, etc.) also appear inline with full text
- [ ] Structure matches the prior week's sermon note (`Areas/Sermon Notes/YYYY-MM-DD.md` from the previous Sunday)

### Theology Wiki Cross-Linking

After writing the sermon note, also update `Resources/MOCs/Faith & Theology MOC.md` to link the new note under an appropriate theme grouping (Advent, Christmas, Epiphany, Lent, Easter, Pentecost, Ordinary Time, or a thematic grouping like "Identity and Calling", "Pastoral Care", "Justice and Social Action", "Apostolic Calling", etc.). Create a new theme subheading if none of the existing ones fit.


### Browser staging on finish (added 2026-07-18)

After the sermon note and NotebookLM source are written and the MOC is updated, offer one finishing move (don't do it unprompted — Sunday context, keep it calm):

> "Want me to open the note and this week's passages for review?"

If yes, open in one batched Claude in Chrome call:

1. The new sermon note — Obsidian URI: `obsidian://open?vault=2nd%20Brain&file=2.%20Areas%2FSermon%20Notes%2FYYYY-MM-DD`
2. One BibleGateway tab per distinct reading (not per verse): `https://www.biblegateway.com/passage/?search=[Book+Ch:V-V]&version=NRSVUE`

Cap: the note + 4 passage tabs. If Chrome isn't connected, print the links instead.
