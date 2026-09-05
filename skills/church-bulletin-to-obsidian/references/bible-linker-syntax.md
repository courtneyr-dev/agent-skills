# Bible Linker scripture syntax

### Step 3: Convert ALL Scripture to Bible Linker Syntax

This is the most critical formatting step. The Obsidian Bible Linker plugin renders verse text inline when using embed syntax.

#### Bible Linker Syntax Rules

```
![[Book Chapter#Verse]]     ← EMBED: renders full verse text in reading view
[[Book Chapter#Verse]]      ← INLINE LINK: clickable but doesn't render text
```

**Always use embeds (`![[...]]`) for scripture in this document** unless the context calls for an inline link (rare).

#### Book Name Reference Table

ALWAYS use the full book name. The Bible Linker plugin uses these exact names:

**Old Testament:**
Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Joshua, Judges, Ruth, 1 Samuel, 2 Samuel, 1 Kings, 2 Kings, 1 Chronicles, 2 Chronicles, Ezra, Nehemiah, Esther, Job, Psalm, Proverbs, Ecclesiastes, Song of Solomon, Isaiah, Jeremiah, Lamentations, Ezekiel, Daniel, Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Habakkuk, Zephaniah, Haggai, Zechariah, Malachi

**New Testament:**
Matthew, Mark, Luke, John, Acts, Romans, 1 Corinthians, 2 Corinthians, Galatians, Ephesians, Philippians, Colossians, 1 Thessalonians, 2 Thessalonians, 1 Timothy, 2 Timothy, Titus, Philemon, Hebrews, James, 1 Peter, 2 Peter, 1 John, 2 John, 3 John, Jude, Revelation

**Critical notes:**

- Use `Psalm` (singular), not `Psalms`
- Use `Song of Solomon`, not `Song of Songs`
- Numbered books: `1 Samuel` (with space), not `1Samuel`
- No abbreviations: `Genesis` not `Gen`, `Matthew` not `Matt`

#### Expanding Verse Ranges

Every verse in a range gets its own embed line. No exceptions.

For **Romans 8:28-30**:

```
![[Romans 8#28]]
![[Romans 8#29]]
![[Romans 8#30]]
```

For **Psalm 23:1-6**:

```
![[Psalm 23#1]]
![[Psalm 23#2]]
![[Psalm 23#3]]
![[Psalm 23#4]]
![[Psalm 23#5]]
![[Psalm 23#6]]
```

For a single verse like **John 3:16**:

```
![[John 3#16]]
```

#### Cross-Chapter Ranges

If a reading spans chapters (e.g., Isaiah 52:13-53:12), expand each chapter separately:

```
![[Isaiah 52#13]]
![[Isaiah 52#14]]
![[Isaiah 52#15]]
![[Isaiah 53#1]]
![[Isaiah 53#2]]
...
![[Isaiah 53#12]]
```

#### Responsive Readings with Bible Linker

For responsive readings, preserve the Leader/People format AND include Bible Linker embeds. Example for Psalm 100:

```markdown
##### Responsive Reading: Psalm 100

**Leader:** Make a joyful noise to the Lord, all the earth.
![[Psalm 100#1]]

**People:** Worship the Lord with gladness; come into his presence with singing.
![[Psalm 100#2]]

**Leader:** Know that the Lord is God. It is he that made us, and we are his; we are his people, and the sheep of his pasture.
![[Psalm 100#3]]

**People:** Enter his gates with thanksgiving, and his courts with praise. Give thanks to him, bless his name.
![[Psalm 100#4]]

**All:** For the Lord is good; his steadfast love endures forever, and his faithfulness to all generations.
![[Psalm 100#5]]
```
