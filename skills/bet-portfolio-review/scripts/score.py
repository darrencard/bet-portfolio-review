#!/usr/bin/env python3
"""Check each bet, find work linked to no bet, rank the bets and pick one next step each.

One owner per figure (Landing Loop contract, plans/landing-loop-contract-2026-11.md):
  - Brief completeness is the vendored landing_brief.py's call. This file keeps no list of brief parts: it calls
    landing_brief.parse and reports each problem the parser lists, word for word, as spec-auditor does.
  - Landed, watch and stalled belong to did-it-land. This file never computes one: it reads `landed.status` from the
    bet's loop record and prints it, or prints that there is no result yet.
  - Cost per task belongs to cost-budget-check. This file computes none; the review shows the `cost` key when present.

What this skill owns is the portfolio: whether each bet has an owner, whether its brief parses, whether any work
links to it, the rank, and the one next step. The readiness score (14 points):
  owner         3  the bet names one owner (the Linear lead, the Jira assignee, the owner column)
  brief        10  landing_brief.parse accepts the brief: every part present and readable
  linked work   1  at least one work item links to the bet

Orphan work is ported from Throughline's detectOrphans (lib/analysis/orphans.ts): an item with no bet, or one that
links to a bet not on the roadmap.

Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

import landing_brief
from load import Bet, Work

WEIGHTS = {"owner": 3, "brief": 10, "linked_work": 1}
TOTAL = sum(WEIGHTS.values())
LABELS = {
    "no-owner": "No owner",
    "no-brief": "No landing brief",
    "brief-problems": "Brief does not parse",
    "no-work": "No work linked",
    "date-passed": "Date passed, no result met the bar",
    "no-result": "No result yet",
}
ORDER = list(LABELS)
STATUS_WORDS = ("landed", "watch", "stalled")
URGENCY = {"stalled": 0, None: 1, "watch": 2, "landed": 3}


@dataclass
class Review:
    bet: Bet
    brief: landing_brief.Brief | None
    problems: list[str]
    passed: dict[str, bool]
    gaps: list[str]
    points: int
    percent: int
    status: str | None
    record: dict[str, Any] | None = None
    work: list[Work] = field(default_factory=list)
    next_step: str = ""
    rank: int = 0


def brief_check(text: str) -> tuple[landing_brief.Brief | None, list[str]]:
    """landing_brief.parse's verdict: the parsed brief, or every problem it lists, word for word."""
    try:
        return landing_brief.parse(text), []
    except landing_brief.BriefError as e:
        lines = [x.strip() for x in str(e).splitlines()[1:] if x.strip()]
        return None, lines or [str(e)]


def has_block(text: str) -> bool:
    return any(landing_brief.HEADING.match(x.strip()) for x in (text or "").splitlines())


def landed_status(record: dict[str, Any] | None) -> str | None:
    """The status did-it-land wrote, when it is one of the three words. Never computed here."""
    landed = (record or {}).get("landed")
    word = landed.get("status") if isinstance(landed, dict) else None
    return word if word in STATUS_WORDS else None


def review_bet(bet: Bet, work: list[Work], as_of: str, record: dict[str, Any] | None = None) -> Review:
    brief, problems = brief_check(bet.description)
    passed = {"owner": bool(bet.owner), "brief": brief is not None, "linked_work": bool(work)}
    status = landed_status(record)
    gaps = []
    if not passed["owner"]:
        gaps.append("no-owner")
    if not has_block(bet.description):
        gaps.append("no-brief")
    elif problems:
        gaps.append("brief-problems")
    if not passed["linked_work"]:
        gaps.append("no-work")
    if brief is not None and status != "landed" and as_of > brief.by:
        gaps.append("date-passed")
    if brief is not None and status is None:
        gaps.append("no-result")
    points = sum(WEIGHTS[c] for c, ok in passed.items() if ok)
    r = Review(bet, brief, problems, passed, sorted(gaps, key=ORDER.index), points, round(100 * points / TOTAL), status, record, work)
    r.next_step = next_step(r)
    return r


def next_step(r: Review) -> str:
    """One next step, from the most important gap. Who decides is named when the brief names them.

    Owners and deciders are often roles scoped to a team ("Lead, Quoting squad"), so the role is named as a label
    ("Owner: ...", "Decider: ...") and the step is an instruction; a scoped role never sits as a sentence's subject.
    """
    b = r.brief
    who = b.decides if b else (r.bet.owner or "the bet's owner")
    for gap in r.gaps:
        if gap == "no-owner":
            return "Name one owner for this bet."
        if gap == "no-brief":
            return f"Owner: {r.bet.owner or 'none named'}. Write the landing brief: problem, definition of good, non-goals, cost budget, the line."
        if gap == "brief-problems":
            return f"Fix the brief: {r.problems[0]}"
        if gap == "no-work" and r.status != "landed":
            return "Link the work that delivers this bet, or cut the bet."
    assert b is not None  # noqa: S101  (a bet with no brief problems has a parsed brief)
    if "date-passed" in r.gaps and r.status is None:
        return f"The date, {b.by}, has passed with no result yet. Run did-it-land on {b.metric}, then the decider chooses what comes next. Decider: {who}."
    if "date-passed" in r.gaps:
        return f"The date, {b.by}, has passed. Decider: {who}. Extend the date, change the approach or stop."
    if r.status is None and "spec" not in (r.record or {}):
        return "Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts."
    if r.status is None:
        return f"Run did-it-land on {b.metric} once it has a reading from its source."
    if r.status == "landed":
        return f"Record it as landed. Decider: {who}. Choose what comes next."
    if r.status == "watch":
        return f"Take the next reading of {b.metric} before {b.by}."
    return f"Decider: {who}. Change the approach or stop the bet."


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
    """Lowest score first; then more brief problems; then stalled, no result, watch, landed; then bet id."""
    ordered = sorted(reviews, key=lambda r: (r.percent, -len(r.problems), URGENCY[r.status], -len(r.gaps), r.bet.id.lower()))
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
        """Share of all work under a bet whose brief parses: output that can be judged."""
        if not self.work_total:
            return None
        return round(100 * self.judged_work / self.work_total)

    @property
    def linked_percent(self) -> int | None:
        if not self.work_total:
            return None
        return round(100 * (self.work_total - len(self.orphans)) / self.work_total)


def is_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def review(bets: list[Bet], work: list[Work], as_of: str, records: dict[str, dict[str, Any] | None] | None = None) -> Portfolio:
    if not is_date(as_of):
        raise ValueError(f"as-of is {as_of!r}. Write it as YYYY-MM-DD.")
    records = records or {}
    linked, lost = orphans(bets, work)
    reviews = rank([review_bet(b, linked[b.id], as_of, records.get(b.id)) for b in bets])
    counts = {g: sum(1 for r in reviews if g in r.gaps) for g in ORDER}
    complete = sum(1 for r in reviews if r.passed["brief"])
    statuses = {s: sum(1 for r in reviews if r.status == s) for s in STATUS_WORDS}
    statuses["with no result yet"] = sum(1 for r in reviews if r.status is None)
    judged = sum(len(r.work) for r in reviews if r.passed["brief"])
    return Portfolio(reviews, lost, len(work), as_of, counts, complete, statuses, judged)
