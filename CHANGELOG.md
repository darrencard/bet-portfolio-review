# Changelog

## 0.3.1 (2026-11-26)

- README: install through the Landing Loop bundle (`/plugin marketplace add darrencard/landing-loop`, then `/plugin install bet-portfolio-review@landing-loop`), with the paste-in prompt kept for a standalone install.
- README: the repository is public, so the private-until-review notes are gone, and the loop is counted as eleven skills plus the Product & Technology Leader Report.
- README: one trademark line for Claude and Claude Code.
- No change to what the skill computes. The version in the sample record's `tool` field moves with the release.
- Sample: every owner is a role scoped to a team ("Lead, Payments squad", not "Payments squad lead").
- The next step names a scoped role as a label: "Owner: Lead, Quoting squad. Write the landing brief." and "Decider: Head of Product, Quoting squad. Change the approach or stop the bet." The sample's `portfolio` key changes with it.
- `--demo` runs a second, smaller fixture, labelled as such: its bets are renamed (Job summary drafting, Overdue reminders, Supplier feed matching) so none shares a name or record with a canonical Acme bet, its owners are scoped roles, and its next step is decided by the Head of Product, Quoting squad.
- Text selection and the focus ring print in ink, not the template's green.
- Python 3.11 or later. The entry scripts check the version first and stop with a plain message on anything older.
- The loop records are built in full first, then each is written to a temporary file and renamed into place, so a crash never leaves a record half written.

## 0.3.0 (2026-11-26)

- Sample: `examples/acme/` reads the canonical Acme landing briefs shared by the Landing Loop skills and renders `bet-portfolio-review.html`, with its Markdown and JSON twins and the `portfolio` key of `landing/quote-drafting.json`. The README's Sample section has the one command; a test checks it reproduces the committed files byte for byte.
- `bets.csv` takes a `brief_file` column: a Markdown brief file inside the CSV's folder.
- `--stem` names the output files (default `review`).
- The HTML adds a scorecard in the Leader Report's style: each bet's definition of good in mono, with the result word from did-it-land. The ranked table leaves the result to the scorecard and no longer wraps at desktop width.
- A bet whose date has passed with no result is told to run did-it-land first, not to extend or stop.
- A bet with no loop record yet reads the same as an empty record, so a rerun prints the same page.
- The sample is dated 2026-07-27, the Decide step, so it comes before spec-auditor's audit (2026-08-03) and claims no later result.
- A bet with a parsed brief, no result and no `spec` key is told to run spec-auditor next (02 Spec), not did-it-land.

## 0.2.1 (2026-11-26)

- One owner per figure, per the Landing Loop contract. Brief completeness is `landing_brief.parse`'s call, listed in its own words (as spec-auditor does); this skill's own list of brief parts, placeholder list and part weights are gone. Readiness is owner 3, brief 10, linked work 1.
- landed, watch and stalled print only from the `landed` key; `--readings` and the computed status rule are gone.
- Cost per task is no longer computed; the review shows the `cost` key or says to run cost-budget-check.

## 0.2.0 (2026-11-26)

- Landing Loop: writes the `portfolio` key of `landing/<bet-slug>.json` per bet, keeps every other key as found, and shows each bet's loop progress (spec, evals, cost, result).
- Live data first: Linear projects and issues (connector pages, or Linear's projects CSV) and Jira search pages, read with the Leader Report's `from_linear.py` and `from_jira.py`, vendored at a pinned commit. Canceled Linear items are left out unless `--include-closed`.
- HTML in the Leader Report's style, from its vendored template. Markdown stays the plain-text twin.
- A landed bet with no linked work is told to record it, not to cut it.

## 0.1.0 (2026-11-26)

- First version: brief score, gaps, orphan work, ranked review, one next step per bet, claim check, `--demo`, `--fail-on`.
