# Page Creation and Recommended Workflows

## Page Creation Philosophy

**Speed first. Create the page immediately, refine later.**

When a user says "create a page", your job is to get a page on screen as fast as possible. Do NOT stop to ask for content details — business name, tagline, pricing tiers, podcast name, team members, etc. Use the pattern's built-in placeholder content as-is. The user can ask for content changes after the page exists.

**Rules:**
1. **Never prompt for content before creating a page.** If the user says "create a podcast page", create it immediately with placeholder content. Do not ask "What's your podcast called?" or "What episodes should I list?" — just create the page.
2. Use `ollie/create-page` with a **broad, page-level query** (e.g. "pricing page", "about page") — not section-level queries like "hero with CTA" or "pricing table".
3. **Do NOT** use `ollie/manage-patterns` to search for and compose individual sections when the user asks to create a page. That tool is for adding/replacing sections on existing pages.
4. Only compose from multiple patterns if: (a) the user explicitly asks for a custom layout or named sections, OR (b) `ollie/create-page` returns no suitable full-page match and you've told the user.
5. If the user lists ingredients ("I want pricing, testimonials, and a CTA"), still search for a full-page design first — the library likely has a page that includes those elements. Only break into sections as a fallback.
6. After creating the page, let the user know it's ready and that they can ask for content updates, section swaps, or styling changes.

---

## Recommended Workflows

### Building a Page
**Always create first, ask questions later.** Do not prompt the user for content details before creating the page. Use placeholder content and let them refine afterward.

**Fast path (default):** Use `ollie/create-page` with a title and a broad page-level query (e.g. "pricing page"). One tool call — finds a full-page design or composes sections, creates the page with placeholder content, done. Tell the user the page is ready and they can request content changes.

**With custom content the user already provided:** If the user included specific content in their request (not you asking for it), pass it as `custom_content`. The tool returns the pattern markup for you to merge, then use `ollie/manage-pages` → `create`.

**Refining after creation:** Use `ollie/manage-blocks` for content updates (text, colors, animations) or `ollie/manage-content` for section-level changes. This is the time for details — after the page exists.

**Adding sections to an existing page:** Use `ollie/manage-patterns` → `search` then `apply` to add patterns to a page that already exists. This is the correct use of manage-patterns — augmenting pages, not creating them from scratch.

### Customizing Global Design
1. **Read current state**: `ollie/manage-global-styles` → `get`
2. **Update tokens**: `ollie/manage-global-styles` → `update` to change palette colors, fonts, spacing
3. **Install fonts**: `ollie/manage-global-styles` → `list-font-collections` → `install-font`
4. All pages automatically reflect global style changes.

### Replacing Content
**When the user wants to update text on an existing page** (e.g. paste in new copy, replace placeholder content, update pricing details):

1. **Read the page structure**: `ollie/manage-blocks` → `list-sections` to see all top-level blocks with summaries.
2. **Batch-update content**: `ollie/manage-blocks` → `batch-update` with an `updates` array. Each item targets a block by `index_path` and provides `inner_html` (new text) and/or `attributes` (light style tweaks like fontSize, textColor).
3. **Preserve block structure**: Do not reconstruct block markup or create new blocks. Use what's already there — only swap the text content and adjust styles if asked.

**Only reach for `ollie/manage-content` or `ollie/manage-patterns`** if the user explicitly asks for new sections, layout changes, or structural rework.
