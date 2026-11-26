# Bet portfolio review: Acme roadmap (illustrative)

> **Illustrative: every figure in this review comes from an invented company's sample data.**

As of 2026-11-26. 8 bets; 5 have a brief that parses. 84% of 19 work items link to a bet; 58% sit under a bet whose brief parses.

Status words (landed, watch, stalled) are did-it-land's, read from each bet's loop record. A metric moving is not proof that the bet moved it.

## Do these first

1. **Trade directory listing (ACME-B6):** Name one owner for this bet.
2. **Supplier price sync (ACME-B4):** Fix the brief: non goals is missing or empty.
3. **Payments onboarding revamp (ACME-B5):** Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line.

## Ranked review

Rank 1 needs work first. Brief problems are landing_brief.py's own words. Loop shows which Landing Loop steps the bet's record holds.

| Rank | Bet | Owner | Readiness | Gaps | Result | Loop | Next step |
|---|---|---|---|---|---|---|---|
| 1 | Trade directory listing (ACME-B6) | none | 1 of 14 (7%) | No owner; Brief does not parse | no result yet | no loop record | Name one owner for this bet. |
| 2 | Supplier price sync (ACME-B4) | Catalogue squad lead | 4 of 14 (29%) | Brief does not parse | no result yet | no loop record | Fix the brief: non goals is missing or empty. |
| 3 | Payments onboarding revamp (ACME-B5) | Payments squad lead | 4 of 14 (29%) | No landing brief | no result yet | no loop record | Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line. |
| 4 | Crew scheduling (ACME-B7) | Field squad lead | 13 of 14 (93%) | No work linked; Date passed, no result met the bar; No result yet | no result yet | no loop record | Link the work that delivers this bet, or cut the bet. |
| 5 | Invoice chasing (ACME-B2) | Payments squad lead | 14 of 14 (100%) | None | stalled | spec yes, evals yes, cost no, result stalled | Head of Product decides: change the approach or stop the bet. |
| 6 | Owner reporting dashboards (ACME-B8) | Insights squad lead | 14 of 14 (100%) | No result yet | no result yet | no loop record | Run did-it-land on Weekly active owners viewing reports once it has a reading from its source. |
| 7 | Mobile job sheets (ACME-B3) | Field squad lead | 14 of 14 (100%) | None | watch | spec yes, evals no, cost no, result watch | Take the next reading of Job sheets completed on mobile before 2027-01-31. |
| 8 | Quote drafting assistant (ACME-B1) | Quotes squad lead | 14 of 14 (100%) | None | landed | spec yes, evals yes, cost yes, result landed | Record it as landed. Head of Product decides what comes next. |

## Each bet

### 1. Trade directory listing (ACME-B6)

- Source: bets.csv row 7.
- Owner: none. Decides the next step: none named.
- Readiness: 1 of 14 points (7%).
- Gaps: No owner; Brief does not parse.
  - landing_brief.py: bar is missing or empty.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: no loop record.
- Linked work: 1 item.
- **Next step:** Name one owner for this bet.

### 2. Supplier price sync (ACME-B4)

- Source: bets.csv row 5.
- Owner: Catalogue squad lead. Decides the next step: none named.
- Readiness: 4 of 14 points (29%).
- Gaps: Brief does not parse.
  - landing_brief.py: non goals is missing or empty.
  - landing_brief.py: tokens per task is missing or empty.
  - landing_brief.py: price per token is missing or empty.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: no loop record.
- Linked work: 2 items.
- **Next step:** Fix the brief: non goals is missing or empty.

### 3. Payments onboarding revamp (ACME-B5)

- Source: bets.csv row 6.
- Owner: Payments squad lead. Decides the next step: none named.
- Readiness: 4 of 14 points (29%).
- Gaps: No landing brief.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: no loop record.
- Linked work: 2 items.
- **Next step:** Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line.

### 4. Crew scheduling (ACME-B7)

- Source: bets.csv row 8.
- Owner: Field squad lead. Decides the next step: VP Engineering.
- Readiness: 13 of 14 points (93%).
- Gaps: No work linked; Date passed, no result met the bar; No result yet.
- Definition of good: Double bookings per week, bar 2, lower is better, by 2026-10-31.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: no loop record.
- Linked work: 0 items.
- **Next step:** Link the work that delivers this bet, or cut the bet.

### 5. Invoice chasing (ACME-B2)

- Source: bets.csv row 3.
- Owner: Payments squad lead. Decides the next step: Head of Product.
- Readiness: 14 of 14 points (100%).
- Gaps: None.
- Definition of good: Median days to paid, bar 14, lower is better, by 2026-12-15.
- Cost: not checked. Run cost-budget-check.
- Result: stalled.
- Loop: spec yes, evals yes, cost no, result stalled.
- Linked work: 3 items.
- **Next step:** Head of Product decides: change the approach or stop the bet.

### 6. Owner reporting dashboards (ACME-B8)

- Source: bets.csv row 9.
- Owner: Insights squad lead. Decides the next step: Head of Product.
- Readiness: 14 of 14 points (100%).
- Gaps: No result yet.
- Definition of good: Weekly active owners viewing reports, bar 35%, higher is better, by 2027-01-15.
- Cost: not checked. Run cost-budget-check.
- Result: no result yet.
- Loop: no loop record.
- Linked work: 2 items.
- **Next step:** Run did-it-land on Weekly active owners viewing reports once it has a reading from its source.

### 7. Mobile job sheets (ACME-B3)

- Source: bets.csv row 4.
- Owner: Field squad lead. Decides the next step: VP Engineering.
- Readiness: 14 of 14 points (100%).
- Gaps: None.
- Definition of good: Job sheets completed on mobile, bar 60%, higher is better, by 2027-01-31.
- Cost: not checked. Run cost-budget-check.
- Result: watch.
- Loop: spec yes, evals no, cost no, result watch.
- Linked work: 3 items.
- **Next step:** Take the next reading of Job sheets completed on mobile before 2027-01-31.

### 8. Quote drafting assistant (ACME-B1)

- Source: bets.csv row 2.
- Owner: Quotes squad lead. Decides the next step: Head of Product.
- Readiness: 14 of 14 points (100%).
- Gaps: None.
- Definition of good: Quotes sent within 24 hours, bar 40%, higher is better, by 2026-12-31.
- Cost, from cost-budget-check: tokens per task 8,400 tokens; price per token 0.000003 USD (source: usage export).
- Result: landed.
- Loop: spec yes, evals yes, cost yes, result landed.
- Linked work: 3 items.
- **Next step:** Record it as landed. Head of Product decides what comes next.

## Work linked to no bet

Link or cut: 2 items with no bet, 1 item linked to a bet not on the roadmap.

| Item | Title | Why | Source |
|---|---|---|---|
| ACME-180 | Dark mode for the web app | no bet | work.csv row 18 |
| ACME-181 | Refactor PDF export | no bet | work.csv row 19 |
| ACME-182 | Referral programme page | links to ACME-B9, which is not on the roadmap | work.csv row 20 |

## Gaps across the portfolio

| Gap | Bets |
|---|---|
| No owner | 1 |
| No landing brief | 1 |
| Brief does not parse | 2 |
| No work linked | 1 |
| Date passed, no result met the bar | 1 |
| No result yet | 2 |

## Evidence

| Figure | Value | Computed from |
|---|---|---|
| Bets on the roadmap | 8 | bets.csv |
| Bets whose brief parses (landing_brief.py) | 5 | bets.csv |
| Work items | 19 | work.csv |
| Work items linked to no bet | 3 | bets.csv, work.csv |
| Share of work linked to a bet | 84% | bets.csv, work.csv |
| Share of work under a bet whose brief parses | 58% | bets.csv, work.csv |
| Bets landed | 1 | landing/*.json (landed.status, written by did-it-land) |
| Bets watch | 1 | landing/*.json (landed.status, written by did-it-land) |
| Bets stalled | 1 | landing/*.json (landed.status, written by did-it-land) |
| Bets with no result yet | 5 | landing/*.json (landed.status, written by did-it-land) |

Computed by scripts/review.py. The readiness weights are in scripts/score.py; brief problems come from landing_brief.py.
