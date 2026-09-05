# DevRel Practitioner Craft

Hands-on methodologies, templates, quality standards, and ethical guidelines for the day-to-day work of developer relations. These complement the strategic frameworks in `frameworks.md` — strategy tells you *what* to do; this file tells you *how* to do it well.

**Table of Contents:**
1. Advocacy Ethics
2. Communication Voice & Style (incl. "Reduce Workload" test, "Use it yourself first")
3. Developer Experience (DX) Engineering
4. DX Audit Framework
5. The "DX Before Content" Principle
6. Product Feedback Loop
7. Tutorial & Technical Content Craft
8. Conference Talk Proposals
   - 8b. Live Demo Craft (3-act structure, safety checklist, narration)
   - 8c. Workshop & Hackathon Templates
9. Community Support Response Patterns
10. Content Quality Gates
11. DevRel Practitioner Success Metrics
12. Localization Considerations
13. Friction Logs
14. DevRel Organizational Design

---

## 1. Advocacy Ethics

Non-negotiable principles. Breaking any of these destroys the trust that is the entire foundation of DevRel work.

- **Never astroturf.** Authentic community trust is your entire asset. Fake engagement, fake reviews, fake community notes, or sock puppet accounts destroy credibility permanently. If discovered, recovery takes years.
- **Be technically accurate.** Wrong code in tutorials damages credibility more than publishing no tutorial. Test every snippet. Run every command. Verify every output.
- **Represent the community to the product, not just the product to the community.** You work *for* developers first, then the company. If the product has a real limitation, say so honestly. Developers respect honesty; they despise spin.
- **Disclose relationships.** Always be transparent about your employer when engaging in community spaces (Reddit, Stack Overflow, forums, Discord). Undisclosed paid advocacy is astroturfing.
- **Don't overpromise roadmap items.** "We're looking at this" is not a commitment. "This is on our roadmap" creates expectations. Be precise: "I've shared this feedback with the product team. I can't commit to a timeline, but here's the issue to follow for updates."
- **Respect community norms.** Each community (subreddit, Discord, forum) has its own culture. Adapt to it. Don't show up with corporate energy in a casual space.
- **Give credit.** When community members identify bugs, suggest features, or create content, credit them publicly and specifically.

---

## 2. Communication Voice & Style

DevRel communication should be distinguishable from marketing. These patterns build trust.

**Be a practitioner, not a spokesperson.** "I hit this wall on my last project" is more credible than "our platform enables seamless integration." Speak from personal experience building real things.

**Lead with empathy, follow with solution.** Acknowledge frustration before explaining the fix. "I ran into this myself, so I know it's painful" is more effective than jumping to the answer.

**Be honest about limitations.** "This doesn't support X yet — here's the workaround and the issue to track" builds more trust than silence or deflection. Developers respect transparency about constraints.

**Quantify developer impact.** "Fixing this error message saves every new developer ~20 minutes of debugging" is more compelling than "this is a common pain point." Numbers make the case to both developers and product teams.

**Use community voice.** "Three developers at the conference asked the same question, which means hundreds more hit it silently" is evidence-based advocacy. Aggregate community signals into patterns.

**Don't use marketing language in technical contexts.** Avoid "powerful," "seamless," "best-in-class," "enterprise-grade" in developer-facing content. Use specific, measurable claims instead. "Processes 10K requests/second with p99 latency under 50ms" beats "blazing fast performance."

**Match the channel:**
- GitHub issues: Technical, specific, actionable. Include code snippets and version numbers.
- Stack Overflow: Answer the question first, then provide context. Include runnable code.
- Discord/Slack: Conversational, quick, helpful. Link to deeper resources.
- Conference talks: Narrative-driven, demo-heavy, problem-first. No product pitches.
- Blog posts: Educational, thorough, opinionated. Show your reasoning.
- Social media: Authentic, concise, community-aware. Share others' work generously.
- Reddit: Value-first, never promotional. Be a community member who happens to work on the product, not a marketer wearing a community costume.

**The "Reduce Workload" Litmus Test** (Chris Heilmann, Developer Advocacy Handbook):
Before publishing or sharing any content, ask: does this reduce work for the developer, or add to their pile? If your message means less work — a solved problem, a shortcut, a fix for a common frustration — developers will pay attention. If it means extra work on top of what's already on their plate (learn a new API, migrate to a new version, adopt a new tool without clear benefit), you'll lose them. Content that passes this test: "Here's how to do [thing you already need to do] in half the time." Content that fails: "Check out our new feature that requires you to refactor your auth layer." The second might still be valuable, but it needs to lead with the payoff, not the work.

**Use it yourself first.** Heilmann's methodology: when something new ships, access it as an outside developer would. Build something with it. Document what you built. Write about how you built it. Now you have half an article, a demo, and genuine experience with the friction points — all before writing a single piece of advocacy content.

---

## 3. Developer Experience (DX) Engineering

DX engineering treats the developer's experience of using your platform as a product in itself. DX improvements compound — fixing an error message helps every future user forever, while a tutorial has a shelf life.

### Core DX Surfaces to Audit
- **Time-to-first-success (TTFS):** How long from "I just heard about this" to "I did something meaningful with it." Target: under 15 minutes for most platforms, under 5 for simple tools.
- **Onboarding flow:** Account creation → environment setup → first API call/first build/first deploy. Every step is a potential drop-off point.
- **Documentation:** Can developers find what they need? Is the search good? Are code examples runnable? Are error codes documented?
- **SDKs and libraries:** Do they have TypeScript types? Do they match the API surface? Are they idiomatic for the language?
- **Error messages:** Does every error code have a human-readable message, a likely cause, and a suggested fix? "Unknown error" is a DX failure.
- **Authentication:** How many steps from "I want to try this" to "I have a working API key/token"? Each step loses 10-20% of potential users.
- **Pricing clarity:** Can a developer estimate their costs before committing? Unpredictable pricing is the #1 complaint across AI/vibe coding platforms.

### DX Improvement Prioritization
Rank DX fixes by: (frequency of encounter) × (severity of friction) × (stage in journey). A high-frequency, high-severity issue at the Evaluate/Learn stage kills adoption before it starts.

---

## 4. DX Audit Framework

A structured methodology for measuring and improving developer experience. Run this quarterly or before major launches.

```
# DX Audit: Time-to-First-Success Report

## Methodology
- Recruit 5 users at [target experience level for your audience]
- Ask them to complete: [specific onboarding task — e.g., "build and publish a simple app"]
- Observe silently, note every friction point, measure time at each phase
- Grade each phase: 🟢 < 5 min | 🟡 5-15 min | 🔴 > 15 min

## Onboarding Flow Analysis

### Phase 1: Discovery (Target: < 2 minutes)
| Step | Observed Time | Friction Points | Severity |
|------|--------------|-----------------|----------|
| Find docs/getting-started from main page | | | |
| Understand what the product does | | | |
| Locate the quickstart or first action | | | |

### Phase 2: Account/Environment Setup (Target: < 5 minutes)
| Step | Observed Time | Friction Points | Severity |
|------|--------------|-----------------|----------|
| Create account or install tool | | | |
| Get credentials/API key/access | | | |
| Complete environment setup | | | |

### Phase 3: First Success (Target: < 10 minutes)
| Step | Observed Time | Friction Points | Severity |
|------|--------------|-----------------|----------|
| Follow quickstart to first meaningful result | | | |
| Verify the result works as expected | | | |
| Understand what to do next | | | |

## Top 5 DX Issues by Impact
1. [Issue] — [frequency: X of 5 users hit this] — [severity]
2. ...

## Recommended Fixes (Priority Order)
1. [Fix] — [effort: Low/Med/High] — [impact: compound reach]
2. ...
```

**Adaptation for non-developer audiences:** If your community serves non-technical users (SMB owners, "vibe coders," content creators), replace "first API call" with "first meaningful result" and adjust time targets upward. The methodology still applies — observe, measure, identify friction, fix.

---

## 5. The "DX Before Content" Principle

A foundational priority rule for DevRel practitioners:

**Prioritize DX fixes over content creation.** DX improvements compound forever. A better error message helps every developer who ever encounters it. A tutorial helps only those who find and read it, and it decays as the product changes.

Priority order:
1. **Fix broken DX** — error messages, SDK bugs, missing types, auth friction, broken quickstarts
2. **Improve existing DX** — clearer docs, better examples, smoother onboarding
3. **Create content for existing friction** — tutorials addressing known pain points
4. **Create content for growth** — new tutorials, showcases, comparison content

This doesn't mean "never create content." It means when you have limited bandwidth (and solo practitioners always do), fix the product experience before adding marketing on top of a broken funnel.

---

## 6. Product Feedback Loop

A systematic process for translating community signals into product improvements. This is DevRel's most valuable function — and the one most often done informally rather than systematically.

### The Monthly "Voice of the Developer" Report

Compile monthly for product/engineering leadership:

```
# Voice of the Developer — [Month/Year]

## Top 5 Pain Points by Evidence Weight

### 1. [Issue Title]
- GitHub issues: [X] open, [Y] in last 30 days
- Community mentions: [X] Discord/forum threads, [Y] Reddit posts
- Support tickets: [X] related tickets
- Conference/event signals: [mentioned at X events]
- Severity: [Blocker/High/Medium/Low]
- Journey stage affected: [where in the funnel this hurts]
- Competitive context: [how competitors handle this]
- User story: "As a [persona], I need [thing] so that [outcome]"
- Suggested priority: [with rationale]

### 2. ...

## Feature Requests by Community Demand
| Feature | GitHub 👍 | Forum Votes | Mentions | Status |
|---------|-----------|-------------|----------|--------|
| [Feature] | [count] | [count] | [count] | [New/Tracked/Planned/Shipped] |

## DX Wins Shipped This Month
- [Fix]: [Impact — e.g., "reduced auth setup time from 12 min to 3 min"]
- [Attribution: community issue #X, reported by @username]

## Sentiment Snapshot
- Overall: [Positive/Mixed/Negative — with trend arrow]
- Key quote (positive): "[quote]"
- Key quote (critical): "[quote]"
```

### Closing the Loop
When a community-requested DX fix or feature ships:
1. Update the original GitHub issue/forum thread with the fix
2. Thank the reporter(s) by name
3. Announce in community channels, attributing the request to the community
4. Include in changelog with community attribution
This "close the loop" pattern is what turns frustrated reporters into loyal advocates.

---

## 7. Tutorial & Technical Content Craft

### The "Viral Tutorial" Structure
Based on patterns from highest-performing developer tutorials across platforms:

1. **Start with the end result, not "In this tutorial we will..."** — Show the demo, the screenshot, the live app. Let people see what they're building before they invest time.

2. **State what's needed upfront** — Account requirements, tools, time estimate. No surprises at step 7.

3. **Explain the WHY before the HOW** — Explain the architectural decision before the code. "Most systems poll for updates. That's inefficient. Instead, we'll use SSE because..." This teaches engineering judgment, not just syntax.

4. **Every command should show expected output** — If a developer runs a command and sees something different from what you documented, they stop trusting the tutorial. Include expected outputs, and note OS-specific variations.

5. **Include failure modes** — "If you see error X, it usually means Y. Fix it by Z." This is what differentiates a great tutorial from a mediocre one. Developers don't follow happy paths — they hit errors.

6. **End with what they built AND what's next** — Recap the concepts taught (not just the steps), then provide 2-3 natural next paths.

### Written Content Quality Checklist
- [ ] Every code sample runs without modification on the specified environment
- [ ] Expected output is shown for every command
- [ ] OS-specific gotchas are noted (Windows PowerShell vs Bash, etc.)
- [ ] Prerequisites are stated upfront with version numbers
- [ ] Time estimate is honest (tested with a real person, not the author)
- [ ] Feature status is labeled (GA / beta / preview / experimental)
- [ ] Links are tested and not behind auth walls
- [ ] Error scenarios are documented with solutions

---

## 8. Conference Talk Proposals

```
# Talk Proposal: [Title That Promises a Specific Outcome]

Category: [Engineering / Architecture / Community / DevRel / etc.]
Level: [Beginner / Intermediate / Advanced]
Duration: [25 / 45 minutes]

## Abstract (150 words max, public-facing)
[Start with the developer's pain or a compelling question. NOT "In this talk
I will..." but "You've probably hit this wall: [relatable problem]. Here's
what most teams do wrong, why it fails at scale, and the pattern that works."]

## Detailed Description (300 words, for reviewers)
[Problem statement with evidence: GitHub issues, SO questions, survey data.
Proposed solution with live demo. Key takeaways. Why this speaker: relevant
experience and credibility signal.]

## Takeaways (exactly 3)
1. Attendees will understand [concept] and know when to apply it
2. Attendees will leave with [working code pattern / template / framework]
3. Attendees will know the [2-3 failure modes / anti-patterns] to avoid

## Speaker Bio (2 sentences)
[What you've built and shipped, not your job title.]

## Previous Talks
- [Conference, Year] — [Title] ([recording link])
```

**Acceptance rate target:** 60%+ at tier-1 conferences indicates strong topic selection and proposal quality. If below 40%, the proposals need work on specificity and evidence.

---

## 8b. Live Demo Craft

Source: securesigner/AbsolutelySkilled.

Live demos fail when they are too ambitious. Scope ruthlessly. A 90-second demo that works is worth more than a 30-minute slide deck.

### The 3-Act Demo Structure
1. **Setup** (30 seconds) — Show the starting state. "Here's an empty project / a broken feature / a slow endpoint."
2. **Build** (3-5 minutes) — Write the code live. Narrate what you type and why. Never type silently for more than 10 seconds — the audience disengages.
3. **Payoff** (30 seconds) — Run it. Show the working result. Celebrate briefly.

### Demo Safety Checklist
Before any live demo (conference talk, livestream, office hours):

- [ ] **Pre-install all dependencies** — never run `npm install` or `pip install` live
- [ ] **Have a fallback git branch** with the finished working state
- [ ] **Record a backup video** of the demo running successfully in case everything breaks
- [ ] **Use large fonts** — 24pt minimum in terminal, 20pt minimum in editor
- [ ] **Disable all notifications** — Slack, email, calendar, system popups, phone
- [ ] **Test on exact presentation hardware/display** — not just your dev machine
- [ ] **Use environment variables for secrets** — never paste API keys on screen
- [ ] **Cache all API responses** if the demo makes HTTP calls — conference Wi-Fi fails at every venue
- [ ] **Pre-type long commands** in a scratchpad you can copy-paste from, rather than typing complex commands live
- [ ] **Have a "skip ahead" plan** — if something breaks, know how to jump to the next working state

### Narration Principle
Silence while typing causes the audience to lose focus within 10 seconds. Practice narrating every keystroke aloud: "I'm setting the API key as an environment variable because we never hard-code credentials." This feels unnatural in practice; it's essential in performance.

---

## 8c. Workshop & Hackathon Templates

### Workshop Structure (90-120 minutes)
```
[0:00–0:10]  Introduction + environment check
             (Confirm everyone has prerequisites installed. Fix issues NOW, not mid-workshop.)
[0:10–0:25]  Concept overview (slides, max 10 slides)
             (Frame the problem. Explain WHY before HOW.)
[0:25–1:10]  Guided hands-on (step-by-step, instructor-led)
             (This is the core. Go slow. Wait for stragglers. Have TAs circulating.)
[1:10–1:25]  Free exploration
             (Attendees extend the project on their own. Provide 3-5 challenge prompts.)
[1:25–1:30]  Wrap-up + resources + feedback form
             (Share repo link, docs link, community link. Collect feedback immediately.)
```

**Workshop rules:**
- Publish the prerequisites and setup instructions 48+ hours before the event
- Have at least 1 teaching assistant per 15 attendees
- Provide a completed reference repo that attendees can clone if they fall behind
- Test the entire workshop end-to-end on a fresh machine before delivery
- Collect feedback on a 1-5 scale for: pace, clarity, relevance, overall value

### Hackathon Planning Checklist
- [ ] Define clear judging criteria before the event (not after)
- [ ] Provide starter templates / boilerplate repos that work out of the box
- [ ] Have mentors available during the entire hacking period
- [ ] Set realistic scope — 24-hour hackathons need APIs that work in under 5 minutes
- [ ] Prepare prizes developers actually want (cloud credits, conference tickets, hardware > swag)
- [ ] Collect submissions via GitHub repos, not slide decks
- [ ] Partner with integration providers for category prizes (converts sponsors into ecosystem partners)
- [ ] Plan for post-hackathon follow-up — winners should be featured in community, invited to Champion program

---

## 9. Community Support Response Patterns

Templates for common community interaction types. Adapt voice to platform norms.

### Bug Report (with reproduction steps)
```
Thanks for the detailed report and reproduction case — that makes debugging much faster.

I can reproduce this on [version]. The root cause is [brief explanation].

**Workaround (available now):**
[code or steps]

**Fix:** Tracked in #[issue]. I've bumped priority given the reports.
Target: [version/milestone]. Subscribe for updates.

Let me know if the workaround doesn't work for your case.
```

### Feature Request
```
Great use case — you're not the first to ask. [#related-issue] and
[#related-issue] cover similar ground.

I've added this to our [backlog/roadmap board] with context from this thread.
I can't commit to a timeline, but I want to be transparent: [honest
assessment of likelihood and priority].

In the meantime, here's how some community members work around this today:
[link or approach].
```

### Frustrated User
```
I hear you — [specific acknowledgment of their frustration, not generic].
That shouldn't be that hard, and I'm sorry it is right now.

[If there's a fix:] Here's what should work: [solution].
[If there's no fix yet:] I've flagged this with the team. Here's the issue
to follow: [link]. I'll update it when I have news.

[If they're comparing to a competitor:] Fair point about [competitor] —
they do handle [specific thing] well. We're working on [honest status].
```

### First-Time Community Member
```
Welcome! Great [question / project / observation].

[Direct, helpful answer — don't make them work for it.]

A few resources that might help as you get started:
- [Most relevant resource]
- [Second resource]

And feel free to share what you're building — we love seeing what
people create!
```

---

## 10. Content Quality Gates

Standards that should be verified before publishing any DevRel content.

### Code Content
- [ ] Every code sample runs without modification on stated environment/version
- [ ] Expected output documented for every command
- [ ] Dependencies/prerequisites stated with version numbers
- [ ] Error scenarios addressed
- [ ] Feature labeled as GA / beta / preview (never publish beta-feature tutorials without labeling)

### Community Engagement
- [ ] First response to community questions within 24 hours (business days)
- [ ] Acknowledgment within 4 hours during business hours
- [ ] Employer disclosed when engaging in external community spaces
- [ ] No unattributed promotional language in earned communities

### Stakeholder Communication
- [ ] Business impact framed in revenue/retention/cost terms, not activity metrics
- [ ] Claims supported by data, not anecdotes
- [ ] Roadmap items communicated with appropriate uncertainty language

---

## 11. DevRel Practitioner Success Metrics

A personal scoreboard for the DevRel practitioner — different from community health metrics (which measure the community) and business value metrics (which measure ROI). These measure *your effectiveness as an advocate*.

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time-to-first-success for new users | ≤ 15 min | DX audit observations |
| Developer/user NPS | ≥ 8/10 | Quarterly survey |
| Community first-response time | ≤ 24 hours (business days) | Platform analytics |
| Tutorial/guide completion rate | ≥ 50% | Analytics events or scroll depth |
| Community-sourced DX fixes shipped | ≥ 3/quarter | Track attribution in issues |
| Conference talk acceptance rate | ≥ 60% at target-tier conferences | Track submissions vs acceptances |
| New user activation rate | ≥ 40% complete first meaningful action within 7 days | Product analytics |
| SDK/docs bugs filed by community | Decreasing month-over-month | GitHub/forum tracking |
| Content production/distribution | Meets cadence commitments | Self-tracking |

---

## 12. Localization Considerations

For communities with international audiences, localization unlocks non-obvious growth.

- **Multi-language creator content** drives growth in underserved markets. Competition for attention is dramatically lower in non-English markets, and creator costs are often 3-5x cheaper.
- **Community programs for non-English communities** require local champions, not just translated content. A Brazilian Portuguese Discord channel needs a Portuguese-speaking moderator, not just a translation bot.
- **Documentation localization** has the highest compound ROI of any localization investment — docs are referenced repeatedly, while event content is consumed once.
- **Start with demand signals:** Check traffic analytics for geographic concentration. If 15% of users are from Brazil, investing in Portuguese content has a clear business case.
- **Don't machine-translate community interactions.** Automated translation of support responses feels impersonal. Either have a native speaker or respond in English with a note that you wish you could respond in their language.

---

## 13. Friction Logs

Source: Apollo GraphQL DX Audit framework. A friction log is the practitioner-level artifact that sits between a DX audit (high-level assessment) and product feedback (formatted for engineering). It captures the emotional and functional experience of completing a task step-by-step.

### When to Create a Friction Log
- During DX audits (structured program)
- When personally hitting friction while building content or demos
- When a community member reports a confusing workflow
- When onboarding a new team member and observing their experience

### Friction Log Template
```
FRICTION LOG
Task: [What the user is trying to accomplish]
Persona: [Which persona/journey stage]
Date: [When the audit was conducted]
Auditor: [Who experienced this]

| Step | Action Taken | Expected Result | Actual Result | Emotional Temp | Friction Level |
|------|-------------|-----------------|---------------|----------------|----------------|
| 1 | [What I did] | [What I expected] | [What happened] | 😊/😐/😤/🤬 | None/Low/Med/High/Blocker |
| 2 | ... | ... | ... | ... | ... |

TOTAL TIME: [How long the full task took]
TARGET TIME: [How long it should take]

FRICTION POINTS (ranked by severity):
1. [Most severe friction — what happened, why it's a problem, suggested fix]
2. [Second most severe — etc.]

ACTION ITEMS:
- [ ] [Specific fix with owner and priority]
- [ ] [Content to create to address this]
- [ ] [Doc update needed]

NOTES:
[Anything else worth capturing — workarounds attempted, community threads about this, competitor comparison]
```

### Using Friction Logs
- Share with product/engineering as evidence for DX investment
- Use as the basis for tutorials (write the tutorial that would have prevented the friction)
- Track over time to measure DX improvement (re-run the same friction log after fixes ship)
- Reference in performance reviews as evidence of cross-functional DX impact

---

## 14. DevRel Organizational Design

Where DevRel sits in an organization determines what it can accomplish. These principles are informed by industry experience (Angie Jones, Matt Palmer, Lewko & Parton) and common failure modes.

### Organizational Independence
- **DevRel should not report to Marketing.** When Marketing directs DevRel content, the advocate becomes "tainted" — community credibility erodes because content is perceived as sales collateral. (Angie Jones: "I encourage companies to keep their Marketing and Developer Relations departments separate.")
- **DevRel should not report to Sales.** Sales incentives (quota, pipeline) conflict with community-first advocacy. A DevRel practitioner who needs to hit a sales number will eventually compromise authenticity.
- **Best-case: DevRel reports to Product or Engineering.** This aligns incentives — DevRel improves the product through community feedback, and Product gives DevRel the technical credibility to be effective.
- **Acceptable: DevRel as its own function.** Reporting to a VP or C-level who understands developer audiences. Requires executive sponsorship.
- **Reality check:** Many DevRel practitioners sit in Marketing, Sales, or hybrid structures. If you're in this situation, establish clear boundaries on content editorial independence, even if reporting lines aren't ideal.

### Collaboration Without Subordination
DevRel should collaborate closely with Marketing, Sales, and Product — but not take directives from them.

| Team | DevRel Provides | DevRel Receives |
|------|----------------|-----------------|
| **Marketing** | Authentic technical voice, community insights, content review for technical accuracy | Campaign awareness, brand assets, event logistics, budget |
| **Sales** | Technical credibility on prospect calls, DRQLs with context, competitive intelligence from community | Pipeline data, customer feedback, enterprise use cases |
| **Product** | Community feedback, DX audits, friction logs, feature request data with evidence | Roadmap visibility, early access to features, engineering time for DX fixes |
| **Engineering** | Bug reports with reproduction, community-sourced testing, SDK feedback | Code reviews, technical accuracy checks, API design input |
| **Support** | Deflection content (docs, tutorials, FAQ), community-answered question data | Ticket pattern data, common failure modes, escalation paths |

### The "Content Veto" Principle
A DevRel practitioner should have the right to decline producing content they don't believe genuinely helps the community. "I will only produce content if I believe it truly adds value for my community" (Angie Jones). This is not insubordination — it's brand protection. An advocate who publishes content they don't believe in damages the trust that makes them effective.

### Rotation Models
Some teams (notably Netlify) rotate developer advocates between pure advocacy work and pure engineering work. Benefits: keeps engineering skills sharp, builds product empathy, generates content ideas from direct building experience, and prevents advocacy burnout. Consider quarterly or semi-annual rotations.

### Solo Practitioner Realities
Many DevRel functions start with a single person. When you are the entire DevRel team:
- You are simultaneously strategist, content creator, community manager, event organizer, and product feedback synthesizer
- Prioritize ruthlessly using the energy-level framework — not everything can happen every week
- Build volunteer Champions early to create leverage before headcount arrives
- Document everything as if someone else will need to pick it up — because eventually they will
- The biggest risk is "solo hero syndrome" — building programs that only work because of you personally. Build systems, not dependencies.
