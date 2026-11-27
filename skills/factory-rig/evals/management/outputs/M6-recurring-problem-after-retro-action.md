skills used: kanban-guru, incident-learning

# Advice on the Review bottleneck

**The 2026-09-18 action isn't done; it was marked done.** Board data for October and November shows Review at 6 to 8 items, 2 to 2.7 times the limit of 3, and the oldest item has sat there 19 days. Marking an action done is a tracker step. The test is whether Review stayed at 3 or fewer, and it didn't.

**I'd advise against "communicate more about reviews".** It has no owner, no measure, and no test of success, the same shape as the action that failed.

## What to do instead

1. **Reopen the September action** and record what happened: limit set, not enforced, Review grew to 6 to 8.
2. **Find out why the limit didn't hold.** Common causes: new work keeps starting when Review is full, items are too large, few reviewers, or blocked items parked in Review.
3. **Make the limit bite.** When Review hits 3, nobody pulls new work; people review instead. Write the rule on the board.
4. **Start from the oldest item.** Walk the board right to left at standup and clear the 19-day item first. Track work item age in Review.
5. **Run one experiment with an owner, a measure, and a check date.** For example: "Review stays at 3 or fewer and no item there is older than 5 days, checked at the next retro." Adjust the thresholds after two weeks of data.
6. **Close the action only on board data** showing Review held at the limit, not a status change.

## Assumptions

- Review is team-controlled. If it waits on an outside approver, track those items as blocked dependencies.
- Throughput was roughly stable over the period, so by Little's Law the higher WIP in Review means longer waits there.
