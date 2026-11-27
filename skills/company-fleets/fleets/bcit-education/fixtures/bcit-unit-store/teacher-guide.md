SYNTHETIC FIXTURE (Fixture Co): teacher guide for a demonstration unit. Fixture Co, its student-run store and every number here are fictional. No standards mapping in this unit is verified; see alignment.json.

# Teacher guide: pricing and sales data for the student-run store

## Context

- Course: Business and Computer Applications, grades 10-12 (teaching assignment and certification not verified).
- Duration: five 45-minute periods.
- Prerequisites: percent and decimal operations; entering a value and a formula in a spreadsheet cell.
- Resources: student handout, `sales-data.csv` (synthetic), any spreadsheet program the school provides, the SQLite browser or command line on lab machines, printed copies of the handout and data.
- Technology constraints: no accounts, no internet needed after files are copied; every task has a paper route.

## Objectives

- O1 (apply): calculate markup, contribution margin and weekly gross profit with formulas built from cell references.
- O2 (analyze): query a sales table to compare revenue by item and by week, and explain which item drives profit.
- O3 (evaluate): recommend and justify one price change in a memo to the store manager.

## Sequence

| Period | Focus | Evidence you collect |
|---|---|---|
| 1 | Fixed and variable costs; markup versus margin, using the sticker example | Exit ticket T0 (recall check, formative only) |
| 2 | Worked example, then guided practice building the profit sheet | Spreadsheet T1 draft |
| 3 | Independent application: finish T1 and change the notebook price | T1 product and one-sentence explanation |
| 4 | Sales table: two queries, guided then independent | T2 result sets and interpretation |
| 5 | Pricing memo and peer feedback | T3 memo |

## Guided practice

Model the sticker row on the projector: type 2.50 in B2 and 1.00 in C2, then write `=E2*(B2-C2)` in D2 and say why each reference is there. Ask the class to predict D2 before you press Enter. Then fade: students write the notebook row while you only name the cells. Students write the lanyard row alone.

## Checks for understanding

- Before D2 is calculated, every student writes a prediction on a mini-whiteboard or paper. Compare predictions with the result and ask two students with different predictions to explain theirs.
- After the first query, ask: "Which number in your result is the sticker revenue for all three weeks, and how do you know the query added the weeks?"
- Exit ticket T0 checks the fixed-versus-variable idea only. It is formative; it never stands in for T1-T3.

## Common misconceptions

- Markup and margin swapped: 1.80 / 4.00 = 0.45 is margin on price; markup on cost is 1.80 / 2.20 = 0.8182. Ask which number the formula divides by and why.
- Typed numbers instead of references: the result looks right until the price changes. Change B3 in front of the student and look at D3 together.
- A query without GROUP BY returns one row per sale. Ask the student to count the rows and compare with the number of items.
- "Most units sold" read as "most profit": stickers sell the most units, and here they also lead profit, but ask students to prove it with margin times units, not unit counts.

## Accessibility and differentiation

- Every task works on paper with the printed data table and a calculator; the spreadsheet and SQL routes are faster, not required, for O3.
- The handout uses short sentences (screened at about grade 7-9); vocabulary cards define markup, margin, revenue and query with an example each.
- Supports change access, not the target: a learner with an accommodation plan gets the supports in that plan (extended time, reader, reduced copying), and still builds the formulas and writes the recommendation.
- No meaning is carried by color in the sheet; cells are labeled in column A.

## Offline and low-bandwidth alternative

Print the handout and the data table. For O2, students total revenue by item with a tally table and a calculator, then write in words the query they would run; you check the logic against the key. Nothing in the unit needs internet access once files are on the lab machines.

## Evidence, feedback and reteaching

- Score T1-T3 with the rubric in `assessment.json`. Use the scoring rationale for each criterion before you score.
- Give feedback on the next action, quoting what the student wrote, for example: "D3 shows 21.6 because it uses C3; now change B3 to 4.50 and tell me what D3 should become before you look."
- Reteach the markup-versus-margin idea to students whose T1 shows the swap, using the two-line contrast in the worked example.
- Record what you actually observe. The rig stops here: it does not invent scores, observations or gains.

## Extension

Add a fourth item with a supplier discount at 50 units, and ask students to model when the discount changes the best price.

## Teacher review points

- Before teaching: confirm the standards mappings against your district's adopted documents; every row in `alignment.json` is a gap or unverified.
- After period 3: review T1 work before the SQL lesson; reteach if more than a few students typed values.
- After the unit: compare T1-T3 results with the objectives and note what to revise; this is the actual learning evidence, which only you can collect.
