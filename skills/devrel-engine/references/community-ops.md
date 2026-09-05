# Community Operations

Day-to-day operational guidance for building and running communities. Complements the strategic frameworks in `frameworks.md` and the DevRel craft in `craft.md`. This file covers the practical mechanics of community management: engagement design, moderation, scaling, platform selection, and operational routines.

**Table of Contents:**
1. Community vs Audience
2. The 1-9-90 Rule & Engagement Ladder
3. Community Types
4. The Community Engagement Flywheel
5. Platform Selection
6. Moderation Design
7. Automated Onboarding Drip
8. Conversation Starters & Engagement Programming
9. Community Rituals
10. User-Generated Content (UGC)
11. Scaling Operations
12. Community Launch Quality Gate
13. Operational Principles

---

## 1. Community vs Audience

Before building anything, verify you're creating a community, not just an audience. The distinction determines strategy, metrics, and success criteria.

| Attribute | Audience | Community |
|-----------|----------|-----------|
| Communication | One-to-many | Many-to-many |
| Value creation | Creator/company only | Members + creator |
| Identity | "I follow X" | "I am a member of X" |
| Engagement | Passive consumption | Active participation |
| Switching cost | Low (unfollow) | High (relationships, identity, history) |
| Growth driver | Content quality | Belonging and relationships |
| Key metric | Followers/subscribers | Active members, conversations, peer replies |
| What it feels like dying | Declining views | Silence |

**The litmus test:** Are members talking to each other, or only to you? The moment member-to-member conversation exceeds member-to-staff conversation, you have a community. Before that, you have a content operation with a comments section.

---

## 2. The 1-9-90 Rule & Engagement Ladder

### The 1-9-90 Rule
In any community, roughly:
- **1%** create original content (posts, tutorials, projects, long-form contributions)
- **9%** contribute through lighter actions (replies, reactions, upvotes, shares)
- **90%** lurk — they read, consume, and benefit but don't visibly participate

Do not design only for the 1%. Lurkers get value, generate SEO traffic, and often become contributors later when the right prompt arrives. Measure reach and value delivery, not just post count.

### The 6-Step Engagement Ladder

A more granular progression model that complements the Orbit Model (O4→O1):

```
Aware → Lurker → Reactor → Contributor → Champion → Leader
  |        |         |           |            |          |
found    reads     likes/     posts/       creates    co-runs
 you     only      reacts     replies      content   programs
```

**Design for transitions, not levels.** Most programs focus on converting:
- **Lurker → Reactor** (lowest friction: add emoji reactions, polls, "introduce yourself" threads)
- **Contributor → Champion** (highest leverage: recognition, early access, direct feedback channel)

**Mapping to Orbit Model:**
- Aware + Lurker = O4 (Observers)
- Reactor = O4→O3 transition
- Contributor = O3 (Participants) and O2 (Contributors)
- Champion = O2→O1 transition
- Leader = O1 (Ambassadors)

---

## 3. Community Types

Knowing the type determines success metrics, content strategy, moderation bar, and platform choice.

| Type | Primary Value | Success Metric | Examples |
|------|--------------|----------------|----------|
| **Product community** | Support deflection + product feedback | Ticket deflection rate, time-to-resolution | Figma, Linear, Notion communities |
| **Developer community** | Ecosystem growth + advocacy | SDK adoption, contributor count, TTFS | GitHub, Stripe, Twilio DevRel |
| **Interest/hobby community** | Connection + identity | DAU/MAU, member retention, ritual participation | Subreddits, Discord servers, forums |
| **Customer success community** | Retention + expansion revenue | NPS lift, churn reduction, upsell rate | Enterprise user groups, advisory boards |
| **Professional/learning community** | Career growth + skill development | Course completion, job placements, peer help rate | Dev.to, Hashnode, alumni networks |

A single community can blend types. A developer community often has product support and professional networking functions. Identify the primary type to set the dominant strategy, then layer secondary functions.

---

## 4. The Community Engagement Flywheel

Source: brainbytes-dev. This is the member-side flywheel (how members experience community), complementing the DevRel Flywheel in `frameworks.md` (how the DevRel function operates).

```
New member joins
      ↓
Sees active discussion + welcoming culture
      ↓
Makes first contribution (comment, question, share)
      ↓
Receives response/validation from members or moderators
      ↓
Feels belonging — returns and contributes again
      ↓
Becomes a regular — welcomes and validates NEW members
      ↓
[Cycle continues — the community sustains itself]
```

**How to kickstart the flywheel:**
1. **Seed conversations** — In the early days, the community manager must start every conversation.
2. **Respond to everything** — Every post, question, and comment gets a response. Within 2 hours for first 100 members, within 24 hours after that.
3. **Spotlight members** — Feature member stories, wins, and contributions publicly.
4. **Lower the barrier for first contribution** — Polls, intros, simple yes/no reactions. Make the first step trivially easy.
5. **Introduce members to each other** — "Hey @Alex, @Jordan asked about X — I think you'd have great insight here." This models the many-to-many pattern.

**The flywheel breaks when:** new members arrive, see silence or unanswered questions, and leave. A community that opens to the public with zero existing content looks like a ghost town. Seed 20-30 high-quality posts and recruit 10-15 founding members before any public launch.

---

## 5. Platform Selection

Match the platform to member behavior, not organizational preference.

| Member Behavior | Best Platform(s) | Notes |
|----------------|-------------------|-------|
| Async Q&A, needs SEO visibility | Discourse, GitHub Discussions, Stack Overflow | Searchable, indexed, threaded |
| Real-time chat, casual interaction | Discord, Slack | High-energy but high-noise; requires active moderation |
| Long-form content and courses | Circle, Mighty Networks | Built-in monetization if needed |
| Professional networking | LinkedIn Groups | Familiar UX but limited community features |
| Developer-native workflows | GitHub Discussions, Dev.to | Low friction for people already in the tool |
| Topic-focused public discussion | Reddit (subreddit) | Strong for discovery; anti-brand culture requires authenticity |

**Platform selection rules:**
- **Where does your audience already spend time?** Go there first.
- **One platform, fully activated, before adding a second.** Multi-platform splits attention and dilutes quality.
- **Platform ≠ community.** Discord is infrastructure. The community is the people, culture, and relationships. Don't over-invest in platform features at the expense of human engagement.
- **Platform migration destroys momentum.** Moving from Slack to Discord or Discourse to Circle causes 40-60% active member loss. Only migrate when the current platform has a fundamental limitation — not to chase the newest tool.
- **Consider ownership.** Platform-owned (Reddit, Facebook Groups) means you don't control the rules or algorithm. Self-hosted/managed (Discord, Circle, Discourse) gives more control but requires more operational overhead.

---

## 6. Moderation Design

What you allow is what you become. The first 100 members watch what you enforce. If you let one snarky reply or off-topic promotion slide because the member seems valuable, you've told everyone that rules are negotiable.

### Moderation Policy Template
```
## [Community Name] Guidelines

### What this community is for
[One paragraph: purpose and who it's for]

### What we expect
- Be helpful: answer questions you know, ask questions clearly
- Be respectful: disagree with ideas, not people
- Be on-topic: [specific scope]
- Be real: no impersonation, spam, or undisclosed promotion

### What will get you removed
- Harassment, hate speech, or personal attacks
- Spam, affiliate links, or undisclosed promotion
- Sharing private information without consent
- Deliberately spreading misinformation

### Enforcement ladder
1. Post removed (no warning for clear violations)
2. Public or private warning (first-time or ambiguous violations)
3. 7-day suspension
4. Permanent ban

### Appeals
[Contact method]. We review appeals within 3 business days.
```

### Moderation Approaches by Maturity

| Community Size | Approach | Staffing |
|----------------|----------|----------|
| 0-100 | Founder moderates directly | Solo practitioner |
| 100-500 | Founder + 1-2 trusted member moderators | Volunteer |
| 500-2,000 | Dedicated community manager + volunteer moderators | 1 CM + volunteers |
| 2,000-10,000 | CM team + moderation tools + volunteer team | 2-3 CM + tools |
| 10,000+ | Full team + automated moderation + escalation protocols | Scaled team |

### Moderation Principles
- **Enforce consistently** — same rules for everyone, including Champions and early advocates
- **Assume good intent first** — most rule-breaking is accidental, especially from new members
- **Private correction, public praise** — address violations in DMs when possible; celebrate contributions publicly
- **AI-assisted moderation at scale** — auto-flag spam and clear violations, but human review for ambiguous cases

---

## 7. Automated Onboarding Drip

Complements the 90-day onboarding journey in `frameworks.md` with specific automated touchpoints. Build the drip natively in the platform (Discord bots, forum automations) — don't rely on email if members joined without providing one.

| Timing | Touchpoint | Goal |
|--------|-----------|------|
| **Day 0** (immediate) | Welcome message + invitation to introduce themselves + link to community purpose and guidelines | Orientation — they know where they are and what to do first |
| **Day 1** | Prompt: "What brought you here? What are you working on?" | First contribution — lower the barrier to posting |
| **Day 3** | Resource digest: top 3 most useful threads/guides/FAQs | Value delivery — they discover something useful without searching |
| **Day 7** | "Have you tried [specific feature/activity]?" nudge + invitation to upcoming event | Activation — connect them to a second touchpoint |
| **Day 14** | Feedback ask: "How's your experience so far? Anything confusing or missing?" | Voice — they feel heard + you surface onboarding friction |
| **Day 30** | Recognition opportunity: "You've been here a month! Here's how to contribute more deeply..." | Progression — pathway from Reactor to Contributor |

**Key rule:** If someone hasn't taken any action by Day 7, a personal (non-automated) DM from the community manager or a Champion is 10x more effective than another automated message.

---

## 8. Conversation Starters & Engagement Programming

### Weekly Prompt Templates (Adapt to Your Community)

| Day | Prompt Type | Example |
|-----|------------|---------|
| **Monday** | Goal-setting | "What's one thing you want to accomplish this week?" |
| **Wednesday** | Win sharing | "Share a win from this week — big or small." |
| **Friday** | Learning reflection | "What's something you learned this week that surprised you?" |
| **Weekend** | Casual/off-topic | "What are you reading/watching/building this weekend?" |

### Engagement-Driving Post Types
1. **Hot takes** — "Unpopular opinion: [controversial-but-not-offensive take]. Agree or disagree?" (Drives debate)
2. **This-or-that** — "Remote work or office? And why?" (Low barrier, high response)
3. **AMA / Ask Me Anything** — Feature a member, team member, or expert for Q&A (Showcasing + Educational)
4. **Challenges** — "30-day [skill] challenge — share your daily progress" (Habit formation)
5. **Advice threads** — "You can only give ONE piece of advice about [topic]. What is it?" (Concentrated value)
6. **Show your work** — "Share what you're working on. No polish needed." (Reduces intimidation)
7. **Resource sharing** — "Best [tool/book/course] you've discovered recently?" (Crowdsourced value)
8. **Storytelling** — "Tell us about a time when [relatable experience]." (Builds identity)

### Engagement Killers to Avoid
- Questions that can be answered in one word
- Prompts you wouldn't respond to yourself
- Reusing the same prompt format too frequently
- Making prompts about the brand instead of the members

---

## 9. Community Rituals

Rituals turn a group into a community. They create predictability, shared experience, and identity.

### Ritual Types
1. **Welcome ritual** — How new members are greeted (intro thread, welcome message, buddy system, welcome committee)
2. **Regular events** — Weekly office hours, monthly AMAs, bi-weekly build sessions
3. **Celebration rituals** — Acknowledging milestones (100th post, member anniversaries, project launches, personal achievements)
4. **Inside language** — Community-specific terms, acronyms, jokes, or phrases that signal belonging
5. **Shared challenges** — Monthly or quarterly group challenges with collective progress
6. **Annual traditions** — Yearly events members look forward to (awards, retrospectives, summits, hackathons)

### Making Rituals Stick
- **Start with one** — don't launch 5 rituals simultaneously
- **Be consistent** — same day, same time, same format. Predictability builds habit.
- **Make them participatory** — rituals that require member involvement create stronger bonds than rituals members watch
- **Let them evolve** — the best rituals get adapted by the community over time
- **Document them** — pin rituals in a welcome guide so new members can participate immediately

---

## 10. User-Generated Content (UGC)

UGC is the signal that you have a real community. When members create content about your product/community without being asked, you've crossed the line from audience to community.

### Making UGC Easy
1. **Templates and frameworks** — Fill-in-the-blank templates members can customize and share
2. **Branded hashtags** — Create a hashtag and actively reshare content that uses it
3. **Time-bound challenges** — Clear parameters, limited duration, low bar for entry
4. **Features and spotlights** — "Member of the week" or "Project spotlight" programs that reward contribution
5. **Co-creation opportunities** — Let members vote on features, content topics, event themes

### UGC Ethics
- Always ask permission before resharing member content on official channels
- Credit the creator prominently and specifically
- Showcase a variety of members, not just the loudest voices
- Respond to every UGC submission, even if you don't feature it — acknowledgment sustains participation

---

## 11. Scaling Operations

Signs you need to scale: response time exceeds 4 hours consistently, moderation queue grows faster than you clear it, no single person can summarize what happened last week.

### Scaling Sequence (in this specific order)

| Step | Action | Why This Order |
|------|--------|----------------|
| **1** | **Document everything** | Playbooks, moderation guidelines, onboarding scripts. Undocumented processes cannot be delegated. |
| **2** | **Promote community moderators** | Trusted members make excellent part-time mods — lower cost, higher community trust, deep context. |
| **3** | **Automate the repetitive** | Welcome messages, FAQ responses, link-to-docs for common questions. Bots, Zapier, platform-native automations. |
| **4** | **Hire a community manager** | When paid staff is needed, hire for empathy and writing quality first, platform expertise second. |
| **5** | **Add a second platform only if members demand it** | Resist the urge to be everywhere. Every platform splits attention and quality. |

### The 3-Layer Model for Scaled Communities
1. **Core team** (paid) — Community managers who set strategy, create content, manage operations
2. **Super members** (volunteer or incentivized) — Active members who moderate, welcome newcomers, and spark conversations
3. **General members** — The broader community participating at various engagement levels

### Identifying Super Members
- Consistently contribute quality content
- Help other members without being asked
- Model the culture you want to see
- Have been active for 4+ weeks minimum

Invite them to a private group. Give them recognition. Include them in decisions. Never exploit their goodwill — offer genuine value in return.

---

## 12. Community Launch Quality Gate

Before launching or opening a community publicly, verify all of these:

- [ ] Community purpose is clear in one sentence
- [ ] Value proposition: members get something they can't get elsewhere
- [ ] Community guidelines are written, posted, and accessible
- [ ] Onboarding flow exists for new members (welcome message, intro prompt, resource links)
- [ ] 20-30 seed posts exist with genuine discussion already happening
- [ ] 10-15 founding members are committed to daily participation for the first 4+ weeks
- [ ] At least 1 recurring ritual or event is scheduled (weekly thread, office hours, etc.)
- [ ] Response time target is set (and the team can actually meet it)
- [ ] Moderation policy is documented with an enforcement ladder
- [ ] Metrics tracking is in place (at minimum: DAU/MAU, new member activation, peer reply rate)
- [ ] Community manager or designated person is committed to being the most active participant for 18+ months
- [ ] The community feels member-shaped, not brand-shaped — the layout, prompts, and tone signal "this is for you" not "this is our marketing channel"

---

## 13. Operational Principles

Named principles to reference in recommendations. These come from synthesized best practices across community management literature and practice.

- **"Community is a garden, not a broadcast channel."** You tend it; you don't control it. Create conditions for good things to grow, then get out of the way.
- **"Value before extraction."** Give generously before asking anything. A survey, testimonial request, or referral ask lands differently when you have a deposit history. Aim for a 10:1 give-to-ask ratio.
- **"The first 50-100 members set the tone for the next 100,000."** Culture is established early and extremely hard to change later. Recruit founding members intentionally.
- **"Communities die from neglect, not conflict."** Silence kills faster than arguments. An unanswered question is more damaging than a heated debate.
- **"Moderation is culture enforcement."** What you allow, you encourage. What you remove, you discourage. Apply rules from day one, consistently, to everyone.
- **"Small and engaged beats large and passive."** 100 daily active members helping each other are more valuable than 50,000 silent followers. Report DAU/MAU, not raw member count.
- **"Community managers are the most important hire."** A great community manager is worth more than a great marketing campaign. Hire for empathy and writing quality first.
- **"One platform, fully activated, before expansion."** Resist the urge to be on every platform. Each additional channel splits attention, dilutes quality, and multiplies operational overhead.
