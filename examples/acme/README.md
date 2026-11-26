# Acme sample

Acme is an invented company (invoicing software for trades businesses). Every figure is illustrative.

- `briefs/` are the canonical Acme landing briefs from the Landing Loop repo (`examples/acme/briefs/`), copied unchanged.
- `bets.csv` is the roadmap: one row per bet, its owner, and the brief file. Supplier price sync has no brief on purpose.
- `work.csv` is the work, each item linked to a bet by id. Three items link to no bet on the roadmap.
- `bet-portfolio-review.html` is the sample page, with `.md` (its plain-text twin) and `.json` (the claim check's input).
- `landing/quote-drafting.json` and the other records hold only this skill's `portfolio` key. The review is dated 2026-07-27, the Decide step, before spec-auditor's audit (2026-08-03), so no later step's figures are in it yet.

Regenerate with the command in the repository README's Sample section.
