# Changelog

## 0.3.3 (2026-11-27)

- The page's picture is now the scorecard, in the grammar of the outcome scorecard on dacard.ai/update: one frame of HTML rows split by hairlines, one row per project in rank order. Each row prints the name, four pips (plan, owner, work linked, cost budget; filled when in place), the figure `3 of 4 in place`, and the next step as a muted check word, with DO FIRST in ink on rank 1. The pips are named once in the column head and once in the caption. Labels and words render 12px Geist Mono, names 14px Geist; no text in any SVG, no viewBox, no boxed chip. The two-axis grid (wide and tall SVGs) is gone.
- Each pip is drawn on its own, so an empty pip sits where its part is missing (Auto match has no owner, SMS reminders no work). The cost budget is in place when the landing brief states it and the parser lists no problem with either of its two lines; a fixed-code brief that states none counts.
- Steps done in each project's detail print as words (done in ink, not yet muted), not boxed chips.
- svgkit 1.2.0, vendored byte-identical from landing-loop 78784ef (the commit that last changed `tools/svgkit.py`; rollout recipe at c6c47e7) and pinned in `VENDORED.json`.
- Tests copied from the rollout recipe: no text inside an SVG, no scaled picture, only the 12px and 14px sizes in the frame, no box in the frame and no chip before the engineers' fold, no legacy svgkit primitive (rendered with DeprecationWarning as an error), status dots only beside their words, one frame with one row per project and each figure line printed exactly, the aria-label equal to the verdict, and nothing drawn that the page does not print.
- Plain words in the README and SKILL.md: project, target, the project file, and the landing brief defined once as a one-page plan: what good looks like, by when, at what cost. SKILL.md tells Claude to use the user's own word if they say bet. Keys, file names and flags are unchanged.

## 0.3.2 (2026-11-27)

- The HTML page follows the Landing Loop sample anatomy, built like did-it-land's and eval-kit's: the shared header (mark, DACARD, skill, date, version, blue Illustrative tag), the verdict as the heading ("Five of eight projects are ready. Start with Supplier price sync: it has no landing brief."), the signature picture, one next step with its owner in brass and when it is due, then every project in two columns and the work linked to no project. The evidence ledger and an engineers' fold (gap codes, landing_brief.py's own words, source rows, flags, the record key) are folded. No call to action: the page is the skill's own output.
- The signature picture: a two-axis grid, plan complete across and work linked down, one dot per project with its name, a hollow dot for no owner, the project to do first circled and tagged. The corner with both is shaded neutral, never green. A 640 wide variant beside the next step on desktop and a 340 wide one for phones; its aria-label states the answer. Drawn with svgkit, vendored byte-identical from landing-loop 5d01756 and pinned in `VENDORED.json` under `landing-loop`.
- Plain words in the page and the Markdown twin: project, target, landing brief (defined at first use), build plan checked, quality tested, AI usage per task, AI price per unit. The stored `portfolio` key and the JSON keys are unchanged apart from `tool`; the record keeps the next step's original text.
- Gap labels: "Landing brief incomplete" and "Date passed, target not met".
- Design fix round 2: no text below 11px at any width (the page raises the vendored template's and svgkit's 10 and 10.5px labels as it writes its CSS; both files stay byte-identical). The header prints the plain name, Portfolio review; the code name moves to the engineers' fold. Public copy, on the page and in the Markdown twin, prints none of record, bet, the bar, PRD, ARR or tokens: the evidence ledger names its sources in plain words, file names and each project's source move to the engineers' fold (a new "For your engineers" section in the Markdown), AI usage prints as a count, and "Record it as landed" reads "Mark it landed in the project file". Tests for each.
- Tests: the picture draws only names the page prints and no figure of its own, green and red appear only beside the words landed and stalled, the aria-label states the answer, public copy uses the plain words, the page follows the anatomy, and the vendored svgkit matches its pin.

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
