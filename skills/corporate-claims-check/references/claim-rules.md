Source: Google Search Central, "Do You Need an SEO? Tips for Hiring an SEO"; FTC Policy Statement Regarding Advertising Substantiation
Location: https://developers.google.com/search/docs/fundamentals/do-i-need-seo ; https://www.ftc.gov/legal-library/browse/ftc-policy-statement-regarding-advertising-substantiation
Version or retrieved date: Google page fetched 2026-11-25 (page footer reads "Last updated 2026-06-05 UTC"); FTC statement dated 1984, not re-fetched at authoring time (ftc.gov answered a plain curl request with HTTP 403 on 2026-11-25)
Rights: Google page content is under the Creative Commons Attribution 4.0 License per its footer; the FTC statement is a US government document

# Claim rules

`scripts/claims_check.py` runs eleven blocking rules: two on the register's sign-off and nine per sentence, plus the owner-log rules company-fleets defines. Before matching, it turns the draft into the text a reader sees: `<blockquote>`, `<q>` and `<a href>` become their Markdown forms and other HTML tags are dropped, HTML entities decoded, NFKC (fullwidth letters, the numero sign), format characters (zero-width, soft hyphen), combining marks and invisible joiners dropped, spaced-out letters rejoined, Markdown emphasis inside a word and a hyphenated line break removed, and Cyrillic and Greek look-alikes folded to Latin. It checks every block, code fences and footnote definitions included; a fence that never closes is invalid input (exit 2). The script reports a rule id, a line number and the matched text, so the author can fix the sentence and rerun.

## Where the rules come from

- Google's page tells site owners to walk away from a vendor who promises first place. Two sentences from it sit in `fixtures/sources.json` as verbatim excerpts: "No one can guarantee a #1 ranking on Google." and "If they guarantee you that their changes will give you first place in search results, find someone else." The page also warns against claims of a "special relationship" with Google and a "priority submit" to Google. The script does not match those two phrases.
- The FTC's advertising substantiation policy says an advertiser needs a reasonable basis for an objective claim before the ad runs. Statistics and outcome claims are objective claims, so the script asks for a registered source on each one. The script does not decide whether a source is a reasonable basis; a person does.

This file states a local policy. It is not legal advice and the script does not establish that a draft complies with any law.

## Rules

### ranking-guarantee

- Fires on: a promise of search rank, position or AI-answer inclusion, found by cue class rather than a phrase list, when the author makes it or makes it to the client. A sentence is a guarantee when an un-negated promise cue and a target meet in it:
  - a promise cue (guarantee, assured, promise, money back, or you don't pay, risk-free) with any ranking, position, traffic, visibility or AI-answer target;
  - a commitment cue (ensure, make sure, count on, rest assured) with a position within five words after it, in the same clause;
  - "certified" or "warranted" right after a position ("Number one on Google, certified");
  - a certainty cue (will, 'll, shall, going to) followed by "rank", by a position within six words, or by an inclusion verb (cite, recommend, feature, appear, show up) within two words, on an AI target;
  - "always" or "every time" with a position or an AI target and an inclusion verb;
  - an achievement verb (dominate, hit, land, reach, deliver, get you, put you) followed by a position in the same clause, or a timeframe (in 30 days, within a month, by spring) with a position in the same clause;
  - "you" or "your site, pages, brand" followed by "ranks", "sits" or "appears" and a position ("Your site ranks #1 on Google").
- Who says it: the script reads the nearest speaker word before the cue, in the cue's own clause. We, our, you, your, an imperative ("Rank #1 or you don't pay") and a headline fragment ("#1 ranking guaranteed") count as the author's promise. A third party (who, that, which, they, anyone, agencies, vendors, competitors and similar) makes the sentence reported speech, so "Agencies that promise top rankings should worry you." passes. A search or AI engine counts as that third party only for a promise verb: "Google guarantees nothing about rankings." passes, while "ChatGPT will cite your brand." is still the author's prediction to the client. A quote that matches a cited excerpt word for word is the source's speech, so Google's own warning, quoted and cited, passes.
- The 25 phrasings from the 2026-11-26 independent review and 12 disguised or paraphrased promises from the re-review are all flagged; `scripts/tests/test_claims_check.py` (ReviewProbes) holds them, plus 14 cautionary, reporting and quoted sentences that must pass, such as "We will report on your rankings each month."
- Why it blocks even with a citation: no vendor or author controls a search engine's ranking or an AI assistant's answer. A citation can show that a number is real. It cannot make a promise true.
- Does not fire on negated or reported statements: "No one can guarantee a #1 ranking on Google." The script reads the clause before the match, split at commas, semicolons, colons, "but", "however", "yet" and "and", for a cue such as "no one", "cannot", "never", "beware" or "claims to". "Not only" and "no matter" do not count as cues. A cue that follows the phrase is not credited, so that case errs toward blocking.

### unsupported-ranking-claim

- Fires on: an outcome verb near a ranking or traffic noun, in either order ("boost your rankings", "traffic tripled"), when the sentence has no valid citation or when no cited excerpt states that outcome (holds both the verb and the noun).
- Fix: cite the excerpt that states the outcome, or cut the claim.

### statistic-without-citation

- Fires on: a percentage ("40%", "12 percent"), a multiplier ("3x", "2.5-fold", "5 times") or a word multiplier ("three times", "twice") on a sentence with no valid citation.
- Known false positives: "3 times a week" reads as a multiplier. Rewrite the sentence or cite a source.

### citation-unknown-source

- Fires on: a footnote id or an http(s) link url that is not in the register. The url must match a register url exactly, including a trailing slash.
- Why: a citation that resolves to nothing is the usual shape of a fabricated reference.

### quote-not-in-source

- Fires on: quoted text on a cited sentence that appears, as whole words, in none of the cited sources' excerpts. Quotes are straight or curly doubles and singles, „…“, «…», and a `>` blockquote followed by an attribution line (`— Google Search Central[^S1]`), which cites it. A quote spanning two excerpts doesn't match. The comparison is case-sensitive, collapses whitespace, turns curly quotes into straight ones and ignores punctuation at the end of the quote. "one can guar" doesn't match "one can guarantee".

### quote-too-short

- Fires on: a one-word quote on a cited sentence. "ran" sits inside "guarantee", and a single word can come from anywhere, so a quote attributed to a source needs two or more whole words, such as the verbatim "someone else".
- Scare quotes count: a cited sentence with "approved" in quotes needs that word in an excerpt, or the quote marks go.

### quote-without-citation

- Fires on: a quote with no registered citation in a sentence that attributes it (says, said, writes, according to, calls, advises, recommends, warns, notes, claims, a colon), or an attributed blockquote whose attribution line has no citation. `Google's guidance says "links no longer matter for search at all".` needs the source whose excerpt holds those words.
- Doesn't fire on unattributed quoted text such as interface labels: `The button reads "Give monthly" in every locale.`

### number-not-in-source

- Fires on: a cited sentence whose percentage or multiplier number appears in none of the cited excerpts. Thousands separators are ignored, so "1,200" and "1200" match. A word multiplier matches its word or its digit.
- Limit: the number must appear as a number token in the excerpt.

### number-out-of-context

- Fires on: a cited statistic whose number appears in a cited excerpt, but every excerpt holding it shares under half of the sentence's content words (four letters or more, matched on their first five letters). "42% of readers doubled their traffic" can't borrow the 42% from "42% of respondents read the newsletter weekly".

## Register and trust

The register holds the evidence. Each source carries an id, a title, an http(s) url, a retrieved date and at least one verbatim excerpt. Its sign-off doesn't live in the register: a person other than the author checks each excerpt against the live page, and the workload's coordinator records that in the owner log of the instance the register names (`company-fleets/bin/fleet owner-record --kind claims-sign-off`, under its claim token). The check reads only that instance's ledger, at `company-fleets/fleets/corporate/owner/<instance>/`, and refuses one whose tenant differs from the register's `tenant_id`. The entry holds the SHA-256 of the sources list (sorted keys, compact separators), the signer and the author. The check looks the sign-off up by the current sources' hash.

- `register-not-signed-off`: the owner log has no sign-off for these exact sources, or the register names no instance. A source added later, such as an invented analyst report, changes the hash, and so does a `sign_off` field the author writes into the register; neither is signed.
- `register-self-signed`: the signer is the author. The owner path also refuses this when recording, after NFKC and zero-width normalization.
- `ledger-not-for-this-work`, `owner-log-missing`, `owner-log-broken`, `owner-log-truncated`, `owner-head-missing`, `owner-entry-without-lease`, `owner-not-coordinator`: the owner log can't be trusted for this register, so no sign-off counts.

The owner path stops a draft author who uses this script and the fleet commands without the claim token, once the owner has claimed the register's instance. It doesn't stop a same-user process that writes the owner root, reads the token, or claims an instance first, including a new instance id the author writes into the register and claims; `company-fleets/references/authoring-guide.md` (Owner path and its limit) states those limits.
