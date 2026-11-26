# Find the bets that cannot land

A free Claude skill that scores every bet on your roadmap against its landing brief and ranks what to fix first.

**Why it matters:** a bet with no metric, owner or cost budget cannot be called landed or stalled, and work tied to no bet is spend no one is accountable for. This review finds both, from your Linear, Jira or CSV roadmap, with one next step per bet.

**How it works:** Python computes every score, count and cost per task, with a source for each. The model never does the arithmetic, and a rewrite that adds a number, changes a status word or claims cause fails the check.

## Install: paste this into Claude Code

```text
Install the bet-portfolio-review skill from https://github.com/darrencard/bet-portfolio-review: clone it, run python3 -m unittest discover -s evals and stop if any test fails, then copy skills/bet-portfolio-review into ~/.claude/skills/. Then review my roadmap: read the Linear projects and issues already connected to this session (or ask me for a CSV or Jira export), ask me only for metric readings I have with their sources, run the review as of today, and show me the ranked table, the work linked to no bet and the top three next steps.
```

The repository is private until review, so the clone needs `gh` signed in with access.

## What it checks

| Check | Points | Flag when it fails |
|---|---|---|
| Owner | 3 | no-owner |
| Definition of good: metric, bar, higher or lower, date | 3 | no-metric |
| Cost budget: tokens per task and price per token | 2 | no-cost-budget |
| Non-goals | 2 | no-non-goals |
| Problem, the line, who decides | 1 each | no-problem, no-line, no-decider |
| Work linked to the bet | 1 | no-work |

Also flagged: a bet with no brief at all, work linked to no bet or to a bet not on the roadmap, a reading with no source, and a date passed without landing.

## What you get

- **A ranked review** in Markdown and one self-contained HTML file. Rank 1 needs work first.
- **One next step per bet**, chosen in code from its most important gap.
- **Status words only when earned.** landed, watch or stalled prints only where a reading with a named source meets a complete definition of good. Stalled prints in red.
- **An evidence table.** Every portfolio figure names the file it was computed from; every bet names its row or project.
- **A claim check.** `validate.py` refuses an edited review that adds a figure, changes a status word, claims a bet caused a change, or drops a bet.

## Run it yourself

```bash
cd skills/bet-portfolio-review
python3 scripts/review.py --csv ../../evals/fixtures/acme/bets.csv --work ../../evals/fixtures/acme/work.csv --readings ../../evals/fixtures/acme/readings.csv --as-of 2026-11-26 --illustrative --out run
```

The fixture is Acme, an invented invoicing company for trades businesses. Every figure in it is illustrative.

## Built on

- The landing brief schema and status rule from the [Product & Technology Leader Report](https://github.com/darrencard/product-engineering-update) (`landing_brief.py`, copied unchanged from v0.11.0; a test pins its hash).
- Orphan and data-gap checks ported to Python from Throughline, Dacard's R&D prototype.

Python 3.9 or later, standard library only. MIT licensed. Version 0.1.0.
