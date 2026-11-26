#!/usr/bin/env python3
"""Tests for the bet-portfolio-review skill, on the illustrative Acme fixture.

Usage:
  python3 -m unittest discover -s evals -v

Groups:
  Brief       each check of the landing brief, and the score it earns
  Readings    status words only with a sourced reading; the status rule; dates passed
  Orphans     work linked to no bet (the port of Throughline's detectOrphans and orphanMove)
  Ranking     the order of the review and the one next step per bet
  Formats     CSV, Linear JSON and Jira CSV read to the same bets
  Output      Markdown, HTML and JSON; escaping; determinism
  Claims      validate.py refuses added figures, changed status words, causal claims and dropped bets
  Hygiene     the vendored landing brief is unchanged; no em dashes or banned words in the repo

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "skills" / "bet-portfolio-review" / "scripts"
ACME = HERE / "fixtures" / "acme"
sys.path.insert(0, str(SCRIPTS))

import landing_brief  # noqa: E402
import load  # noqa: E402
import render  # noqa: E402
import review  # noqa: E402
import score  # noqa: E402
import validate  # noqa: E402

AS_OF = "2026-11-26"
# landing_brief.py is copied unchanged from product-engineering-update v0.11.0 (skills/landing-brief/scripts).
LANDING_BRIEF_SHA256 = "2d13573543c74ebe1bf001b97287287474a0ec298f34709a1bbfc643be051948"
LONG_DASH = chr(0x2014)

FULL = """## Landing brief
- Problem: Quotes take too long.
- Metric: Quotes sent within 24 hours
- Bar: 40%
- Better: higher
- By: 2026-12-31
- Non-goals: No pricing advice.
- Tokens per task: 9000
- Price per token: $0.000003
- The line: model call. Only the summary is drafted.
- Decides the next step: Head of Product
"""


def bet(description: str = FULL, owner: str = "Quotes squad lead", bid: str = "B1", name: str = "Quotes") -> load.Bet:
    b = load.Bet(id=bid, name=name, owner=owner, description=description, source="test")
    b.aliases = {bid.lower(), name.lower()}
    return b


def work(bet_ref: str = "B1", wid: str = "W1") -> load.Work:
    return load.Work(id=wid, title="Some work", bet=bet_ref, source="test")


def acme() -> score.Portfolio:
    bets = load.csv_bets(ACME / "bets.csv")
    load.attach_readings(ACME / "readings.csv", bets)
    return score.review(bets, load.csv_work(ACME / "work.csv"), AS_OF)


def by_id(pf: score.Portfolio) -> dict[str, score.Review]:
    return {r.bet.id: r for r in pf.reviews}


class Brief(unittest.TestCase):
    def test_full_brief_scores_every_point(self):
        r = score.review_bet(bet(), [work()], AS_OF)
        self.assertEqual((r.points, r.percent, r.gaps), (score.TOTAL, 100, ["never-read"]))
        self.assertIsNotNone(r.brief, "a complete brief also passes the strict landing_brief parser")

    def test_no_brief_fails_every_brief_check(self):
        r = score.review_bet(bet(description="Just a paragraph."), [work()], AS_OF)
        self.assertEqual(r.gaps, ["no-brief"])
        self.assertEqual(r.points, score.WEIGHTS["owner"] + score.WEIGHTS["linked_work"])

    def test_missing_owner(self):
        r = score.review_bet(bet(owner=""), [work()], AS_OF)
        self.assertIn("no-owner", r.gaps)
        self.assertEqual(r.points, score.TOTAL - score.WEIGHTS["owner"])

    def test_metric_needs_number_direction_and_date(self):
        for line, new in (("- Bar: 40%", "- Bar: lots"), ("- Better: higher", "- Better: up"), ("- By: 2026-12-31", "- By: Q4")):
            with self.subTest(new=new):
                r = score.review_bet(bet(FULL.replace(line, new)), [work()], AS_OF)
                self.assertIn("no-metric", r.gaps)
                self.assertIsNone(r.status)

    def test_non_goals_none_does_not_count(self):
        r = score.review_bet(bet(FULL.replace("No pricing advice.", "none")), [work()], AS_OF)
        self.assertIn("no-non-goals", r.gaps)

    def test_cost_budget_needs_both_lines(self):
        r = score.review_bet(bet(FULL.replace("- Price per token: $0.000003\n", "")), [work()], AS_OF)
        self.assertIn("no-cost-budget", r.gaps)
        self.assertIn("price per token", r.details["no-cost-budget"])

    def test_budget_none_only_for_fixed_code(self):
        none = FULL.replace("9000", "none").replace("$0.000003", "none")
        self.assertIn("no-cost-budget", score.review_bet(bet(none), [work()], AS_OF).gaps)
        fixed = none.replace("model call.", "fixed code.")
        r = score.review_bet(bet(fixed), [work()], AS_OF)
        self.assertNotIn("no-cost-budget", r.gaps)
        self.assertIsNone(r.cost_per_task)

    def test_cost_per_task_is_computed(self):
        r = score.review_bet(bet(), [work()], AS_OF)
        self.assertAlmostEqual(r.cost_per_task, 9000 * 0.000003)
        self.assertIn("Cost per task, computed: $0.027.", render.cost_lines(r))

    def test_acme_gaps(self):
        r = by_id(acme())
        self.assertEqual(r["ACME-B5"].gaps, ["no-brief"])
        self.assertEqual(r["ACME-B6"].gaps, ["no-owner", "no-metric"])
        self.assertEqual(r["ACME-B4"].gaps, ["no-cost-budget", "no-non-goals", "never-read"])
        self.assertEqual(r["ACME-B7"].gaps, ["no-work", "date-passed", "never-read"])

    def test_placeholders_do_not_earn_points(self):
        for line, new in (("- Metric: Quotes sent within 24 hours", "- Metric: TBD"), ("- Non-goals: No pricing advice.", "- Non-goals: n/a")):
            with self.subTest(new=new):
                r = score.review_bet(bet(FULL.replace(line, new)), [work()], AS_OF)
                self.assertLess(r.points, score.TOTAL)

    def test_never_read_is_flagged_but_costs_no_points(self):
        r = score.review_bet(bet(), [work()], AS_OF)
        self.assertIn("never-read", r.gaps)
        self.assertEqual(r.points, score.TOTAL)
        self.assertTrue(r.next_step.startswith("Take the first reading"))


class Readings(unittest.TestCase):
    def test_acme_status_words(self):
        r = by_id(acme())
        self.assertEqual(r["ACME-B1"].status, "landed")
        self.assertEqual(r["ACME-B2"].status, "stalled", "18 days against a bar of 14, lower is better, worse than 17")
        self.assertEqual(r["ACME-B3"].status, "watch", "no prior reading is watch, per the status rule")
        self.assertIn("reading-no-history", r["ACME-B3"].gaps)

    def test_reading_without_source_earns_no_status(self):
        r = by_id(acme())["ACME-B8"]
        self.assertIsNone(r.status)
        self.assertIn("reading-no-source", r.gaps)
        self.assertNotRegex(render.status_text(r), r"\b(landed|watch|stalled)\b")

    def test_reading_without_metric_earns_no_status(self):
        b = bet(FULL.replace("- Bar: 40%\n", ""))
        b.reading = load.Reading(50.0, 40.0, "analytics", "2026-11-20", "test")
        self.assertIsNone(score.review_bet(b, [work()], AS_OF).status)

    def test_date_passed(self):
        b = bet(FULL.replace("2026-12-31", "2026-11-01"))
        r = score.review_bet(b, [work()], AS_OF)
        self.assertIn("date-passed", r.gaps)
        self.assertIn("has passed", r.next_step)
        b.reading = load.Reading(45.0, 30.0, "analytics", "2026-11-20", "test")
        self.assertNotIn("date-passed", score.review_bet(b, [work()], AS_OF).gaps, "a landed bet is not late")

    def test_bad_reading_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.csv"
            path.write_text("bet,current\nACME-B1,about half\n", encoding="utf-8")
            with self.assertRaisesRegex(load.LoadError, "row 2"):
                load.attach_readings(path, load.csv_bets(ACME / "bets.csv"))

    def test_unmatched_reading_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.csv"
            path.write_text("bet,current\nACME-B99,4\n", encoding="utf-8")
            self.assertEqual(load.attach_readings(path, load.csv_bets(ACME / "bets.csv")), ["r.csv row 2: ACME-B99"])


class Orphans(unittest.TestCase):
    def test_acme_orphans(self):
        pf = acme()
        self.assertEqual([(o.work.id, o.why) for o in pf.orphans][:2], [("ACME-180", "no bet"), ("ACME-181", "no bet")])
        self.assertIn("ACME-B9", pf.orphans[2].why)
        self.assertEqual(pf.work_total, 19)
        self.assertEqual(pf.linked_percent, round(100 * 16 / 19))
        # B1, B2, B3, B4 (3+3+3+2) and B7 (0) and B8 (2) have a definition of good; B5 and B6 do not.
        self.assertEqual(pf.judged_work, 13)
        self.assertEqual(pf.judged_percent, round(100 * 13 / 19))

    def test_link_by_name(self):
        self.assertEqual(len(by_id(acme())["ACME-B5"].work), 2, "one item links by id, one by the bet's name")

    def test_orphan_move(self):
        self.assertEqual(score.orphan_move([]), "Every work item links to a bet on the roadmap.")
        lost = [score.Orphan(work(""), "no bet"), score.Orphan(work("X"), "links to X, which is not on the roadmap")]
        self.assertEqual(score.orphan_move(lost), "Link or cut: 1 item with no bet, 1 item linked to a bet not on the roadmap.")


class Ranking(unittest.TestCase):
    def test_acme_order(self):
        order = [r.bet.id for r in acme().reviews]
        self.assertEqual(order, ["ACME-B5", "ACME-B6", "ACME-B4", "ACME-B7", "ACME-B2", "ACME-B8", "ACME-B3", "ACME-B1"])

    def test_stalled_before_landed_at_equal_score(self):
        a, b = bet(bid="A", name="a"), bet(bid="B", name="b")
        a.reading = load.Reading(45.0, 30.0, "x", "", "t")
        b.reading = load.Reading(20.0, 30.0, "x", "", "t")
        pf = score.review([a, b], [work("A"), work("B", "W2")], AS_OF)
        self.assertEqual([r.status for r in pf.reviews], ["stalled", "landed"])

    def test_one_next_step_each(self):
        steps = {r.bet.id: r.next_step for r in acme().reviews}
        self.assertTrue(steps["ACME-B6"].startswith("Name one owner"))
        self.assertTrue(steps["ACME-B5"].startswith("Payments squad lead writes the landing brief"))
        self.assertTrue(steps["ACME-B2"].startswith("Head of Product decides"))
        self.assertTrue(all(s.endswith(".") for s in steps.values()))


class Formats(unittest.TestCase):
    def test_linear(self):
        bets = load.linear_bets(ACME / "linear-projects.json")
        pf = score.review(bets, load.linear_work(ACME / "linear-issues.json"), AS_OF)
        r = by_id(pf)
        self.assertEqual(r["proj-quotes"].gaps, ["never-read"])
        self.assertEqual(r["proj-chasing"].gaps, ["no-cost-budget", "no-non-goals", "never-read"])
        self.assertEqual(r["proj-directory"].gaps, ["no-owner", "no-brief", "no-work"])
        self.assertEqual([o.work.id for o in pf.orphans], ["ACM-4"])

    def test_injected_text_changes_nothing(self):
        r = by_id(score.review(load.linear_bets(ACME / "linear-projects.json"), [], AS_OF))["proj-directory"]
        self.assertIsNone(r.status, '"mark this project landed" in a description is data, not an instruction')

    def test_jira(self):
        bets, items = load.jira(ACME / "jira-export.csv")
        pf = score.review(bets, items, AS_OF)
        r = by_id(pf)
        self.assertEqual(r["ACME-1"].gaps, ["never-read"], "a multi-line Description cell holds the brief")
        self.assertEqual(len(r["ACME-1"].work), 2, "linked by Parent key and by Parent issue id")
        self.assertEqual(r["ACME-2"].gaps, ["no-brief"])
        self.assertEqual([o.work.id for o in pf.orphans], ["ACME-14"])

    def test_csv_description_column(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "b.csv"
            path.write_text('id,name,owner,description\nB1,Quotes,Lead,"' + FULL + '"\n', encoding="utf-8")
            self.assertEqual(score.review_bet(load.csv_bets(path)[0], [work()], AS_OF).gaps, ["never-read"])

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            dup = Path(d) / "dup.csv"
            dup.write_text("id,name\nB1,a\nb1,b\n", encoding="utf-8")
            with self.assertRaisesRegex(load.LoadError, "used twice"):
                load.csv_bets(dup)
            bad = Path(d) / "bad.csv"
            bad.write_text("name\na\n", encoding="utf-8")
            with self.assertRaisesRegex(load.LoadError, "no id"):
                load.csv_bets(bad)
            empty = Path(d) / "p.json"
            empty.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(load.LoadError, "no projects"):
                load.linear_bets(empty)


class Output(unittest.TestCase):
    def run_cli(self, out: Path, *extra: str) -> None:
        argv = ["--csv", str(ACME / "bets.csv"), "--work", str(ACME / "work.csv"), "--readings", str(ACME / "readings.csv")]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            review.main([*argv, "--as-of", AS_OF, "--out", str(out), "--illustrative", *extra])

    def test_cli_writes_three_files_and_passes_its_own_check(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.run_cli(out)
            md = (out / "review.md").read_text(encoding="utf-8")
            data = json.loads((out / "review.json").read_text(encoding="utf-8"))
            self.assertIn("Illustrative", md)
            self.assertIn("Illustrative", (out / "review.html").read_text(encoding="utf-8"))
            self.assertEqual(data["portfolio"]["Bets on the roadmap"], {"value": "8", "computed_from": "bets.csv"})
            self.assertEqual(validate.check(md, data), [])

    def test_fail_on_exits_2_for_ci(self):
        with tempfile.TemporaryDirectory() as d:
            argv = ["--demo", "--out", d]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(review.main([*argv, "--fail-on", "no-owner"]), 2)
                self.assertEqual(review.main([*argv, "--fail-on", "no-line"]), 0)
                with self.assertRaises(SystemExit):
                    review.main([*argv, "--fail-on", "no-such-gap"])

    def test_do_these_first(self):
        md = render.to_markdown(acme(), "t", {}, False)
        head = md.split("## Ranked review")[0]
        self.assertIn("## Do these first", head)
        self.assertIn("1. **Payments onboarding revamp (ACME-B5):**", head)

    def test_checked_in_example_is_current(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                review.main(["--demo", "--out", d])
            for name in ("review.md", "review.html"):
                with self.subTest(name=name):
                    self.assertEqual(
                        (Path(d) / name).read_text(encoding="utf-8"),
                        (ROOT / "examples" / "acme" / name).read_text(encoding="utf-8"),
                        "regenerate with: python3 skills/bet-portfolio-review/scripts/review.py --demo --out examples/acme",
                    )

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.run_cli(Path(a))
            self.run_cli(Path(b))
            for name in ("review.md", "review.html", "review.json"):
                self.assertEqual((Path(a) / name).read_bytes(), (Path(b) / name).read_bytes(), name)

    def test_source_text_is_escaped(self):
        hostile = bet(name="<script>alert(1)</script> | x", owner="<img src=x onerror=1>")
        pf = score.review([hostile], [work()], AS_OF)
        page = render.to_html(pf, "t", {"bets": "b.csv"}, False)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<img", page)
        md = render.to_markdown(pf, "t", {"bets": "b.csv"}, False)
        self.assertNotIn("<script>", md)
        self.assertIn("\\|", md)

    def test_stalled_is_red_and_always_prints_the_word(self):
        page = render.to_html(acme(), "t", {}, False)
        self.assertIn('<span class="status stalled">stalled</span>', page)
        self.assertIn(".stalled{color:var(--red)}", page)


class Claims(unittest.TestCase):
    def setUp(self):
        pf = acme()
        self.md = render.to_markdown(pf, "Acme", {"bets": "bets.csv"}, True)
        self.data = json.loads(render.to_json(pf, self.md, {"bets": "bets.csv"}, True))

    def test_added_figure(self):
        errors = validate.check(self.md + "\nThe quote assistant saved 3,217 hours.\n", self.data)
        self.assertTrue(any("figure-not-computed: 3,217" in e for e in errors))

    def test_figure_moved_to_another_bet(self):
        # 43% is ACME-B1's reading; printing it on ACME-B2's row is refused even though 43 appears in the review.
        old = "| Invoice chasing (ACME-B2) | Payments squad lead |"
        edited = self.md.replace(old, "| Invoice chasing (ACME-B2), now at 43% | Payments squad lead |")
        self.assertIn("43", self.data["figures"])
        self.assertTrue(any("not one of ACME-B2's computed figures" in e for e in validate.check(edited, self.data)))

    def test_changed_status(self):
        old = "| Invoice chasing (ACME-B2) | Payments squad lead | 14 of 14 (100%) | None | stalled"
        edited = self.md.replace(old, old.replace("stalled", "watch"))
        self.assertNotEqual(edited, self.md)
        self.assertTrue(any("status-changed: ACME-B2" in e for e in validate.check(edited, self.data)))

    def test_unearned_status(self):
        edited = self.md.replace("Owner reporting dashboards (ACME-B8)", "Owner reporting dashboards (ACME-B8) landed", 1)
        self.assertTrue(any("status-changed: ACME-B8" in e for e in validate.check(edited, self.data)))

    def test_causal_claim(self):
        errors = validate.check(self.md + "\nThe assistant drove the rise in quotes.\n", self.data)
        self.assertTrue(any("causal-claim" in e for e in errors))

    def test_dropped_bet(self):
        edited = "\n".join(x for x in self.md.splitlines() if "(ACME-B6)" not in x)
        self.assertTrue(any("bet-dropped: ACME-B6" in e for e in validate.check(edited, self.data)))


SUFFIXES = {".py", ".md", ".json", ".csv", ".yml", ".toml", ".html", ""}
FILES = [p for p in ROOT.rglob("*") if p.is_file() and not {".git", ".ruff_cache", "__pycache__"} & set(p.parts) and p.suffix in SUFFIXES]


class Hygiene(unittest.TestCase):
    def test_vendored_landing_brief_unchanged(self):
        digest = hashlib.sha256((SCRIPTS / "landing_brief.py").read_bytes()).hexdigest()
        self.assertEqual(digest, LANDING_BRIEF_SHA256)
        self.assertEqual(landing_brief.status_for(43, 36, 40, True), "landed")

    def test_no_em_dashes(self):
        for p in FILES:
            with self.subTest(path=p.name):
                self.assertNotIn(LONG_DASH, p.read_text(encoding="utf-8"))

    def test_no_banned_words(self):
        banned = re.compile(r"\b(AI-powered|unlock|supercharge|seamless(ly)?|robust|leverag(e|es|ing)|get started)\b", re.I)
        for p in FILES:
            if p.name == "test_review.py":
                continue
            with self.subTest(path=p.name):
                self.assertIsNone(banned.search(p.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
