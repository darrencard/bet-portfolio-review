# Find the bets that cannot land

A free Claude skill that scores every bet on your roadmap against its landing brief and ranks what to fix first.

**Why it matters:** a bet with no metric, owner or cost budget cannot be called landed or stalled, and work tied to no bet is spend no one is accountable for. This review finds both, live from your Linear or Jira roadmap (a CSV when there is no connector), with one next step per bet.

**How it works:** Python computes every score, count and cost per task, with a source for each. The model never does the arithmetic, and a rewrite that adds a number, changes a status word or claims cause fails the check.

## Install: paste this into Claude Code

```text
Install the bet-portfolio-review skill from https://github.com/darrencard/bet-portfolio-review: clone it, run python3 -m unittest discover -s evals and stop if any test fails, then copy skills/bet-portfolio-review into ~/.claude/skills/. Then review my roadmap: read the Linear projects and issues already connected to this session (or my Jira search results through the Jira connector, or ask me for a CSV), ask me only for metric readings I have with their sources, run the review as of today, and show me the ranked table, the work linked to no bet and the top three next steps.
```

The repository is private until review, so the clone needs `gh` signed in with access.

**See it first, in one command:** from a clone, `python3 skills/bet-portfolio-review/scripts/review.py --demo --out run` reviews the illustrative Acme roadmap. The same output is checked in at [examples/acme/review.md](examples/acme/review.md).

```text
Do these first
1. Payments onboarding revamp (ACME-B5): Payments squad lead writes the landing brief.
2. Trade directory listing (ACME-B6): Name one owner for this bet.
3. Supplier price sync (ACME-B4): State the cost budget as two lines, tokens per task and price per token.
```

## Step 1 of the Landing Loop

Five skills and the [Product & Technology Leader Report](https://github.com/darrencard/product-engineering-update) work on one landing brief per bet, and share one record per bet, `landing/<bet-slug>.json`. This skill is step 1, Decide: it writes only the record's `portfolio` key, and its review shows how far each bet has got through the other steps (spec, evals, cost, result).

## What it checks

| Check | Points | Flag when it fails |
|---|---|---|
| Owner | 3 | no-owner |
| Definition of good: metric, bar, higher or lower, date | 3 | no-metric |
| Cost budget: tokens per task and price per token | 2 | no-cost-budget |
| Non-goals | 2 | no-non-goals |
| Problem, the line, who decides | 1 each | no-problem, no-line, no-decider |
| Work linked to the bet | 1 | no-work |

Also flagged: a bet with no brief at all, work linked to no bet or to a bet not on the roadmap, a metric never read, a reading with no source, and a date passed without landing. A placeholder such as TBD or n/a counts as missing.

## What it does not do

- **It does not judge whether a bet is the right one.** The score says whether a bet can be judged when the reading comes in, not whether it is worth doing. Value, usability, feasibility and viability stay with the team.
- **It does not do discovery.** It reads the problem as written; it does not check it against customer evidence.
- **It does not prove cause.** A metric moving is not proof the bet moved it, and the review never says so.

Because a full score is easy to game with filler, the review also shows what the score cannot: whether each metric has ever been read, and how much of the work sits under a bet with a definition of good.

## Gate a roadmap in CI

`--fail-on no-owner,no-metric` exits 2 when any bet has one of those gaps, so a planning repo or a scheduled job can refuse a roadmap with unowned or unmeasured bets.

## What you get

- **A ranked review** in Markdown and one self-contained HTML page in the Leader Report's style. Rank 1 needs work first.
- **A loop record per bet**, with every figure carrying its value, unit, source, window and date.
- **One next step per bet**, chosen in code from its most important gap.
- **Status words only when earned.** landed, watch or stalled prints only where a reading with a named source meets a complete definition of good. Stalled prints in red.
- **An evidence table.** Every portfolio figure names the file it was computed from; every bet names its row or project.
- **A claim check.** `validate.py` refuses an edited review that adds a figure, changes a status word, claims a bet caused a change, or drops a bet.

## Run it on your own roadmap

```bash
python3 skills/bet-portfolio-review/scripts/review.py --csv bets.csv --work work.csv --readings readings.csv --as-of 2026-11-26 --out run
```

Templates for the three CSVs are in `skills/bet-portfolio-review/assets/`. Linear and Jira inputs are in [SKILL.md](skills/bet-portfolio-review/SKILL.md). The demo fixture is Acme, an invented invoicing company for trades businesses; every figure in it is illustrative.

## Built on

- The Leader Report's landing brief parser, Linear and Jira readers, and style, copied unchanged at one pinned commit (`skills/bet-portfolio-review/VENDORED.json`; a test checks every hash).
- Orphan and data-gap checks ported to Python from Throughline, Dacard's R&D prototype.

Python 3.9 or later, standard library only. MIT licensed. Version 0.2.0.
