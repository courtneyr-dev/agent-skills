# Document structure

### Step 5: Generate the Complete Markdown File

Use the document structure below. Fill in everything from the bulletin. Leave scaffolding sections empty (they're for the user to fill during/after the service).

---

## Document Structure

### YAML Front Matter

```yaml
---
excalidraw-plugin: parsed
excalidraw-open-md: true
excalidraw-embed-md: true
excalidraw-autoexport: svg
aliases:
  - "Sermon Notes — [Month Day, Year]"
  - "[Church Name] - [Month Day, Year]"
  - "[Liturgical Day Name]"
tags:
  - excalidraw
  - sermon-notes
  - "[liturgical-season]"
  - "[church-name-slugified]"
  - "[year]"
title: "Sermon Notes — [Service Date]"
date: YYYY-MM-DD
service_date: YYYY-MM-DD
church: "[Church Name]"
denomination: "[Denomination]"
pastor: "[Pastor Name]"
sermon_title: ""
sermon_text: "[Primary scripture reference]"
liturgical_season: "[Season]"
liturgical_year: "[A/B/C]"
liturgical_color: "[Color]"
liturgical_week: "[e.g., Fourth Sunday after Epiphany]"
hymns:
  - number: "[Hymn number]"
    title: "[Hymn title]"
  - number: "[Hymn number]"
    title: "[Hymn title]"
---
```

### Document Body — Excalidraw Hybrid Note Structure

The file has three parts in this order:

1. **Title + SVG embed** — links back to self and shows the Excalidraw drawing on the text side
2. **`# Back of Card`** — all the sermon content (this is what the user sees in markdown mode)
3. **`# Excalidraw Data`** — text elements, embedded files, and drawing JSON (inside `%%` comments)

The user toggles between the visual canvas and the text back with their hotkey.

```markdown
# [[YYYY-MM-DD]]

![[YYYY-MM-DD.svg]]

# Back of Card

## Liturgical Context

### Christian Calendar

- **Season:** [Season name]
- **Week:** [Specific Sunday/day]
- **Liturgical Year:** Year [A/B/C] ([Primary Gospel])
- **Liturgical Color:** [Color] — [significance of color]

### Hebrew Calendar

- **Date:** [Hebrew date]
- **Observances:** [Any Jewish observances near this date]

### Ecumenical Observances

- [Any ecumenical observances for this date, or "None noted"]

### Revised Common Lectionary Readings

- **Old Testament:** [Reference] — [[Book Chapter#Verse]] (link, not embed, for RCL listing)
- **Psalm:** [Reference] — [[Psalm N#Verse]]
- **Epistle:** [Reference] — [[Book Chapter#Verse]]
- **Gospel:** [Reference] — [[Book Chapter#Verse]]

### Narrative Lectionary Reading

- **Year:** [1/2/3/4] ([Primary Text Focus])
- **Reading:** [Reference] — [[Book Chapter#Verse]]
- **Theme:** [Brief thematic description]

---

## Service Information

- **Church:** [Full church name]
- **Date:** [Full date]
- **Time:** [Service time]
- **Pastor:** [Name]
- **Denomination:** [Denomination]

---

## Order of Worship

[Reproduce the full order of worship from the bulletin, using the heading levels below]

### Gathering

#### Prelude

[Title if listed]

#### Welcome and Announcements

#### Call to Worship

[If scripture-based, include Bible Linker embeds]

#### Opening Hymn: [Title] ([Hymnal] #[Number])

[Full hymn lyrics with attribution — see Step 4 format]

### Word

#### Prayer of Illumination

#### Scripture Reading: [Reference]

[Bible Linker embeds for every verse]

#### Responsive Reading: [Reference]

[Leader/People format with Bible Linker embeds — see Step 3]

#### Sermon: "[Title]" — [Preacher Name]

**Scripture Text:** [Reference]

[Bible Linker embeds for sermon text]

### Response

#### Hymn of Response: [Title] ([Hymnal] #[Number])

[Full hymn lyrics with attribution]

#### Prayers of the People

#### Offering

#### Doxology

### Sending

#### Closing Hymn: [Title] ([Hymnal] #[Number])

[Full hymn lyrics with attribution]

#### Benediction

#### Postlude

---

## Sermon Notes

> [!note] Fill this section during and after the service

### Sermon Title

<!-- Fill in when announced -->

### Introduction

### Main Points

#### Point 1:

#### Point 2:

#### Point 3:

### Illustrations and Stories

### Scripture Connections

<!-- Other passages referenced during the sermon -->

### Key Quotes

<!-- Notable phrases or statements -->

---

## Personal Reflections

> [!note] Fill this section after the service

### What Spoke to Me

### Questions Raised

### Challenges to My Thinking

### Liturgical Context Reflections

<!-- How does the season/color/calendar context shape the message? -->

---

## Applications

### Action Items

- [ ]
- [ ]
- [ ]

### Prayer List

<!-- People or situations mentioned for prayer -->

### Follow-Up Study

<!-- Passages or topics to study further -->

---

## Connections

### Related Notes

## <!-- Links to other notes in your vault -->

### Related Bible Studies

## <!-- Links to bible studies of passages referenced -->

### Previous Sermon Notes

## <!-- Link to last week's notes -->

---

## Announcements and Church Life

[Reproduce all announcements from the bulletin]

### Upcoming Events

| Date | Event | Details |
| ---- | ----- | ------- |
|      |       |         |

### Prayer Requests

[From the bulletin]

---

## Church Information

- **Church:** [Full name]
- **Address:** [Full address]
- **Phone:** [Phone number]
- **Website:** [URL]
- **Email:** [Email]
- **Pastor:** [Name]
- **Staff:** [List any staff mentioned]

### Mission Statement

> [Church mission statement if included in bulletin]

# Excalidraw Data

## Text Elements

## Embedded Files

%% ## Drawing
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"}}
%%
```
