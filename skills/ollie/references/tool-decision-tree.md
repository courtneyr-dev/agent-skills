## Decision Tree: Which Tool to Use

```
Need to change site-wide colors/fonts/spacing?
  → ollie/manage-global-styles

User wants to create/build/add a new page?
  → ollie/create-page FIRST (uses a broad query to find a full-page design — one call, done)
  → Do NOT use ollie/manage-patterns to compose sections — prefer a single full-page pattern
  → ollie/manage-pages "create" only when you already have prepared block markup

Need to list/get/update/delete pages?
  → ollie/manage-pages

Need to add a section/pattern to an EXISTING page?
  → ollie/manage-patterns (search first!) → apply/replace
  → This is the correct use of manage-patterns — augmenting pages, not building them from scratch

Need to replace/update text content on a page?
  → ollie/manage-blocks "batch-update" (preserves layout, swaps content only)

Need to tweak text, colors, or attributes on a specific block?
  → ollie/manage-blocks "update"

Need to swap or restructure entire sections on a page?
  → ollie/manage-content

Need to edit header/footer/sidebar templates?
  → ollie/manage-templates

Need to edit navigation menus?
  → ollie/manage-navigation

```
