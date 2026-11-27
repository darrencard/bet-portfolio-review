# Bet portfolio review: Acme roadmap

> **Illustrative: every figure in this review comes from an invented company's sample data.**

As of 2026-07-27. 8 bets; 7 have a brief that parses. 83% of 18 work items link to a bet; 78% sit under a bet whose brief parses.

Status words (landed, watch, stalled) are did-it-land's, read from each bet's loop record. A metric moving is not proof that the bet moved it.

## Do these first

1. **Supplier price sync (ACME-8):** Lead, Quoting squad writes the landing brief: problem, definition of good, non-goals, cost budget, the line.
2. **Auto match (ACME-5):** Name one owner for this bet.
3. **SMS reminders (ACME-7):** Link the work that delivers this bet, or cut the bet.

## Scorecard

Each bet's definition of good, read from its brief. The result is did-it-land's; this review prints it and never computes one.

| Rank | Bet | Metric | Bar | Better | By | Result |
|---|---|---|---|---|---|---|
| 1 | Supplier price sync (ACME-8) | no landing brief that parses | none | none | none | no result yet |
| 2 | Auto match (ACME-5) | Invoice auto-match rate | 80% | higher | 2026-12-31 | no result yet |
| 3 | SMS reminders (ACME-7) | Reminder open rate | 55% | higher | 2026-12-15 | no result yet |
| 4 | Quote drafting (ACME-1) | Quote draft acceptance rate | 40% | higher | 2026-11-15 | no result yet |
| 5 | Invoice chasing (ACME-2) | Days sales outstanding | 30 | lower | 2026-12-31 | no result yet |
| 6 | Automatic reminders (ACME-3) | Reminders sent per week | 20,000 | higher | 2026-11-30 | no result yet |
| 7 | Payment links (ACME-4) | Payment link conversion | 18% | higher | 2026-11-30 | no result yet |
| 8 | Job scheduler (ACME-6) | Weekly active schedulers | 3,000 | higher | 2026-10-31 | no result yet |

## Ranked review

Rank 1 needs work first. Brief problems are landing_brief.py's own words. Loop shows which Landing Loop steps the bet's record holds.

| Rank | Bet | Owner | Readiness | Gaps | Result | Loop | Next step |
|---|---|---|---|---|---|---|---|
| 1 | Supplier price sync (ACME-8) | Lead, Quoting squad | 4 of 14 (29%) | No landing brief | no result yet | spec no, evals no, cost no, result no | Lead, Quoting squad writes the landing brief: problem, definition of good, non-goals, cost budget, the line. |
| 2 | Auto match (ACME-5) | none | 11 of 14 (79%) | No owner; No result yet | no result yet | spec no, evals no, cost no, result no | Name one owner for this bet. |
| 3 | SMS reminders (ACME-7) | Messaging squad lead | 13 of 14 (93%) | No work linked; No result yet | no result yet | spec no, evals no, cost no, result no | Link the work that delivers this bet, or cut the bet. |
| 4 | Quote drafting (ACME-1) | Lead, Quoting squad | 14 of 14 (100%) | No result yet | no result yet | spec no, evals no, cost no, result no | Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts. |
| 5 | Invoice chasing (ACME-2) | Payments squad lead | 14 of 14 (100%) | No result yet | no result yet | spec no, evals no, cost no, result no | Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts. |
| 6 | Automatic reminders (ACME-3) | Payments squad lead | 14 of 14 (100%) | No result yet | no result yet | spec no, evals no, cost no, result no | Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts. |
| 7 | Payment links (ACME-4) | Payments squad lead | 14 of 14 (100%) | No result yet | no result yet | spec no, evals no, cost no, result no | Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts. |
| 8 | Job scheduler (ACME-6) | Field squad lead | 14 of 14 (100%) | No result yet | no result yet | spec no, evals no, cost no, result no | Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts. |

## Each bet

### 1. Supplier price sync (ACME-8)

- Source: bets.csv row 9.
- Owner: Lead, Quoting squad. Decides the next step: none named.
- Readiness: 4 of 14 points (29%).
- Gaps: No landing brief.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 1 item.
- **Next step:** Lead, Quoting squad writes the landing brief: problem, definition of good, non-goals, cost budget, the line.

### 2. Auto match (ACME-5)

- Source: briefs/auto-match.md.
- Owner: none. Decides the next step: Head of Finance Product, Ledger squad.
- Readiness: 11 of 14 points (79%).
- Gaps: No owner; No result yet.
- Definition of good: Invoice auto-match rate, bar 80%, higher is better, by 2026-12-31.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 1 item.
- **Next step:** Name one owner for this bet.

### 3. SMS reminders (ACME-7)

- Source: briefs/sms-reminders.md.
- Owner: Messaging squad lead. Decides the next step: Head of Product, Messaging squad.
- Readiness: 13 of 14 points (93%).
- Gaps: No work linked; No result yet.
- Definition of good: Reminder open rate, bar 55%, higher is better, by 2026-12-15.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 0 items.
- **Next step:** Link the work that delivers this bet, or cut the bet.

### 4. Quote drafting (ACME-1)

- Source: briefs/quote-drafting.md.
- Owner: Lead, Quoting squad. Decides the next step: Head of Product, Quoting squad.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Quote draft acceptance rate, bar 40%, higher is better, by 2026-11-15.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 4 items.
- **Next step:** Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

### 5. Invoice chasing (ACME-2)

- Source: briefs/invoice-chasing.md.
- Owner: Payments squad lead. Decides the next step: Head of Product, Payments squad.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Days sales outstanding, bar 30, lower is better, by 2026-12-31.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 3 items.
- **Next step:** Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

### 6. Automatic reminders (ACME-3)

- Source: briefs/automatic-reminders.md.
- Owner: Payments squad lead. Decides the next step: Head of Product, Payments squad.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Reminders sent per week, bar 20,000, higher is better, by 2026-11-30.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 2 items.
- **Next step:** Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

### 7. Payment links (ACME-4)

- Source: briefs/payment-links.md.
- Owner: Payments squad lead. Decides the next step: Head of Product, Payments squad.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Payment link conversion, bar 18%, higher is better, by 2026-11-30.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 2 items.
- **Next step:** Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

### 8. Job scheduler (ACME-6)

- Source: briefs/job-scheduler.md.
- Owner: Field squad lead. Decides the next step: Head of Product, Field squad.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Weekly active schedulers, bar 3,000, higher is better, by 2026-10-31.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: spec no, evals no, cost no, result no.
- Linked work: 2 items.
- **Next step:** Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

## Work linked to no bet

Link or cut: 2 items with no bet, 1 item linked to a bet not on the roadmap.

| Item | Title | Why | Source |
|---|---|---|---|
| OPS-901 | Dark mode for the dashboard | no bet | work.csv row 17 |
| OPS-902 | Upgrade the PDF library | no bet | work.csv row 18 |
| OPS-903 | Referral programme banner | links to Growth, which is not on the roadmap | work.csv row 19 |

## Gaps across the portfolio

| Gap | Bets |
|---|---|
| No owner | 1 |
| No landing brief | 1 |
| No work linked | 1 |
| No result yet | 7 |

## Evidence

| Figure | Value | Computed from |
|---|---|---|
| Bets on the roadmap | 8 | bets.csv |
| Bets whose brief parses (landing_brief.py) | 7 | bets.csv |
| Work items | 18 | work.csv |
| Work items linked to no bet | 3 | bets.csv, work.csv |
| Share of work linked to a bet | 83% | bets.csv, work.csv |
| Share of work under a bet whose brief parses | 78% | bets.csv, work.csv |
| Bets landed | 0 | landing/*.json (landed.status, written by did-it-land) |
| Bets watch | 0 | landing/*.json (landed.status, written by did-it-land) |
| Bets stalled | 0 | landing/*.json (landed.status, written by did-it-land) |
| Bets with no result yet | 8 | landing/*.json (landed.status, written by did-it-land) |

Computed by scripts/review.py. The readiness weights are in scripts/score.py; brief problems come from landing_brief.py.
