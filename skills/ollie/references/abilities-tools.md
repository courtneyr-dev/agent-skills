## Abilities Tools Reference

### Available Abilities

These are the currently registered abilities (slash-namespaced as `ollie/*`):

| Ability | Purpose |
|---------|---------|
| `ollie/manage-pages` | CRUD for WordPress pages |
| `ollie/manage-content` | Block-level operations on page content |
| `ollie/manage-blocks` | Surgical block attribute/innerHTML edits + batch content replacement |
| `ollie/manage-patterns` | Search, apply, replace block patterns |
| `ollie/create-page` | One-shot page creation from a pattern |
| `ollie/manage-templates` | Block templates and template parts |
| `ollie/manage-navigation` | WordPress navigation menus |
| `ollie/manage-global-styles` | Site-wide design tokens and fonts |

### Page Management

#### `ollie/manage-pages`
List, get, update, and delete WordPress pages. **Always use `list` first** to find page IDs. For creating new pages, prefer `ollie/create-page` — it's the fastest path.

- `list` — Get all pages with IDs (use `search` param to filter by title)
- `create` — Requires `title`; optional `content` (block markup), `status`, `template`. **Only use this when you already have prepared block markup** (e.g. after merging custom content into a pattern). For new pages, use `ollie/create-page` instead.
- `get` — Read page content by `post_id`
- `update` — Modify page by `post_id`
- `delete` — Remove page by `post_id` (set `force: true` to permanently delete)

#### `ollie/manage-content`
Block-level operations on page content. **Best for swapping sections, restructuring layouts, or bulk changes.**

- `list_blocks` — See all top-level blocks on a page
- `get_block` — Read a single block's full markup by index
- `update_block` — Replace a block with new markup
- `insert_block` — Add a block at a position
- `delete_block` — Remove a block
- `batch_update` — Replace multiple blocks in one call (indices refer to original positions)

#### `ollie/manage-blocks`
**Surgical** attribute and innerHTML edits on individual blocks. Best for tweaking styles, adding animations, changing classes, or editing text within existing blocks without replacing the full section. **Preferred tool for content replacement** — use `batch-update` to swap text across multiple blocks in one call.

- `list-sections` — Returns all top-level blocks with index, blockName, label, and text summary
- `update` — Modify a single block's attributes and/or innerHTML by `index_path`
- `batch-update` — Modify multiple blocks' attributes and/or innerHTML in one call. Each item in the `updates` array takes an `index_path` and at least one of `attributes` or `inner_html`. All changes are applied to the in-memory block tree, then serialized, validated, and saved once. **Use this for content replacement** — swap text while preserving block structure.

`index_path` is an array of zero-based integers navigating the block tree:
- `[0]` = first top-level block
- `[0, 2]` = third inner block inside the first top-level block

**Which tool to use:**
- Replace/update text content across a page → `ollie/manage-blocks` `batch-update` (preserves layout)
- Tweak a single block's color, animation, or text → `ollie/manage-blocks` `update`
- Replace or restructure an entire section → `ollie/manage-content`
- Create/delete/list pages → `ollie/manage-pages`

---

### Patterns

#### `ollie/manage-patterns`
Search, apply, and replace block patterns from the Ollie cloud pattern library. **Do NOT use this tool to compose a new page from multiple section patterns** — use `ollie/create-page` instead, which finds full-page designs in a single call. This tool is for: adding sections to an existing page, replacing sections on an existing page, or browsing available patterns.

**Workflow**:
1. `search` — Semantic cloud search. Describe what you need (e.g., "hero section with image and CTA"). Returns patterns with full block markup, auto-cached locally. Always search before building from scratch.
2. `apply` — Insert a pattern into a page. **Requires `post_id`.** Use the `pattern_slug` from search results (preferred — fast and reliable) or pass raw `content`.
3. `replace` — Swap a top-level section with a new pattern. **Requires `post_id` and `section_index`.**

**Preview/Confirm flow** (applies to both `apply` and `replace`):
1. Call with `post_id` + `pattern_slug` (confirm defaults to false) → returns `preview_url`, `preview_token`, and validation summary.
2. Call again with `post_id` + `pattern_slug` + `confirm: true` + `preview_token` → finalizes the change.

**Important**: Pattern `pattern_slug` values look like `cloud/agency/05-pricing-page`. Always run a `search` first to cache the pattern locally before attempting to apply — otherwise the apply call will fail with a "not found in local cache" error.

You can also pass a `template` param on apply/replace to set the page template (e.g. `"page-no-title"`, `"blank"`).

#### `ollie/create-page`
**The preferred tool for creating new pages.** Always use this first when a user asks to create, build, or add a page. One tool call handles everything — search, pattern selection, and page creation.

**How it works internally:**
1. Searches the pattern library and picks the **single best match**.
2. Creates the page with that one pattern. One call, one pattern, done.
3. To compose multiple specific sections, use the `pattern_slugs` array param — this is the only way to get multi-section composition, and it requires you to choose the slugs deliberately.

**Parameters:**
- `title` + `query` — use **broad, page-level queries** like "pricing page", "about page", "contact page".
- `pattern_slug` — skip search, use a single known cached pattern.
- `pattern_slugs` — array of cached pattern slugs to compose into a page. Use when you already know exactly which sections to combine (e.g. from a prior `ollie/manage-patterns` search). All patterns are concatenated in order and the page is created in one shot.
- `status` (`draft`/`publish`) — optional.
- `template` — defaults to `"page-no-title"` (full width, no title), which is standard for pattern-based pages. Only override if the user requests a specific template.

**When to use:**
- User says "create a pricing page" → `ollie/create-page` with query "pricing page". One call, done. Do NOT ask what their pricing tiers are — use placeholder content.
- User says "create a podcast page" → `ollie/create-page` with query "podcast page". Do NOT ask for the podcast name — just create it with placeholders.
- User says "create a page with pricing, testimonials, and a CTA" → still use `ollie/create-page` with a broad query like "pricing page". The tool handles composition internally.
- You already searched and know the slugs → pass `pattern_slugs` array. One call, all sections composed, page created.
- User already provided specific content in their request → pass `custom_content`. The tool returns the markup for you to merge, then use `ollie/manage-pages` create. (Only use this when the user volunteered the content — never prompt for it.)

---

### Templates & Navigation

#### `ollie/manage-templates`
Manage WordPress block templates and template parts (headers, footers, sidebars).

- `list` — Returns all templates/parts with id, slug, title, area
- `get` — Read full block markup by `template_id` or `slug`
- `update` — Replace a template's block markup by `template_id`

Set `type` to `wp_template` for page templates or `wp_template_part` (default) for headers/footers/sidebars.

#### `ollie/manage-navigation`
Manage WordPress navigation menus.

- `list` — Returns all navigation menus with id/title
- `get` — Read full block markup of a menu by `nav_id`
- `create` — Create a new navigation menu with title and optional items
- `update` — Replace menu content by `nav_id`. Use structured `items` array for simple menus or raw block markup for `content`.

Supports `core/navigation-link`, `core/navigation-submenu`, and `ollie-menu-designer/mega-menu` blocks (when Mega Menu extension is active).

---

### Global Styles & Design

#### `ollie/manage-global-styles`
Read and update site-wide design tokens and fonts. **Always call `get` first** to see current values before making changes.

- `get` — Returns current colors, typography, spacing, layout (use `sections` param to limit)
- `update` — Modify color palette hex values, font families, font sizes, spacing, layout widths
- `read-raw` — Returns the raw theme.json overrides object
- `update-raw` — Deep-merge arbitrary theme.json overrides
- `list-fonts` — All installed font families with faces
- `install-font` — Install from URL, file upload, or Google Fonts by name
- `remove-font` — Delete a font family by slug
- `list-font-collections` — Browse available font collections (Google Fonts, etc.)
