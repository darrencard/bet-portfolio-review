#!/usr/bin/env python3
"""Read a roadmap of bets, the work under them and any metric readings, from CSV, Linear JSON or a Jira CSV export.

Every bet and work item keeps a `source` (file and row, or file and id) so each line of the review traces back.
Text read from a file is data: it is stored and shown, never acted on.

Formats:
  csv     bets.csv (id, name, owner, then either a description holding a "Landing brief" block, or one column per
          part: problem, metric, bar, better, by, non_goals, tokens_per_task, price_per_token, line, decides)
          and work.csv (id, title, bet).
  linear  the projects JSON from the Linear connector (list_projects or get_project, saved as it stands), and the
          issues JSON (list_issues). A project is a bet; an issue links to a bet through its project.
  jira    one Jira CSV export. Rows of the bet type (Epic by default) are bets; every other row is work, linked
          through Parent, Parent key, Parent id or the Epic Link field.
  readings.csv (optional, any format): bet, current, prior, source, date. A reading with no source is kept but
          never earns a status word.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import landing_brief

MAX_BYTES = 20_000_000
MAX_CELL = 20_000
PART_COLUMNS = {
    "problem": "Problem",
    "metric": "Metric",
    "bar": "Bar",
    "better": "Better",
    "by": "By",
    "non_goals": "Non-goals",
    "tokens_per_task": "Tokens per task",
    "price_per_token": "Price per token",
    "line": "The line",
    "decides": "Decides the next step",
}


class LoadError(ValueError):
    """An input that cannot be read. The message says which file and row, and how to fix it."""


@dataclass
class Bet:
    id: str
    name: str
    owner: str
    description: str
    source: str
    aliases: set[str] = field(default_factory=set)
    reading: Reading | None = None


@dataclass
class Work:
    id: str
    title: str
    bet: str
    source: str


@dataclass(frozen=True)
class Reading:
    current: float
    prior: float | None
    source: str
    date: str
    where: str


def key(text: str) -> str:
    """A column name in one form: lower case, spaces and hyphens as underscores."""
    return re.sub(r"[\s\-]+", "_", text.strip().lower())


def clean(value: Any) -> str:
    """One cell as plain text, capped, with surrounding space removed."""
    if value is None:
        return ""
    return str(value).strip()[:MAX_CELL]


def read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_BYTES:
            raise LoadError(f"{path} is over {MAX_BYTES:,} bytes. Export a smaller range.")
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise LoadError(f"cannot read {path} ({e}). Save it as UTF-8.") from None


def rows(path: Path) -> list[dict[str, str]]:
    """CSV rows with normalised column names. The first of two same-named columns wins."""
    reader = csv.reader(io.StringIO(read_text(path), newline=""))
    try:
        header = next(reader)
    except StopIteration:
        raise LoadError(f"{path} is empty.") from None
    names = [key(h) for h in header]
    out = []
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue
        row: dict[str, str] = {}
        for name, cell in zip(names, cells):
            if name and name not in row:
                row[name] = clean(cell)
        out.append(row)
    return out


def need(path: Path, found: list[dict[str, str]], *columns: str) -> None:
    present = set(found[0]) if found else set()
    missing = [c for c in columns if c not in present]
    if missing:
        raise LoadError(f"{path} has no {', '.join(missing)} column. Use assets/bets-template.csv or assets/work-template.csv.")


def brief_from_columns(row: dict[str, str]) -> str:
    """A "Landing brief" block built from per-part columns, so one parser reads every format."""
    lines = [f"- {label}: {' '.join(row[col].split())}" for col, label in PART_COLUMNS.items() if row.get(col)]
    return "## Landing brief\n" + "\n".join(lines) if lines else ""


def has_heading(text: str) -> bool:
    return any(landing_brief.HEADING.match(line.strip()) for line in text.splitlines())


def check_unique(bets: list[Bet]) -> None:
    seen: dict[str, str] = {}
    for bet in bets:
        if not bet.id:
            raise LoadError(f"{bet.source} has no id. Every bet needs one.")
        if bet.id.lower() in seen:
            raise LoadError(f"bet id {bet.id} is used twice ({seen[bet.id.lower()]} and {bet.source}). Keep one.")
        seen[bet.id.lower()] = bet.source


def csv_bets(path: Path) -> list[Bet]:
    found = rows(path)
    need(path, found, "id", "name")
    bets = []
    for i, row in enumerate(found, start=2):
        text = row.get("description", "")
        if not has_heading(text):
            text = brief_from_columns(row) or text
        bet = Bet(id=row["id"], name=row["name"] or row["id"], owner=row.get("owner", ""), description=text, source=f"{path.name} row {i}")
        bet.aliases = {bet.id.lower(), bet.name.lower()}
        bets.append(bet)
    check_unique(bets)
    return bets


def csv_work(path: Path) -> list[Work]:
    found = rows(path)
    need(path, found, "id", "title", "bet")
    return [Work(id=r["id"], title=r["title"], bet=r["bet"], source=f"{path.name} row {i}") for i, r in enumerate(found, start=2)]


def nodes(data: Any, *names: str) -> list[dict[str, Any]]:
    """The list of objects in a connector's JSON: a bare list, {name: [...]}, {name: {nodes: [...]}} or {data: ...}."""
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if isinstance(data, dict):
        for name in (*names, "nodes", "items", "results"):
            if name in data:
                data = data[name]
                break
        else:
            data = [data] if "id" in data else []
        if isinstance(data, dict):
            data = data.get("nodes", [])
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def person(value: Any) -> str:
    if isinstance(value, dict):
        return clean(value.get("name") or value.get("displayName") or value.get("email"))
    return clean(value)


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise LoadError(f"{path} is not valid JSON ({e.msg}, line {e.lineno}).") from None


def linear_bets(path: Path) -> list[Bet]:
    bets = []
    for project in nodes(load_json(path), "projects", "project"):
        pid = clean(project.get("id") or project.get("slugId"))
        name = clean(project.get("name")) or pid
        texts = [clean(project.get(k)) for k in ("content", "description") if isinstance(project.get(k), str)]
        text = next((t for t in texts if has_heading(t)), texts[0] if texts else "")
        bet = Bet(id=pid, name=name, owner=person(project.get("lead")), description=text, source=f"{path.name} project {pid}")
        bet.aliases = {a.lower() for a in (pid, name, clean(project.get("slugId"))) if a}
        bets.append(bet)
    if not bets:
        raise LoadError(f"{path} holds no projects. Save the JSON from the Linear connector's list_projects as it stands.")
    check_unique(bets)
    return bets


def linear_work(path: Path) -> list[Work]:
    out = []
    for issue in nodes(load_json(path), "issues", "issue"):
        iid = clean(issue.get("identifier") or issue.get("id"))
        project = issue.get("project")
        ref = clean(project.get("id") or project.get("name")) if isinstance(project, dict) else clean(project or issue.get("projectId"))
        out.append(Work(id=iid, title=clean(issue.get("title")), bet=ref, source=f"{path.name} issue {iid}"))
    return out


JIRA_PARENT = ("parent", "parent_key", "parent_id", "custom_field_(epic_link)", "epic_link")


def jira(path: Path, bet_type: str = "Epic") -> tuple[list[Bet], list[Work]]:
    found = rows(path)
    need(path, found, "issue_key", "summary", "issue_type")
    bets, work = [], []
    for i, row in enumerate(found, start=2):
        where = f"{path.name} row {i}"
        if row["issue_type"].lower() == bet_type.lower():
            bet = Bet(id=row["issue_key"], name=row["summary"], owner=row.get("assignee", ""), description=row.get("description", ""), source=where)
            bet.aliases = {a.lower() for a in (row["issue_key"], row.get("issue_id", "")) if a}
            bets.append(bet)
        else:
            parent = next((row[c] for c in JIRA_PARENT if row.get(c)), "")
            work.append(Work(id=row["issue_key"], title=row["summary"], bet=parent, source=where))
    if not bets:
        raise LoadError(f"{path} has no rows of issue type {bet_type}. Pass --jira-bet-type with the type your bets use.")
    check_unique(bets)
    return bets, work


def value(text: str, where: str, column: str) -> float | None:
    if not text:
        return None
    parsed = landing_brief.number(text)
    if parsed is None:
        raise LoadError(f'{where}: {column} is "{text[:40]}". Write one number, such as 46%, 18 or $0.30.')
    return parsed[1]


def attach_readings(path: Path, bets: list[Bet]) -> list[str]:
    """Attach each reading to its bet. Returns the readings that match no bet, so the review can show them."""
    found = rows(path)
    need(path, found, "bet", "current")
    by_alias = {a: b for b in bets for a in b.aliases}
    unmatched = []
    for i, row in enumerate(found, start=2):
        where = f"{path.name} row {i}"
        bet = by_alias.get(row["bet"].lower())
        if bet is None:
            unmatched.append(f"{where}: {row['bet']}")
            continue
        if bet.reading is not None:
            raise LoadError(f"{where}: {bet.id} already has a reading ({bet.reading.where}). Keep the latest one.")
        current = value(row["current"], where, "current")
        if current is None:
            raise LoadError(f"{where}: current is empty. Leave the bet out instead; never estimate a reading.")
        bet.reading = Reading(current, value(row.get("prior", ""), where, "prior"), row.get("source", ""), row.get("date", ""), where)
    return unmatched
