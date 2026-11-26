#!/usr/bin/env python3
"""Tests for the bet-portfolio-review skill, on the illustrative Acme fixture.

Usage:
  python3 -m unittest discover -s evals -v

Groups:
  Brief       brief completeness is landing_brief.parse's call, reported in its own words
  Status      landed, watch and stalled printed from the loop record, never computed
  Cost        cost shown from cost-budget-check's key, never computed
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
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKILL = ROOT / "skills" / "bet-portfolio-review"
SCRIPTS = SKILL / "scripts"
ACME = HERE / "fixtures" / "acme"
sys.path.insert(0, str(SCRIPTS))

import landing_brief  # noqa: E402
import load  # noqa: E402
import loop  # noqa: E402
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
    records = loop.collect(ACME / "landing", bets)
    return score.review(bets, load.csv_work(ACME / "work.csv"), AS_OF, records)


def by_id(pf: score.Portfolio) -> dict[str, score.Review]:
    return {r.bet.id: r for r in pf.reviews}


def parser_problems(text: str) -> list[str]:
    try:
        landing_brief.parse(text)
    except landing_brief.BriefError as e:
        return [x.strip() for x in str(e).splitlines()[1:] if x.strip()] or [str(e)]
    return []


class Brief(unittest.TestCase):
    """Brief completeness is landing_brief.parse's call; this skill reports its words and adds no list of its own."""

    def test_full_brief_scores_every_point(self):
        r = score.review_bet(bet(), [work()], AS_OF)
        self.assertEqual((r.points, r.percent, r.problems), (score.TOTAL, 100, []))
        self.assertEqual(r.gaps, ["no-result"])
        self.assertIsNotNone(r.brief)

    def test_no_brief(self):
        r = score.review_bet(bet(description="Just a paragraph."), [work()], AS_OF)
        self.assertEqual(r.gaps, ["no-brief"])
        self.assertEqual(r.points, score.WEIGHTS["owner"] + score.WEIGHTS["linked_work"])

    def test_missing_owner(self):
        r = score.review_bet(bet(owner=""), [work()], AS_OF)
        self.assertIn("no-owner", r.gaps)
        self.assertEqual(r.points, score.TOTAL - score.WEIGHTS["owner"])

    def test_problems_are_the_parsers_own_words(self):
        cases = [
            FULL.replace("- Bar: 40%", "- Bar: lots"),
            FULL.replace("- Better: higher", "- Better: up"),
            FULL.replace("- By: 2026-12-31", "- By: Q4"),
            FULL.replace("- Non-goals: No pricing advice.\n", ""),
            FULL.replace("- Price per token: $0.000003\n", ""),
            FULL.replace("9000", "none").replace("$0.000003", "none"),
            FULL + "- Mood: optimistic\n",
        ]
        for text in cases:
            with self.subTest(text=text[-60:]):
                r = score.review_bet(bet(text), [work()], AS_OF)
                self.assertEqual(r.problems, parser_problems(text))
                self.assertTrue(r.problems)
                self.assertIn("brief-problems", r.gaps)
                self.assertTrue(r.next_step.startswith("Fix the brief: "))
                self.assertIsNone(r.status)

    def test_no_keyword_list_of_brief_parts_outside_the_parser(self):
        for name in ("score.py", "load.py", "render.py", "loop.py", "review.py", "validate.py"):
            with self.subTest(name=name):
                text = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertNotRegex(text, r"[\"']non_goals[\"']|[\"']tokens_per_task[\"']\s*:|PART_COLUMNS|PLACEHOLDERS")

    def test_vendored_parser_check_matches_spec_auditor_shape(self):
        # spec-auditor turns each line after the first of BriefError into one finding; so does this skill.
        r = score.review_bet(bet(FULL.replace("- Metric: Quotes sent within 24 hours\n", "")), [work()], AS_OF)
        self.assertEqual(r.problems, ["metric is missing or empty."])

    def test_acme_gaps(self):
        r = by_id(acme())
        self.assertEqual(r["ACME-B5"].gaps, ["no-brief"])
        self.assertEqual(r["ACME-B6"].gaps, ["no-owner", "brief-problems"])
        self.assertEqual(r["ACME-B6"].problems, ["bar is missing or empty."])
        self.assertEqual(
            r["ACME-B4"].problems, ["non goals is missing or empty.", "tokens per task is missing or empty.", "price per token is missing or empty."]
        )
        self.assertEqual(r["ACME-B7"].gaps, ["no-work", "date-passed", "no-result"])


class Status(unittest.TestCase):
    """Landed, watch and stalled are did-it-land's. This skill prints them from the record and never computes one."""

    def test_acme_status_words_come_from_the_records(self):
        r = by_id(acme())
        self.assertEqual((r["ACME-B1"].status, r["ACME-B2"].status, r["ACME-B3"].status), ("landed", "stalled", "watch"))
        self.assertIsNone(r["ACME-B8"].status, "no record, no status word")

    def test_no_status_without_a_record(self):
        self.assertIsNone(score.review_bet(bet(), [work()], AS_OF).status)

    def test_record_status_is_printed_as_written(self):
        for word in ("landed", "watch", "stalled"):
            r = score.review_bet(bet(), [work()], AS_OF, {"landed": {"status": word}})
            self.assertEqual(r.status, word)

    def test_unknown_word_is_not_printed(self):
        self.assertIsNone(score.review_bet(bet(), [work()], AS_OF, {"landed": {"status": "shipped"}}).status)

    def test_no_status_rule_in_this_skills_code(self):
        for name in ("score.py", "render.py", "loop.py", "review.py"):
            self.assertNotIn("status_for", (SCRIPTS / name).read_text(encoding="utf-8"), name)

    def test_date_passed(self):
        early = FULL.replace("2026-12-31", "2026-11-01")
        r = score.review_bet(bet(early), [work()], AS_OF)
        self.assertIn("date-passed", r.gaps)
        self.assertIn("has passed", r.next_step)
        self.assertNotIn("date-passed", score.review_bet(bet(early), [work()], AS_OF, {"landed": {"status": "landed"}}).gaps)


class Orphans(unittest.TestCase):
    def test_acme_orphans(self):
        pf = acme()
        self.assertEqual([(o.work.id, o.why) for o in pf.orphans][:2], [("ACME-180", "no bet"), ("ACME-181", "no bet")])
        self.assertIn("ACME-B9", pf.orphans[2].why)
        self.assertEqual(pf.work_total, 19)
        self.assertEqual(pf.linked_percent, round(100 * 16 / 19))
        # B1, B2, B3 (3 each), B7 (0) and B8 (2) have a brief that parses.
        self.assertEqual(pf.judged_work, 11)

    def test_link_by_name(self):
        self.assertEqual(len(by_id(acme())["ACME-B5"].work), 2, "one item links by id, one by the bet's name")

    def test_orphan_move(self):
        self.assertEqual(score.orphan_move([]), "Every work item links to a bet on the roadmap.")
        lost = [score.Orphan(work(""), "no bet"), score.Orphan(work("X"), "links to X, which is not on the roadmap")]
        self.assertEqual(score.orphan_move(lost), "Link or cut: 1 item with no bet, 1 item linked to a bet not on the roadmap.")


class Ranking(unittest.TestCase):
    def test_acme_order(self):
        order = [r.bet.id for r in acme().reviews]
        self.assertEqual(order, ["ACME-B6", "ACME-B4", "ACME-B5", "ACME-B7", "ACME-B2", "ACME-B8", "ACME-B3", "ACME-B1"])

    def test_stalled_before_landed_at_equal_score(self):
        a, b = bet(bid="A", name="a"), bet(bid="B", name="b")
        records = {"A": {"landed": {"status": "landed"}}, "B": {"landed": {"status": "stalled"}}}
        pf = score.review([a, b], [work("A"), work("B", "W2")], AS_OF, records)
        self.assertEqual([r.status for r in pf.reviews], ["stalled", "landed"])

    def test_landed_bet_without_work_is_recorded_not_cut(self):
        r = score.review_bet(bet(), [], AS_OF, {"landed": {"status": "landed"}})
        self.assertIn("no-work", r.gaps)
        self.assertTrue(r.next_step.startswith("Record it as landed"))

    def test_one_next_step_each(self):
        steps = {r.bet.id: r.next_step for r in acme().reviews}
        self.assertTrue(steps["ACME-B6"].startswith("Name one owner"))
        self.assertTrue(steps["ACME-B5"].startswith("Payments squad lead writes the landing brief"))
        self.assertTrue(steps["ACME-B2"].startswith("Head of Product decides"))
        self.assertTrue(steps["ACME-B8"].startswith("Run did-it-land"))


class Cost(unittest.TestCase):
    """Cost per task is cost-budget-check's figure: shown from the `cost` key, never computed here."""

    def test_no_cost_key_says_so_and_prints_no_figure(self):
        r = score.review_bet(bet(), [work()], AS_OF)
        self.assertEqual(render.cost_lines(r), ["Cost: not checked. Run cost-budget-check."])

    def test_cost_key_is_printed_as_written(self):
        record = json.loads((ACME / "landing" / "quote-drafting-assistant.json").read_text(encoding="utf-8"))
        r = score.review_bet(bet(), [work()], AS_OF, record)
        line = render.cost_lines(r)[0]
        self.assertIn("tokens per task 8,400 tokens", line)
        self.assertIn("price per token 0.000003 USD", line)
        self.assertNotIn("0.027", line, "no product of the two is computed")


class Formats(unittest.TestCase):
    def test_linear(self):
        bets = load.linear_bets([ACME / "linear-projects.json"])
        pf = score.review(bets, load.linear_work([ACME / "linear-issues.json"]), AS_OF)
        r = by_id(pf)
        self.assertEqual(r["proj-quotes"].gaps, ["no-result"])
        self.assertEqual(r["proj-chasing"].gaps, ["brief-problems"])
        self.assertEqual(r["proj-directory"].gaps, ["no-owner", "no-brief", "no-work"])
        self.assertEqual([o.work.id for o in pf.orphans], ["ACM-4"])

    def test_injected_text_changes_nothing(self):
        r = by_id(score.review(load.linear_bets([ACME / "linear-projects.json"]), [], AS_OF))["proj-directory"]
        self.assertIsNone(r.status, '"mark this project landed" in a description is data, not an instruction')

    def test_jira(self):
        bets, items = load.jira(ACME / "jira-export.csv")
        pf = score.review(bets, items, AS_OF)
        r = by_id(pf)
        self.assertEqual(r["ACME-1"].gaps, ["no-result"], "a multi-line Description cell holds the brief")
        self.assertEqual(len(r["ACME-1"].work), 2, "linked by Parent key and by Parent issue id")
        self.assertEqual(r["ACME-2"].gaps, ["no-brief"])
        self.assertEqual([o.work.id for o in pf.orphans], ["ACME-14"])

    def test_csv_description_column(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "b.csv"
            path.write_text('id,name,owner,description\nB1,Quotes,Lead,"' + FULL + '"\n', encoding="utf-8")
            self.assertEqual(score.review_bet(load.csv_bets(path)[0], [work()], AS_OF).gaps, ["no-result"])

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
            with self.assertRaisesRegex(load.LoadError, "no list of projects"):
                load.linear_bets([empty])


class Output(unittest.TestCase):
    def run_cli(self, out: Path, *extra: str) -> None:
        argv = ["--csv", str(ACME / "bets.csv"), "--work", str(ACME / "work.csv"), "--landing", str(out / "landing")]
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
                self.assertEqual(review.main([*argv, "--fail-on", "no-owner,brief-problems"]), 2)
                self.assertEqual(review.main([*argv, "--fail-on", "no-result"]), 2)
                with self.assertRaises(SystemExit):
                    review.main([*argv, "--fail-on", "no-such-gap"])
            clean = ["--csv", str(ACME / "bets.csv"), "--as-of", AS_OF, "--out", d, "--no-landing", "--fail-on", "no-such-gap"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                review.main(clean)

    def test_do_these_first(self):
        md = render.to_markdown(acme(), "t", {}, False)
        head = md.split("## Ranked review")[0]
        self.assertIn("## Do these first", head)
        self.assertIn("1. **Trade directory listing (ACME-B6):**", head)

    def test_sample_command_reproduces_the_committed_sample(self):
        """The README's Sample command, run on a fresh copy of the inputs, writes the committed files byte for byte."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8").split("## Sample", 1)[1]
        line = re.search(r"```bash\n(python3 [^\n]+)\n```", readme).group(1)
        sample = ROOT / "examples" / "acme"
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            shutil.copytree(SKILL, tmp / "skills" / "bet-portfolio-review", ignore=shutil.ignore_patterns("__pycache__"))
            (tmp / "examples" / "acme" / "landing").mkdir(parents=True)
            for name in ("bets.csv", "work.csv"):
                shutil.copyfile(sample / name, tmp / "examples" / "acme" / name)
            shutil.copytree(sample / "briefs", tmp / "examples" / "acme" / "briefs")
            argv = shlex.split(line)
            self.assertEqual(argv[0], "python3")
            # The command is this repository's own README line, run with this interpreter on a temporary copy.
            done = subprocess.run([sys.executable, *argv[1:]], cwd=tmp, capture_output=True, text=True, check=False)  # noqa: S603
            self.assertEqual(done.returncode, 0, done.stderr)
            made = sorted(p.relative_to(tmp / "examples" / "acme") for p in (tmp / "examples" / "acme").rglob("*") if p.is_file())
            for rel in made:
                with self.subTest(file=str(rel)):
                    self.assertEqual((tmp / "examples" / "acme" / rel).read_bytes(), (sample / rel).read_bytes(), f"regenerate with: {line}")
            self.assertIn(Path("bet-portfolio-review.html"), made)
            self.assertIn(Path("landing") / "quote-drafting.json", made)

    def test_sample_record_holds_only_this_skills_key(self):
        record = json.loads((ROOT / "examples" / "acme" / "landing" / "quote-drafting.json").read_text(encoding="utf-8"))
        self.assertEqual(set(record), {"schema", "bet", "brief", "portfolio"})
        self.assertEqual(record["bet"], "quote-drafting")

    def test_brief_file_must_sit_inside_the_csv_folder(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bets.csv"
            path.write_text("id,name,owner,brief_file\nB1,One,Lead,../outside.md\n", encoding="utf-8")
            with self.assertRaises(load.LoadError):
                load.csv_bets(path)

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
        self.assertIn('<span class="st stalled">stalled</span>', page)
        self.assertIn(".st.stalled{color:var(--stalled)}", page, "the Leader Report's own stylesheet is inlined")
        self.assertIn("--stalled:#F0654F", page)


class Claims(unittest.TestCase):
    def setUp(self):
        pf = acme()
        self.md = render.to_markdown(pf, "Acme", {"bets": "bets.csv"}, True)
        self.data = json.loads(render.to_json(pf, self.md, {"bets": "bets.csv"}, True))

    def test_added_figure(self):
        errors = validate.check(self.md + "\nThe quote assistant saved 3,217 hours.\n", self.data)
        self.assertTrue(any("figure-not-computed: 3,217" in e for e in errors))

    def test_figure_moved_to_another_bet(self):
        # 40% is ACME-B1's bar; printing it on ACME-B2's row is refused even though 40 appears in the review.
        old = "| Invoice chasing (ACME-B2) | Payments squad lead |"
        edited = self.md.replace(old, "| Invoice chasing (ACME-B2), now at 40% | Payments squad lead |")
        self.assertIn("40", self.data["figures"])
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


class LiveFormats(unittest.TestCase):
    def test_linear_projects_csv_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "projects.csv"
            path.write_text('Name,Status,Lead,Description\nQuotes,started,Quotes squad lead,"' + FULL + '"\n', encoding="utf-8")
            bets = load.linear_bets([path])
            self.assertEqual((bets[0].id, bets[0].owner), ("Quotes", "Quotes squad lead"))
            self.assertEqual(score.review_bet(bets[0], [work("Quotes")], AS_OF).gaps, ["no-result"])

    def test_linear_issue_pages_overlap_once(self):
        items = load.linear_work([ACME / "linear-issues.json", ACME / "linear-issues.json"])
        self.assertEqual(len(items), 4, "from_linear.read_issues keeps one row per issue across pages")

    def test_jira_search_pages_with_rich_text(self):
        def para(text):
            return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

        brief = [{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Landing brief"}]}]
        brief.append({"type": "bulletList", "content": [{"type": "listItem", "content": [para(x[2:])]} for x in FULL.splitlines()[1:]]})
        page = {
            "issues": [
                {
                    "key": "Q-1",
                    "id": "100",
                    "fields": {
                        "summary": "Quotes",
                        "issuetype": {"name": "Epic"},
                        "assignee": {"displayName": "Quotes squad lead"},
                        "status": {"name": "In Progress"},
                        "description": {"type": "doc", "content": brief},
                    },
                },
                {
                    "key": "Q-2",
                    "id": "101",
                    "fields": {"summary": "Draft summary", "issuetype": {"name": "Story"}, "parent": {"key": "Q-1"}, "status": {"name": "Done"}},
                },
                {"key": "Q-3", "id": "102", "fields": {"summary": "Loose task", "issuetype": {"name": "Task"}, "status": {"name": "To Do"}}},
            ]
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "search.json"
            path.write_text(json.dumps(page), encoding="utf-8")
            bets, items = load.jira_search([path])
        pf = score.review(bets, items, AS_OF)
        self.assertEqual(pf.reviews[0].gaps, ["no-result"], "the brief is read from Atlassian Document Format")
        self.assertEqual([o.work.id for o in pf.orphans], ["Q-3"])

    def test_vendored_refusal_becomes_load_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text('{"nothing": 1}', encoding="utf-8")
            with self.assertRaisesRegex(load.LoadError, "from_linear"):
                load.linear_work([path])


class Loop(unittest.TestCase):
    def run_cli(self, landing: Path, out: Path) -> int:
        argv = ["--csv", str(ACME / "bets.csv"), "--work", str(ACME / "work.csv")]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return review.main([*argv, "--as-of", AS_OF, "--out", str(out), "--landing", str(landing)])

    def test_writes_only_the_portfolio_key(self):
        with tempfile.TemporaryDirectory() as d:
            landing = Path(d) / "landing"
            landing.mkdir()
            before = json.loads((ACME / "landing" / "invoice-chasing.json").read_text(encoding="utf-8"))
            (landing / "invoice-chasing.json").write_text(json.dumps(before), encoding="utf-8")
            self.run_cli(landing, Path(d) / "run")
            after = json.loads((landing / "invoice-chasing.json").read_text(encoding="utf-8"))
            self.assertEqual({k: v for k, v in after.items() if k != "portfolio"}, before, "every other key is kept exactly")
            self.assertEqual(list(after)[: len(before)], list(before))
            self.assertNotIn("note", after["portfolio"], "the fixture's brief hash matches")
            self.assertEqual(len(list(landing.glob("*.json"))), 8)

    def test_every_figure_carries_source_window_and_as_of(self):
        with tempfile.TemporaryDirectory() as d:
            landing = Path(d) / "landing"
            self.run_cli(landing, Path(d) / "run")
            record = json.loads((landing / "quote-drafting-assistant.json").read_text(encoding="utf-8"))
            self.assertEqual((record["schema"], record["bet"]), ("landing-loop/1", "quote-drafting-assistant"))
            self.assertEqual(len(record["brief"]["sha256"]), 64)
            figures = [v for v in record["portfolio"].values() if isinstance(v, dict)]
            self.assertEqual(len(figures), 4, "rank, readiness, readiness percent, linked work")
            for f in figures:
                self.assertEqual(set(f), {"value", "unit", "source", "window", "as_of"})
                self.assertTrue(f["source"])
                self.assertEqual(set(f["window"]), {"from", "to"})
            self.assertNotIn("cost_per_task_budget", record["portfolio"], "cost per task belongs to cost-budget-check")
            self.assertEqual(record["portfolio"]["brief_problems"], [])
            self.assertNotIn("status", record["portfolio"], "landed.status belongs to did-it-land")

    def test_changed_brief_is_noted_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            landing = Path(d) / "landing"
            landing.mkdir()
            rec = {"schema": "landing-loop/1", "bet": "invoice-chasing", "brief": {"path": "old", "sha256": "0" * 64}}
            (landing / "invoice-chasing.json").write_text(json.dumps(rec), encoding="utf-8")
            self.run_cli(landing, Path(d) / "run")
            after = json.loads((landing / "invoice-chasing.json").read_text(encoding="utf-8"))
            self.assertEqual(after["brief"], rec["brief"])
            self.assertIn("brief has changed", after["portfolio"]["note"])

    def test_refuses_a_file_that_is_not_a_loop_record(self):
        with tempfile.TemporaryDirectory() as d:
            landing = Path(d) / "landing"
            landing.mkdir()
            (landing / "invoice-chasing.json").write_text('{"something": "else"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                self.run_cli(landing, Path(d) / "run")
            self.assertEqual((landing / "invoice-chasing.json").read_text(encoding="utf-8"), '{"something": "else"}')

    def test_progress_shows_in_both_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                review.main(["--demo", "--out", str(out)])
            md = (out / "review.md").read_text(encoding="utf-8")
            self.assertIn("spec yes, evals yes, cost no, result stalled", md)
            self.assertIn('<span class="chip off">cost</span>', (out / "review.html").read_text(encoding="utf-8"))
            self.assertEqual(validate.check(md, json.loads((out / "review.json").read_text(encoding="utf-8"))), [])

    def test_loop_status_word_cannot_be_invented(self):
        p = loop.progress({"landed": {"status": "shipped"}})
        self.assertIsNone(p["landed_status"])
        self.assertEqual(loop.progress_text(p), "spec no, evals no, cost no, result yes")

    def test_no_landing_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            argv = ["--csv", str(ACME / "bets.csv"), "--as-of", AS_OF, "--out", str(Path(d) / "run"), "--landing", str(Path(d) / "l"), "--no-landing"]
            review.main(argv)
            self.assertFalse((Path(d) / "l").exists())


SUFFIXES = {".py", ".md", ".json", ".csv", ".yml", ".toml", ".html", ""}
FILES = [p for p in ROOT.rglob("*") if p.is_file() and not {".git", ".ruff_cache", "__pycache__"} & set(p.parts) and p.suffix in SUFFIXES]


class Hygiene(unittest.TestCase):
    def test_vendored_landing_brief_unchanged(self):
        digest = hashlib.sha256((SCRIPTS / "landing_brief.py").read_bytes()).hexdigest()
        self.assertEqual(digest, LANDING_BRIEF_SHA256)
        self.assertEqual(landing_brief.status_for(43, 36, 40, True), "landed")

    def test_every_vendored_file_matches_its_pinned_hash(self):
        manifest = json.loads((SKILL / "VENDORED.json").read_text(encoding="utf-8"))
        self.assertRegex(manifest["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(len(manifest["files"]), 5)
        for rel, info in manifest["files"].items():
            with self.subTest(file=rel):
                self.assertEqual(hashlib.sha256((SKILL / rel).read_bytes()).hexdigest(), info["sha256"])

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
