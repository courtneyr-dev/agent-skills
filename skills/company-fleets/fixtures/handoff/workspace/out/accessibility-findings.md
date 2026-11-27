# Accessibility findings for Client A staging (SYNTHETIC)

1. Contact form: fields have no programmatic or visible labels (WCAG 2.2 SC 1.3.1, 3.3.2).
   Steps: open /contact, move focus to each field with Tab. Observed: no label is announced or shown.
2. Donate menu: opens on hover only; keyboard users can't reach its items (SC 2.1.1).
   Steps: Tab to the main menu, press Enter or Space on Donate. Observed: nothing opens.
3. Newsletter modal: focus is lost after closing (SC 2.4.3).
   Steps: open the modal, press Escape. Observed: focus lands on the document body.

Not claimed: WCAG conformance of the site. Assistive-technology checks were simulated.
