#!/usr/bin/env python3
"""Review a roadmap of bets against each bet's landing brief. Writes review.md, review.html and review.json.

Usage:
  python3 scripts/review.py --csv bets.csv --work work.csv --as-of 2026-11-26 --out run
  python3 scripts/review.py --linear-projects projects.json --linear-issues issues.json --as-of 2026-11-26 --out run
  python3 scripts/review.py --jira export.csv --as-of 2026-11-26 --out run
  Add --readings readings.csv for metric readings (bet, current, prior, source, date), --title "Q1 roadmap",
  and --illustrative when the data is a sample.

Reads files and writes files. Makes no network calls. Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import load
import render
import score

DEMO = Path(__file__).resolve().parents[3] / "evals" / "fixtures" / "acme"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a roadmap of bets against each bet's landing brief.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="run on the illustrative Acme fixture, to see the output in one command")
    src.add_argument("--csv", type=Path, help="bets.csv: id, name, owner, and a description or one column per brief part")
    src.add_argument("--linear-projects", type=Path, help="the projects JSON from the Linear connector")
    src.add_argument("--jira", type=Path, help="a Jira CSV export holding the bets (epics) and the work")
    ap.add_argument("--work", type=Path, help="with --csv: work.csv (id, title, bet)")
    ap.add_argument("--linear-issues", type=Path, help="with --linear-projects: the issues JSON")
    ap.add_argument("--jira-bet-type", default="Epic", help="with --jira: the issue type that holds bets (default Epic)")
    ap.add_argument("--readings", type=Path, help="readings.csv: bet, current, prior, source, date")
    ap.add_argument("--as-of", help="today, YYYY-MM-DD (required, except with --demo)")
    ap.add_argument("--fail-on", default="", help="comma-separated gaps, such as no-owner,no-metric: exit 2 if any bet has one (for CI)")
    ap.add_argument("--title", default="Roadmap", help="the review's title")
    ap.add_argument("--out", type=Path, default=Path("run"), help="the folder to write into (default run/)")
    ap.add_argument("--illustrative", action="store_true", help="stamp every output as illustrative sample data")
    args = ap.parse_args(argv)

    if args.demo:
        if not DEMO.is_dir():
            raise SystemExit("review: --demo needs the repository's evals/fixtures/acme folder. Run it from a clone.")
        args.csv, args.work, args.readings = DEMO / "bets.csv", DEMO / "work.csv", DEMO / "readings.csv"
        args.as_of, args.illustrative = args.as_of or "2026-11-26", True
        args.title = "Acme roadmap (illustrative)" if args.title == "Roadmap" else args.title
    if not args.as_of:
        raise SystemExit("review: --as-of is required. Write today's date as YYYY-MM-DD.")
    fail_on = [g.strip() for g in args.fail_on.split(",") if g.strip()]
    unknown = [g for g in fail_on if g not in score.LABELS]
    if unknown:
        raise SystemExit(f"review: --fail-on has unknown gap(s) {', '.join(unknown)}. Use: {', '.join(score.LABELS)}.")
    try:
        if args.csv:
            bets = load.csv_bets(args.csv)
            work = load.csv_work(args.work) if args.work else []
            sources = {"bets": args.csv.name, "work": args.work.name if args.work else ""}
        elif args.linear_projects:
            bets = load.linear_bets(args.linear_projects)
            work = load.linear_work(args.linear_issues) if args.linear_issues else []
            sources = {"bets": args.linear_projects.name, "work": args.linear_issues.name if args.linear_issues else ""}
        else:
            bets, work = load.jira(args.jira, args.jira_bet_type)
            sources = {"bets": args.jira.name, "work": args.jira.name}
        unmatched: list[str] = []
        if args.readings:
            unmatched = load.attach_readings(args.readings, bets)
            sources["readings"] = args.readings.name
        pf = score.review(bets, work, args.as_of)
    except (load.LoadError, ValueError) as e:
        raise SystemExit(f"review: {e}") from None

    markdown = render.to_markdown(pf, args.title, sources, args.illustrative)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "review.md").write_text(markdown, encoding="utf-8")
    (args.out / "review.html").write_text(render.to_html(pf, args.title, sources, args.illustrative), encoding="utf-8")
    (args.out / "review.json").write_text(render.to_json(pf, markdown, sources, args.illustrative), encoding="utf-8")

    print(f"review: {len(pf.reviews)} bets, {pf.complete} with a complete brief, {len(pf.orphans)} of {pf.work_total} work items linked to no bet.")
    for r in pf.reviews[:3]:
        print(f"  {r.rank}. {r.bet.id} {r.points}/{score.TOTAL}: {r.next_step}")
    for u in unmatched:
        print(f"review: reading at {u} matches no bet on the roadmap; it was left out.", file=sys.stderr)
    print(f"review: wrote {args.out / 'review.md'}, review.html and review.json.", file=sys.stderr)
    failing = [f"{r.bet.id} ({g})" for r in pf.reviews for g in r.gaps if g in fail_on]
    if failing:
        print(f"review: --fail-on matched {len(failing)}: {', '.join(failing)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
