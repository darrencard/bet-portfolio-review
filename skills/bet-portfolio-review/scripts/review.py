#!/usr/bin/env python3
"""Review a roadmap of bets against each bet's landing brief. Writes review.md, review.html and review.json.

Usage, live data first:
  python3 scripts/review.py --linear-projects projects.json --linear-issues issues-1.json issues-2.json --as-of 2026-11-26
  python3 scripts/review.py --jira-search search-1.json search-2.json --as-of 2026-11-26
and the file fallbacks:
  python3 scripts/review.py --linear-projects projects.csv --as-of 2026-11-26       (Linear's projects CSV export)
  python3 scripts/review.py --jira export.csv --as-of 2026-11-26                    (Jira's CSV export)
  python3 scripts/review.py --csv bets.csv --work work.csv --as-of 2026-11-26
  python3 scripts/review.py --demo                                                  (the illustrative Acme roadmap)
Add --title "Q1 roadmap". Landed, watch or stalled is read from each bet's loop record (did-it-land writes it).

Writes review.md, review.html and review.json to --out (default run/), and the `portfolio` key of each bet's
Landing Loop record to --landing (default landing/), keeping every other key as found. --no-landing skips the records.

Reads files and writes files. Makes no network calls. Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import load
import loop
import render
import score

DEMO = Path(__file__).resolve().parents[3] / "evals" / "fixtures" / "acme"


def names(paths: list[Path]) -> str:
    return ", ".join(p.name for p in paths)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a roadmap of bets against each bet's landing brief.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="run on the illustrative Acme fixture, to see the output in one command")
    src.add_argument("--csv", type=Path, help="bets.csv: id, name, owner, and a description or one column per brief part")
    src.add_argument("--linear-projects", type=Path, nargs="+", help="Linear projects: the connector's list_projects JSON pages, or Linear's projects CSV")
    src.add_argument("--jira-search", type=Path, nargs="+", help="Jira REST search pages (the connector or /rest/api/3/search), saved as they stand")
    src.add_argument("--jira", type=Path, help="a Jira CSV export holding the bets (epics) and the work")
    ap.add_argument("--work", type=Path, help="with --csv: work.csv (id, title, bet)")
    ap.add_argument("--linear-issues", type=Path, nargs="+", help="with --linear-projects: the connector's list_issues JSON pages")
    ap.add_argument("--include-closed", action="store_true", help="with Linear: keep canceled projects and issues (left out by default)")
    ap.add_argument("--jira-bet-type", default="Epic", help="with --jira: the issue type that holds bets (default Epic)")
    ap.add_argument("--as-of", help="today, YYYY-MM-DD (required, except with --demo)")
    ap.add_argument("--fail-on", default="", help="comma-separated gaps, such as no-owner,no-metric: exit 2 if any bet has one (for CI)")
    ap.add_argument("--title", default="Roadmap", help="the review's title")
    ap.add_argument("--out", type=Path, default=Path("run"), help="the folder to write into (default run/)")
    ap.add_argument("--stem", default="review", help="the output file name before .md, .html and .json (default review)")
    ap.add_argument("--illustrative", action="store_true", help="stamp every output as illustrative sample data")
    ap.add_argument("--landing", type=Path, help="the Landing Loop record folder (default landing/, or <out>/landing with --demo)")
    ap.add_argument("--no-landing", action="store_true", help="do not read or write Landing Loop records")
    args = ap.parse_args(argv)

    if args.demo:
        if not DEMO.is_dir():
            raise SystemExit("review: --demo needs the repository's evals/fixtures/acme folder. Run it from a clone.")
        args.csv, args.work = DEMO / "bets.csv", DEMO / "work.csv"
        args.as_of, args.illustrative = args.as_of or "2026-11-26", True
        args.title = "Acme roadmap (illustrative)" if args.title == "Roadmap" else args.title
        if args.landing is None and not args.no_landing:
            # Seed the demo's records with the fixture's other loop steps, so loop progress shows.
            args.landing = args.out / "landing"
            args.landing.mkdir(parents=True, exist_ok=True)
            for old in args.landing.glob("*.json"):
                old.unlink()  # the demo's own records, so every demo run starts from the fixture
            for record in sorted((DEMO / "landing").glob("*.json")):
                shutil.copyfile(record, args.landing / record.name)
    landing = None if args.no_landing else (args.landing or Path("landing"))
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
            bets = load.linear_bets(args.linear_projects, args.include_closed)
            work = load.linear_work(args.linear_issues, args.include_closed) if args.linear_issues else []
            sources = {"bets": names(args.linear_projects), "work": names(args.linear_issues or [])}
        elif args.jira_search:
            bets, work = load.jira_search(args.jira_search, args.jira_bet_type)
            sources = {"bets": names(args.jira_search), "work": names(args.jira_search)}
        else:
            bets, work = load.jira(args.jira, args.jira_bet_type)
            sources = {"bets": args.jira.name, "work": args.jira.name}
        existing = loop.collect(landing, bets) if landing else None
        if landing:
            sources["records"] = f"{landing.name}/*.json"
        pf = score.review(bets, work, args.as_of, existing)
    except (load.LoadError, ValueError) as e:
        raise SystemExit(f"review: {e}") from None

    progress = {bid: loop.progress(rec) for bid, rec in existing.items()} if existing is not None else None
    markdown = render.to_markdown(pf, args.title, sources, args.illustrative, progress)
    args.out.mkdir(parents=True, exist_ok=True)
    out = {ext: args.out / f"{args.stem}.{ext}" for ext in ("md", "html", "json")}
    out["md"].write_text(markdown, encoding="utf-8")
    out["html"].write_text(render.to_html(pf, args.title, sources, args.illustrative, progress), encoding="utf-8")
    out["json"].write_text(render.to_json(pf, markdown, sources, args.illustrative, progress), encoding="utf-8")
    if landing and existing is not None:
        written = loop.write(landing, pf, sources, existing)
        print(f"review: wrote the portfolio key to {len(written)} loop record(s) in {landing}/.", file=sys.stderr)

    print(f"review: {len(pf.reviews)} bets, {pf.complete} with a brief that parses, {len(pf.orphans)} of {pf.work_total} work items linked to no bet.")
    for r in pf.reviews[:3]:
        print(f"  {r.rank}. {r.bet.id} {r.points}/{score.TOTAL}: {r.next_step}")
    print(f"review: wrote {out['md']}, {out['html'].name} and {out['json'].name}.", file=sys.stderr)
    failing = [f"{r.bet.id} ({g})" for r in pf.reviews for g in r.gaps if g in fail_on]
    if failing:
        print(f"review: --fail-on matched {len(failing)}: {', '.join(failing)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
