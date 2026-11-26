#!/usr/bin/env python3
"""Score each bet against its landing brief, find work linked to no bet, rank the bets and pick one next step each.

Every figure is computed here. The model reads the result; it never does the arithmetic.

The checks, and their weight in the brief score (14 points in all):
  owner         3  the bet names one owner (the Linear lead, the Jira assignee, the owner column)
  metric        3  the definition of good: a metric, a bar that is one number, higher or lower, a YYYY-MM-DD date
  cost budget   2  tokens per task and price per token, each one number; or both none when the line is fixed code
  non-goals     2  what the bet will not do ("none" does not count)
  problem       1  the problem, in the customer's terms
  the line      1  starts with "fixed code" or "model call"
  decider       1  "Decides the next step" names who decides
  linked work   1  at least one work item links to the bet
A bet with no "Landing brief" block fails every brief check and is flagged no-brief.

The status word (landed, watch, stalled) prints only when the metric check passes and a reading with a named source
exists. The rule is landing_brief.status_for, unchanged. Without that, the bet shows "no reading".

Orphan work is ported from Throughline's detectOrphans (lib/analysis/orphans.ts): an item with no bet, or one that
links to a bet not on the roadmap. Reading gaps are ported from deriveDataGaps (lib/analysis/data-gaps.ts):
a reading with no source cannot be audited, and a reading with no prior has no known direction.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import landing_brief
from load import Bet, Work

WEIGHTS = {
    "owner": 3,
    "metric": 3,
    "cost_budget": 2,
    "non_goals": 2,
    "problem": 1,
    "line": 1,
    "decider": 1,
    "linked_work": 1,
}
TOTAL = sum(WEIGHTS.values())
# The gap each failed check raises, in the order the next step is chosen from.
GAPS = {
    "owner": "no-owner",
    "brief": "no-brief",
    "metric": "no-metric",
    "cost_budget": "no-cost-budget",
    "non_goals": "no-non-goals",
    "problem": "no-problem",
    "line": "no-line",
    "decider": "no-decider",
    "linked_work": "no-work",
}
LABELS = {
    "no-owner": "No owner",
    "no-brief": "No landing brief",
    "no-metric": "No definition of good",
    "no-cost-budget": "No cost budget",
    "no-non-goals": "No non-goals",
    "no-problem": "No problem statement",
    "no-line": "No line between fixed code and a model call",
    "no-decider": "No one named to decide the next step",
    "no-work": "No work linked",
    "reading-no-source": "Reading has no source",
    "reading-no-history": "Reading has no prior value",
    "date-passed": "Date passed without landing",
    "never-read": "Metric never read",
}
ORDER = list(LABELS)
PLACEHOLDERS = {"", "tbd", "tbc", "todo", "n/a", "na", "-", "?", "unknown", "later"}
URGENCY = {"stalled": 0, None: 1, "watch": 2, "landed": 3}


@dataclass
class Review:
    bet: Bet
    parts: dict[str, str]
    passed: dict[str, bool]
    details: dict[str, str]
    gaps: list[str]
    points: int
    percent: int
    status: str | None
    brief: landing_brief.Brief | None
    work: list[Work] = field(default_factory=list)
    next_step: str = ""
    rank: int = 0
    cost_per_task: float | None = None


def parts_of(text: str) -> tuple[dict[str, str], list[str]]:
    """The brief's parts, read leniently so each gap can be named. Lines that are not a known part are returned too."""
    if not text or not any(landing_brief.HEADING.match(x.strip()) for x in text.splitlines()):
        return {}, []
    try:
        lines = landing_brief.section(text)
    except landing_brief.BriefError:
        return {}, []
    found: dict[str, str] = {}
    unread = []
    for raw in lines:
        line = raw.strip()
        if not line or landing_brief.ANY_HEADING.match(line):
            continue
        m = landing_brief.LINE.match(line)
        name = landing_brief.KEYS.get(m.group(1).strip().lower()) if m else None
        if not m or not name:
            unread.append(line[:80])
            continue
        text = m.group(2).strip().strip("*_").strip()
        # A placeholder is not an answer: "TBD" in a field must not earn its points.
        found.setdefault(name, "" if text.lower().strip(".?! ") in PLACEHOLDERS else text)
    return found, unread


def is_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def check(bet: Bet, work: list[Work]) -> tuple[dict[str, str], dict[str, bool], dict[str, str], bool]:
    p, unread = parts_of(bet.description)
    has_brief = bool(p)
    passed: dict[str, bool] = {}
    details: dict[str, str] = {}

    passed["owner"] = bool(bet.owner)
    passed["problem"] = bool(p.get("problem"))
    passed["decider"] = bool(p.get("decides"))
    nongoals = p.get("non_goals", "")
    passed["non_goals"] = bool(nongoals) and nongoals.lower().strip(". ") != "none"

    metric_missing = []
    if not p.get("metric"):
        metric_missing.append("a metric")
    if landing_brief.number(p.get("bar", "")) is None:
        metric_missing.append("a bar that is one number")
    if p.get("better", "").lower() not in ("higher", "lower"):
        metric_missing.append("higher or lower")
    if not is_date(p.get("by", "")):
        metric_missing.append("a YYYY-MM-DD date")
    passed["metric"] = not metric_missing
    if metric_missing and has_brief:
        details["no-metric"] = "Missing " + ", ".join(metric_missing) + "."

    line = p.get("line", "").lower()
    kind = next((k for k in landing_brief.LINES_ALLOWED if line.startswith(k)), None)
    passed["line"] = kind is not None
    tokens, price = p.get("tokens_per_task", ""), p.get("price_per_token", "")
    if tokens.lower() == "none" and price.lower() == "none":
        passed["cost_budget"] = kind == "fixed code"
        if kind != "fixed code" and has_brief:
            details["no-cost-budget"] = "The budget is none, but the line is not fixed code."
    else:
        bad = [n for n, v in (("tokens per task", tokens), ("price per token", price)) if landing_brief.number(v) is None]
        passed["cost_budget"] = not bad
        if bad and has_brief:
            details["no-cost-budget"] = "Missing or unreadable: " + " and ".join(bad) + "."
    passed["linked_work"] = bool(work)
    if unread:
        details["unread"] = f"{len(unread)} line(s) in the brief are not one of its parts."
    return p, passed, details, has_brief


def review_bet(bet: Bet, work: list[Work], as_of: str) -> Review:
    p, passed, details, has_brief = check(bet, work)
    gaps = [GAPS[c] for c in ("owner",) if not passed[c]]
    if not has_brief:
        gaps.append("no-brief")
    else:
        gaps += [GAPS[c] for c in ("metric", "cost_budget", "non_goals", "problem", "line", "decider") if not passed[c]]
    if not passed["linked_work"]:
        gaps.append("no-work")

    brief = None
    if all(passed[c] for c in ("metric", "cost_budget", "non_goals", "problem", "line", "decider")):
        try:
            brief = landing_brief.parse(bet.description)
        except landing_brief.BriefError as e:
            details["strict"] = str(e).split("\n", 1)[-1].strip()

    status = None
    reading = bet.reading
    if reading is not None and passed["metric"]:
        if not reading.source:
            gaps.append("reading-no-source")
        else:
            bar = landing_brief.number(p["bar"])
            assert bar is not None  # noqa: S101  (the metric check passed)
            status = landing_brief.status_for(reading.current, reading.prior, bar[1], p["better"].lower() == "higher")
            if reading.prior is None:
                gaps.append("reading-no-history")
    if passed["metric"] and reading is None:
        gaps.append("never-read")
    if passed["metric"] and status != "landed" and as_of > p["by"]:
        gaps.append("date-passed")

    points = sum(WEIGHTS[c] for c, ok in passed.items() if ok)
    cost = None
    if passed["cost_budget"] and landing_brief.number(p.get("tokens_per_task", "")) and landing_brief.number(p.get("price_per_token", "")):
        cost = landing_brief.number(p["tokens_per_task"])[1] * landing_brief.number(p["price_per_token"])[1]
    r = Review(
        bet=bet,
        parts=p,
        passed=passed,
        details=details,
        gaps=sorted(gaps, key=ORDER.index),
        points=points,
        percent=round(100 * points / TOTAL),
        status=status,
        brief=brief,
        work=work,
        cost_per_task=cost,
    )
    r.next_step = next_step(r)
    return r


def next_step(r: Review) -> str:
    """One next step, from the most important gap. Who decides is named when the brief names them."""
    p = r.parts
    who = p.get("decides") or r.bet.owner or "the bet's owner"
    metric = p.get("metric", "the metric")
    steps = {
        "no-owner": "Name one owner for this bet.",
        "no-brief": f"{r.bet.owner or 'The owner'} writes the landing brief: problem, definition of good, non-goals, cost budget, the line.",
        "no-metric": "Set the definition of good: one metric the team already measures, a bar, higher or lower, and a date.",
        "no-cost-budget": "State the cost budget as two lines, tokens per task and price per token, or mark the line fixed code.",
        "no-non-goals": "Write what this bet will not do.",
        "no-problem": "Write the problem in one or two sentences, in the customer's terms.",
        "no-line": 'Say where fixed code ends and a model call starts: begin the line with "fixed code" or "model call".',
        "no-decider": "Name the person who decides the next step when the reading comes in.",
        "no-work": "Link the work that delivers this bet, or cut the bet.",
        "reading-no-source": f"Name the source of the {metric} reading. Until then it earns no status word.",
    }
    for gap in r.gaps:
        if gap == "no-work" and r.status == "landed":
            continue  # a bet that has landed is recorded, not cut for want of linked work
        if gap in steps:
            return steps[gap]
    if "date-passed" in r.gaps:
        return f"The date, {p['by']}, has passed without landing. {who} decides: extend the date, change the approach or stop."
    if r.status is None:
        return f"Take the first reading of {metric} from its source and record it."
    if r.status == "landed":
        return f"Record it as landed. {who} decides what comes next."
    if r.status == "watch":
        return f"Take the next reading of {metric} before {p['by']}."
    return f"{who} decides: change the approach or stop the bet."


@dataclass
class Orphan:
    work: Work
    why: str


def orphans(bets: list[Bet], work: list[Work]) -> tuple[dict[str, list[Work]], list[Orphan]]:
    """Each bet's linked work, and the work linked to no bet on the roadmap. Port of Throughline's detectOrphans."""
    by_alias = {a: b.id for b in bets for a in b.aliases}
    linked: dict[str, list[Work]] = {b.id: [] for b in bets}
    lost = []
    for w in work:
        if not w.bet:
            lost.append(Orphan(w, "no bet"))
        elif w.bet.lower() not in by_alias:
            lost.append(Orphan(w, f"links to {w.bet}, which is not on the roadmap"))
        else:
            linked[by_alias[w.bet.lower()]].append(w)
    return linked, lost


def orphan_move(lost: list[Orphan]) -> str:
    """One line for the orphan work. Port of Throughline's orphanMove."""
    none = sum(1 for o in lost if o.why == "no bet")
    missing = len(lost) - none
    parts = []
    if none:
        parts.append(f"{none} item{'' if none == 1 else 's'} with no bet")
    if missing:
        parts.append(f"{missing} item{'' if missing == 1 else 's'} linked to a bet not on the roadmap")
    if not parts:
        return "Every work item links to a bet on the roadmap."
    return f"Link or cut: {', '.join(parts)}."


def rank(reviews: list[Review]) -> list[Review]:
    """Lowest brief score first; then stalled, no status, watch, landed; then most gaps; then bet id. Rank 1 needs work first."""
    ordered = sorted(reviews, key=lambda r: (r.percent, URGENCY[r.status], -len(r.gaps), r.bet.id.lower()))
    for i, r in enumerate(ordered, start=1):
        r.rank = i
    return ordered


@dataclass
class Portfolio:
    reviews: list[Review]
    orphans: list[Orphan]
    work_total: int
    as_of: str
    gap_counts: dict[str, int]
    complete: int
    statuses: dict[str, int]
    judged_work: int = 0

    @property
    def judged_percent(self) -> int | None:
        """Share of all work that sits under a bet with a complete definition of good: output that can be judged."""
        if not self.work_total:
            return None
        return round(100 * self.judged_work / self.work_total)

    @property
    def linked_percent(self) -> int | None:
        if not self.work_total:
            return None
        return round(100 * (self.work_total - len(self.orphans)) / self.work_total)


def review(bets: list[Bet], work: list[Work], as_of: str) -> Portfolio:
    if not is_date(as_of):
        raise ValueError(f"as-of is {as_of!r}. Write it as YYYY-MM-DD.")
    linked, lost = orphans(bets, work)
    reviews = rank([review_bet(b, linked[b.id], as_of) for b in bets])
    counts = {g: sum(1 for r in reviews if g in r.gaps) for g in ORDER}
    # A complete brief: every check but linked work, which is about the roadmap, not the brief.
    complete = sum(1 for r in reviews if all(ok for c, ok in r.passed.items() if c != "linked_work"))
    statuses = {s: sum(1 for r in reviews if r.status == s) for s in ("landed", "watch", "stalled")}
    statuses["with no status word"] = sum(1 for r in reviews if r.status is None)
    judged = sum(len(r.work) for r in reviews if r.passed["metric"])
    return Portfolio(reviews, lost, len(work), as_of, counts, complete, statuses, judged)
