# Style Guide: Patterns to Strip Before Shipping

Condensed from the AI-writing-tell catalog at tropes.fyi (credit: ossama.is)
plus common Claude-specific tells. Check every draft against this before
finalizing.

## Word choice
- Cut "delve," "certainly," "utilize," "leverage" (as a verb), "robust,"
  "streamline," "harness." Use the plain verb instead.
- Cut ornate filler nouns: "tapestry," "landscape," "paradigm," "synergy,"
  "ecosystem," when a specific noun would do.
- Don't dodge "is/are" with "serves as," "stands as," "represents," "marks."
- Cut throat-clearing adverbs: "quietly," "deeply," "fundamentally,"
  "arguably," "notably."

## Sentence structure
- No "It's not X — it's Y" reframes. State the thing once.
- No "Not X. Not Y. Just Z." countdown drama.
- No self-answered rhetorical questions ("The result? Broken.").
- Don't repeat the same sentence opener three times in a row.
- Don't force everything into rule-of-three lists.
- Cut "it's worth noting," "importantly," "interestingly" — either the point
  matters on its own or cut it.

## Paragraph structure
- No manufactured one-word-sentence fragments for drama
  ("Broken. Completely. Every time.").
- Don't disguise a list as prose with "The first... the second... the third..."

## Tone
- No false-suspense transitions: "Here's the kicker," "here's the thing,"
  "here's where it gets interesting."
- No hand-holding metaphors ("think of it like...") for an audience that
  already knows the domain.
- No inflated stakes — a bug fix is a bug fix, not a "fundamental reshaping."
- No performed vulnerability ("And yes, I'll admit...").
- Don't announce something is "clear" or "simple" instead of just showing it.

## Formatting
- Max one em dash per message/description. Want a second? Use a period or
  comma instead.
- Don't bold the first word of every bullet. If every bullet starts bold,
  remove the bolding.
- Type straight quotes and `->` / `=>`, not curly quotes or `→`. Claude in
  particular overuses `→`.

## Composition
- Don't preview what you're about to say, say it, then summarize what you
  said. Say it once.
- One metaphor max, and only if it actually clarifies. Don't reuse it more
  than once or twice.
- No "In conclusion" / "To sum up" — a PR description just ends.
- No "Despite its challenges, X continues to thrive" pattern — earn the
  conclusion or cut it.

## Banned openers (specific to git/PR/issue writing)
Never start a commit message, PR description, or bug report with:
- "This PR implements..." / "This commit adds..." / "This change..."
- "I've made the following changes..."
- "In this PR, I..."
- "The purpose of this PR is to..."

Start with the actual thing that changed or broke, the way you'd say it out
loud to the person next to you.
