SYNTHETIC FIXTURE (Fixture Co): worked example and answer rationale. Every number below was worked by hand first, then executed by edu-answer-key-check against answer-key.json.

# Worked example: the sticker row, then the whole week

## The complete example

Sticker: price 2.50, cost 1.00, 40 sold in week 1.

1. Margin per sticker = 2.50 - 1.00 = 1.50. In the sheet: `=B2-C2`.
2. Profit for the week = 40 x 1.50 = 60.00. In the sheet: `=E2*(B2-C2)`. The parentheses matter: without them the sheet computes `E2*B2 - C2` = 99.00.
3. Markup = 1.50 / 1.00 = 1.5, so 150% on cost.

Why each step: the margin is what one sale adds to profit; multiplying by units turns it into the week's profit; references (B2, C2, E2) make the model update when a price changes.

## Answer rationale

| Item | Answer | How it was worked | Why a common wrong answer is wrong |
|---|---|---|---|
| Q1 notebook markup | 0.8182 | (4.00 - 2.20) / 2.20 = 0.81818 | 0.45 divides by price; that is margin on price, not markup on cost |
| Q2 week 1 gross profit | 92.85 | 60.00 + 12 x 1.80 + 9 x 1.25 = 60.00 + 21.60 + 11.25 | 175.00 is revenue, not profit |
| Q3 revenue by item | sticker 317.50, notebook 148.00, lanyard 78.00 | units summed over three weeks, times price | Week-1-only totals (100, 48, 27) come from a query with no GROUP BY over all weeks |
| Q4 best week | week 3, 203.00 | 130.00 + 40.00 + 33.00 | Week 2 has the most notebook revenue (15 x 4.00 = 60.00) but the lowest total (165.50) |
| Q5 loop total | 175.0 | 100.0 + 48.0 + 27.0 | 75.0 means the loop started at index 1 and skipped stickers |
| Q6 gross margin | 0.5306 | 92.85 / 175.00 | Dividing revenue by profit gives 1.88, which is not a share |
| Q7 decision | keep price | 0.5306 is at least the 0.50 target | - |

## Answer key check

The executed check is retained in `fleets/bcit-education/evidence/` (answer-key and incorrect-solution cases). The engine is a declared spreadsheet subset, SQLite and Python, not Excel; a formula outside the subset is reported unsupported.
