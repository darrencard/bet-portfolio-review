# Find the bets that cannot land

A free Claude skill that scores every bet on your roadmap against its landing brief and ranks what to fix first.

**Why it matters:** a bet with no metric, owner or cost budget cannot be called landed or stalled, and work tied to no bet is spend no one is accountable for. This review finds both, live from your Linear or Jira roadmap (a CSV when there is no connector), with one next step per bet.

**How it works:** Python computes every score and count, with a source for each. Brief completeness is the landing brief parser's own check, word for word, and landed, watch or stalled comes only from did-it-land. The model never does the arithmetic, and a rewrite that adds a number, changes a status word or claims cause fails the check.

## Install

In Claude Code:

```text
/plugin marketplace add darrencard/landing-loop
/plugin install bet-portfolio-review@landing-loop
```

Standalone, paste this into Claude Code:

```text
Install the bet-portfolio-review skill from https://github.com/darrencard/bet-portfolio-review: clone it, find a Python 3.11 or later on this machine (macOS python3 is often 3.9), run python -m unittest discover -s evals with it and stop if any test fails, then copy skills/bet-portfolio-review into ~/.claude/skills/. Then review my roadmap: read the Linear projects and issues already connected to this session (or my Jira search results through the Jira connector, or ask me for a CSV), run the review as of today, and show me the ranked table, the work linked to no bet and the top three next steps.
```

**See it first:** the sample page is [examples/acme/bet-portfolio-review.html](examples/acme/bet-portfolio-review.html), reviewing the illustrative Acme roadmap. `--demo` runs a second, smaller fixture (`evals/fixtures/acme/`, its own made-up bets, not the sample's roadmap) in one command: `python3.12 skills/bet-portfolio-review/scripts/review.py --demo --out run`.

```text
Five of eight projects are ready. Start with Supplier price sync: it has no landing brief.
What to do next: write the landing brief. Owner: Lead, Quoting squad. When: before build starts.
```

## Sample

`examples/acme/` holds the canonical Acme landing briefs shared by every Landing Loop skill (copied unchanged into `briefs/`), a roadmap (`bets.csv`) and its work (`work.csv`). The bet followed end to end is `quote-drafting`. The review is dated 2026-07-27: it is the Decide step, so it runs before the spec audit (2026-08-03) and holds no spec, evals, cost or result yet. This one command, run from the repository root, regenerates the sample page, its Markdown and JSON twins, and the `portfolio` key of `examples/acme/landing/quote-drafting.json` (and the other bets' records):

```bash
python3 skills/bet-portfolio-review/scripts/review.py --csv examples/acme/bets.csv --work examples/acme/work.csv --as-of 2026-07-27 --title "Acme roadmap" --illustrative --out examples/acme --stem bet-portfolio-review --landing examples/acme/landing
```

A test runs that exact line on a fresh copy and checks the output matches the committed files byte for byte. Running it twice changes nothing.

## Step 01 of the Landing Loop: Decide

Eleven skills, the [Product & Technology Leader Report](https://github.com/darrencard/product-engineering-update) among them, work on one landing brief per bet and share one record per bet, `landing/<bet-slug>.json`. This skill is step 01, Decide: it writes only the record's `portfolio` key, and its review shows how far each bet has got through the other steps (spec, evals, cost, result).

## What it checks

| Check | Points | Flag when it fails |
|---|---|---|
| Owner | 3 | no-owner |
| Brief: `landing_brief.parse` accepts it | 10 | no-brief, or brief-problems with the parser's own words |
| Work linked to the bet | 1 | no-work |

Also flagged: work linked to no bet or to a bet not on the roadmap, a date passed with no landed result, and a bet with no result yet. One owner per figure: the brief check is the vendored parser's, status words are did-it-land's, and cost is cost-budget-check's. This skill prints those, never computes them.

## What it does not do

- **It does not judge whether a bet is the right one.** The score says whether a bet can be judged when the reading comes in, not whether it is worth doing. Value, usability, feasibility and viability stay with the team.
- **It does not do discovery.** It reads the problem as written; it does not check it against customer evidence.
- **It does not prove cause.** A metric moving is not proof the bet moved it, and the review never says so.

Because a full score is easy to game with filler, the review also shows what the score cannot: whether did-it-land has a result for each bet, and how much of the work sits under a bet whose brief parses.

## Gate a roadmap in CI

`--fail-on no-owner,no-metric` exits 2 when any bet has one of those gaps, so a planning repo or a scheduled job can refuse a roadmap with unowned or unmeasured bets.

## What you get

- **A ranked review** in Markdown and one self-contained HTML page in the Leader Report's style. Rank 1 needs work first.
- **A loop record per bet**, with every figure carrying its value, unit, source, window and date.
- **One next step per bet**, chosen in code from its most important gap.
- **Status words only from did-it-land.** landed, watch or stalled prints only from the bet's loop record. Stalled prints in red.
- **An evidence table.** Every portfolio figure names the file it was computed from; every bet names its row or project.
- **A claim check.** `validate.py` refuses an edited review that adds a figure, changes a status word, claims a bet caused a change, or drops a bet.

## Run it on your own roadmap

```bash
python3 skills/bet-portfolio-review/scripts/review.py --csv bets.csv --work work.csv --as-of 2026-11-26 --out run
```

Templates for the two CSVs are in `skills/bet-portfolio-review/assets/`. Linear and Jira inputs are in [SKILL.md](skills/bet-portfolio-review/SKILL.md). The demo fixture is Acme, an invented invoicing company for trades businesses; every figure in it is illustrative.

## Built on

- The Leader Report's landing brief parser, Linear and Jira readers, and style, copied unchanged at one pinned commit (`skills/bet-portfolio-review/VENDORED.json`; a test checks every hash).
- Orphan and data-gap checks ported to Python from Throughline, Dacard's R&D prototype.

Python 3.11 or later; the scripts check first and stop with a plain message on anything older (try python3.12). Standard library only. MIT licensed. Version 0.3.2.

Claude and Claude Code are trademarks of Anthropic, PBC. These skills are independent and not affiliated with or endorsed by Anthropic.
