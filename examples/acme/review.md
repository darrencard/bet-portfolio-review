# Bet portfolio review: Acme roadmap (illustrative)

> **Illustrative: every figure in this review comes from an invented company's sample data.**

As of 2026-11-26. 8 bets; 5 have a complete brief. 84% of 19 work items link to a bet; 68% sit under a bet with a definition of good.

Status words print only where a reading with a named source exists: landed, watch or stalled. A metric moving is not proof that the bet moved it.

## Do these first

1. **Payments onboarding revamp (ACME-B5):** Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line.
2. **Trade directory listing (ACME-B6):** Name one owner for this bet.
3. **Supplier price sync (ACME-B4):** State the cost budget as two lines, tokens per task and price per token, or mark the line fixed code.

## Ranked review

Rank 1 needs work first.

| Rank | Bet | Owner | Brief score | Gaps | Status | Next step |
|---|---|---|---|---|---|---|
| 1 | Payments onboarding revamp (ACME-B5) | Payments squad lead | 4 of 14 (29%) | No landing brief | no reading | Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line. |
| 2 | Trade directory listing (ACME-B6) | none | 8 of 14 (57%) | No owner; No definition of good | no reading | Name one owner for this bet. |
| 3 | Supplier price sync (ACME-B4) | Catalogue squad lead | 10 of 14 (71%) | No cost budget; No non-goals; Metric never read | no reading | State the cost budget as two lines, tokens per task and price per token, or mark the line fixed code. |
| 4 | Crew scheduling (ACME-B7) | Field squad lead | 13 of 14 (93%) | No work linked; Date passed without landing; Metric never read | no reading | Link the work that delivers this bet, or cut the bet. |
| 5 | Invoice chasing (ACME-B2) | Payments squad lead | 14 of 14 (100%) | None | stalled | Head of Product decides: change the approach or stop the bet. |
| 6 | Owner reporting dashboards (ACME-B8) | Insights squad lead | 14 of 14 (100%) | Reading has no source | no status word: the reading has no source | Name the source of the Weekly active owners viewing reports reading. Until then it earns no status word. |
| 7 | Mobile job sheets (ACME-B3) | Field squad lead | 14 of 14 (100%) | Reading has no prior value | watch | Take the next reading of Job sheets completed on mobile before 2027-01-31. |
| 8 | Quote drafting assistant (ACME-B1) | Quotes squad lead | 14 of 14 (100%) | None | landed | Record it as landed. Head of Product decides what comes next. |

## Each bet

### 1. Payments onboarding revamp (ACME-B5)

- Source: bets.csv row 6.
- Owner: Payments squad lead. Decides the next step: none named.
- Brief score: 4 of 14 points (29%).
- Gaps: No landing brief.
- Cost budget: missing.
- Reading: none recorded.
- Status: no reading.
- Linked work: 2 items.
- **Next step:** Payments squad lead writes the landing brief: problem, definition of good, non-goals, cost budget, the line.

### 2. Trade directory listing (ACME-B6)

- Source: bets.csv row 7.
- Owner: none. Decides the next step: Head of Growth.
- Brief score: 8 of 14 points (57%).
- Gaps: No owner; No definition of good.
  - No definition of good: Missing a bar that is one number.
- Tokens per task: none.
- Price per token: none (the line is fixed code).
- Reading: none recorded.
- Status: no reading.
- Linked work: 1 item.
- **Next step:** Name one owner for this bet.

### 3. Supplier price sync (ACME-B4)

- Source: bets.csv row 5.
- Owner: Catalogue squad lead. Decides the next step: Head of Product.
- Brief score: 10 of 14 points (71%).
- Gaps: No cost budget; No non-goals; Metric never read.
  - No cost budget: Missing or unreadable: tokens per task and price per token.
- Definition of good: Price book entries older than 30 days, bar 10%, lower is better, by 2027-02-28.
- Cost budget: missing.
- Reading: none recorded.
- Status: no reading.
- Linked work: 2 items.
- **Next step:** State the cost budget as two lines, tokens per task and price per token, or mark the line fixed code.

### 4. Crew scheduling (ACME-B7)

- Source: bets.csv row 8.
- Owner: Field squad lead. Decides the next step: VP Engineering.
- Brief score: 13 of 14 points (93%).
- Gaps: No work linked; Date passed without landing; Metric never read.
- Definition of good: Double bookings per week, bar 2, lower is better, by 2026-10-31.
- Tokens per task: none.
- Price per token: none (the line is fixed code).
- Reading: none recorded.
- Status: no reading.
- Linked work: 0 items.
- **Next step:** Link the work that delivers this bet, or cut the bet.

### 5. Invoice chasing (ACME-B2)

- Source: bets.csv row 3.
- Owner: Payments squad lead. Decides the next step: Head of Product.
- Brief score: 14 of 14 points (100%).
- Gaps: None.
- Definition of good: Median days to paid, bar 14, lower is better, by 2026-12-15.
- Tokens per task: 6000.
- Price per token: $0.000003.
- Cost per task, computed: $0.018.
- Reading: Median days to paid is 18 on 2026-11-24; prior 17 (source: Billing export: paid_at minus sent_at; readings.csv row 3).
- Status: stalled.
- Linked work: 3 items.
- **Next step:** Head of Product decides: change the approach or stop the bet.

### 6. Owner reporting dashboards (ACME-B8)

- Source: bets.csv row 9.
- Owner: Insights squad lead. Decides the next step: Head of Product.
- Brief score: 14 of 14 points (100%).
- Gaps: Reading has no source.
- Definition of good: Weekly active owners viewing reports, bar 35%, higher is better, by 2027-01-15.
- Tokens per task: 4000.
- Price per token: $0.000003.
- Cost per task, computed: $0.012.
- Reading: Weekly active owners viewing reports is 31% on 2026-11-24; prior 28% (no source named; readings.csv row 5).
- Status: no status word: the reading has no source.
- Linked work: 2 items.
- **Next step:** Name the source of the Weekly active owners viewing reports reading. Until then it earns no status word.

### 7. Mobile job sheets (ACME-B3)

- Source: bets.csv row 4.
- Owner: Field squad lead. Decides the next step: VP Engineering.
- Brief score: 14 of 14 points (100%).
- Gaps: Reading has no prior value.
- Definition of good: Job sheets completed on mobile, bar 60%, higher is better, by 2027-01-31.
- Tokens per task: none.
- Price per token: none (the line is fixed code).
- Reading: Job sheets completed on mobile is 22% on 2026-11-24; no prior reading (source: Product analytics: job_sheet_completed event; readings.csv row 4).
- Status: watch.
- Linked work: 3 items.
- **Next step:** Take the next reading of Job sheets completed on mobile before 2027-01-31.

### 8. Quote drafting assistant (ACME-B1)

- Source: bets.csv row 2.
- Owner: Quotes squad lead. Decides the next step: Head of Product.
- Brief score: 14 of 14 points (100%).
- Gaps: None.
- Definition of good: Quotes sent within 24 hours, bar 40%, higher is better, by 2026-12-31.
- Tokens per task: 9000.
- Price per token: $0.000003.
- Cost per task, computed: $0.027.
- Reading: Quotes sent within 24 hours is 43% on 2026-11-24; prior 36% (source: Product analytics: quotes_sent event; readings.csv row 2).
- Status: landed.
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
| No definition of good | 1 |
| No cost budget | 1 |
| No non-goals | 1 |
| No work linked | 1 |
| Reading has no source | 1 |
| Reading has no prior value | 1 |
| Date passed without landing | 1 |
| Metric never read | 2 |

## Evidence

| Figure | Value | Computed from |
|---|---|---|
| Bets on the roadmap | 8 | bets.csv |
| Bets with a complete brief | 5 | bets.csv, work.csv |
| Work items | 19 | work.csv |
| Work items linked to no bet | 3 | bets.csv, work.csv |
| Share of work linked to a bet | 84% | bets.csv, work.csv |
| Share of work under a bet with a definition of good | 68% | bets.csv, work.csv |
| Bets landed | 1 | bets.csv, readings.csv |
| Bets watch | 1 | bets.csv, readings.csv |
| Bets stalled | 1 | bets.csv, readings.csv |
| Bets with no status word | 5 | bets.csv, readings.csv |

Computed by scripts/review.py. The brief score weights are in scripts/score.py.
