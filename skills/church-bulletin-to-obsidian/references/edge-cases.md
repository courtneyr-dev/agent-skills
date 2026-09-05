# Edge cases

## Edge Cases

### Multiple Scripture Readings

Some services have 3-4 readings. Include ALL of them with full Bible Linker embeds for each.

### Hymns Not Found

If you can't find the lyrics for a hymn, note the hymn number and title and flag it:

```markdown
#### [Hymn Title] ([Hymnal] #[Number])

> [!warning] Lyrics not found — look up in physical hymnal
```

### Non-Standard Service Elements

Some churches include elements not in the standard template (litanies, creeds, special music, children's moments). Include them in their logical position within the order of worship.

### Bulletin Images with Poor Quality

If parts of the bulletin image are unreadable, note what you can't read:

```markdown
> [!warning] Unreadable in bulletin image — verify from another source
```

### Multiple Services on Same Date

If the user processes multiple bulletins for the same date, append a suffix:
`YYYY-MM-DD.md`, `YYYY-MM-DD-evening.md`, etc.
