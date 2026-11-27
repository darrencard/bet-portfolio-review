#!/usr/bin/env python3
"""Read a roadmap of bets and the work under them, from Linear, Jira or CSV.

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
Metric readings are not read here: landed, watch or stalled is did-it-land's call, read from the loop record.

Standard library only. Python 3.11 or later.
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


@dataclass
class Work:
    id: str
    title: str
    bet: str
    source: str


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
        for name, cell in zip(names, cells, strict=False):
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
    """A "Landing brief" block built from per-part columns, so one parser reads every format. A column is a part only
    when landing_brief.KEYS knows its name; this file keeps no list of parts of its own."""
    lines = [f"- {col.replace('_', ' ')}: {' '.join(v.split())}" for col, v in row.items() if v and col.replace("_", " ") in landing_brief.KEYS]
    return "## Landing brief\n" + "\n".join(lines) if lines else ""


def brief_file(csv_path: Path, name: str, row: int) -> str:
    """The brief in a Markdown file named by the `brief_file` column, relative to the CSV's folder and inside it."""
    folder = csv_path.resolve().parent
    target = (folder / name).resolve()
    if folder not in target.parents:
        raise LoadError(f"{csv_path.name} row {row}: brief_file {name!r} is outside the CSV's folder. Name a file inside it.")
    if not target.is_file():
        raise LoadError(f"{csv_path.name} row {row}: brief_file {name!r} does not exist. Fix the path or clear the cell.")
    return read_text(target)


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
        source = f"{path.name} row {i}"
        if row.get("brief_file"):
            text, source = brief_file(path, row["brief_file"], i), row["brief_file"]
        else:
            text = row.get("description", "")
        if not has_heading(text):
            text = brief_from_columns(row) or text
        bet = Bet(id=row["id"], name=row["name"] or row["id"], owner=row.get("owner", ""), description=text, source=source)
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


def vendored(call, *args):
    """Call a Leader Report reader; its refusals (SystemExit with a message) become a LoadError."""
    try:
        return call(*args)
    except SystemExit as e:
        raise LoadError(str(e)) from None


CLOSED = ("canceled", "cancelled", "duplicate")


def is_closed(item: dict[str, Any]) -> bool:
    """A canceled project or issue is not on the roadmap. Completed ones stay: they are where landed is read."""
    import from_linear

    status = item.get("status") or item.get("state")
    kind = item.get("statusType") or (status.get("type") if isinstance(status, dict) else None)
    word = from_linear.state_of(item) if "status" in item or "state" in item else ""
    name = status if isinstance(status, str) else (status.get("name") if isinstance(status, dict) else "")
    return any(str(x or "").lower() in CLOSED for x in (kind, word, name))


def linear_bets(paths: list[Path], include_closed: bool = False) -> list[Bet]:
    """Bets from Linear projects: the connector's or API's JSON pages, or Linear's projects CSV export.
    Read with the Leader Report's from_linear.py, so both skills see a project the same way."""
    import from_linear

    projects: list[dict[str, Any]] = []
    where: list[str] = []
    for path in paths:
        found = (
            vendored(from_linear.read_projects_csv, path)
            if path.suffix.lower() == ".csv"
            else vendored(from_linear.read_items, [path], ("projects",), "projects")
        )
        projects += found
        where += [path.name] * len(found)
    bets = []
    for project, src in zip(projects, where, strict=False):
        if not include_closed and is_closed(project):
            continue
        pid = clean(project.get("id") or project.get("slugId") or project.get("name"))
        name = clean(project.get("name")) or pid
        texts = [clean(project.get(k)) for k in ("content", "description") if isinstance(project.get(k), str)]
        text = next((t for t in texts if has_heading(t)), texts[0] if texts else "")
        bet = Bet(id=pid, name=name, owner=clean(from_linear.name_of(project.get("lead"))), description=text, source=f"{src} project {pid}")
        bet.aliases = {a.lower() for a in (pid, name, clean(project.get("slugId"))) if a}
        bets.append(bet)
    if not bets:
        raise LoadError(f"{', '.join(p.name for p in paths)} hold no projects. Save the Linear connector's list_projects result as it stands.")
    check_unique(bets)
    return bets


def linear_work(paths: list[Path], include_closed: bool = False) -> list[Work]:
    """Issues from the connector's or API's JSON pages (overlapping pages are read once), via from_linear.py."""
    import from_linear

    out = []
    for issue in vendored(from_linear.read_issues, paths):
        if not include_closed and is_closed(issue):
            continue
        iid = clean(issue.get("identifier") or issue.get("id"))
        project = issue.get("project")
        ref = clean(project.get("id") or project.get("name")) if isinstance(project, dict) else clean(project or issue.get("projectId"))
        out.append(Work(id=iid, title=clean(issue.get("title")), bet=ref, source=f"Linear issue {iid}"))
    return out


def adf_text(value: Any) -> str:
    """Plain text from a Jira field: a string, or Atlassian Document Format (Jira Cloud's REST v3 description)."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if value.get("type") == "text":
        return str(value.get("text", ""))
    parts = [adf_text(c) for c in value.get("content") or []]
    joiner = "\n" if value.get("type") in ("doc", "bulletList", "orderedList") else ""
    text = joiner.join(parts)
    if value.get("type") == "heading":
        text = "#" * int((value.get("attrs") or {}).get("level", 2)) + " " + text
    if value.get("type") == "listItem":
        text = "- " + text
    return text


def jira_search(paths: list[Path], bet_type: str = "Epic") -> tuple[list[Bet], list[Work]]:
    """Bets and work from Jira REST search pages (the Jira connector or /rest/api/3/search), saved as they stand.
    Issue fields come through the Leader Report's from_jira.py; description and parent, which it does not need,
    are read from the same pages here."""
    import from_jira

    issues = vendored(from_jira.from_search, paths, "customfield_10016")
    extra: dict[str, tuple[str, str, str]] = {}
    for path in paths:
        for raw in (load_json(path) or {}).get("issues") or []:
            f = raw.get("fields") or {}
            parent = f.get("parent") or {}
            ref = clean(parent.get("key") if isinstance(parent, dict) else parent) or clean(f.get("customfield_10014"))
            extra[clean(raw.get("key"))] = (adf_text(f.get("description")), ref, clean(raw.get("id")))
    bets, work = [], []
    for issue in issues:
        key = clean(issue["key"])
        description, parent, iid = extra.get(key, ("", "", ""))
        if issue["issuetype"].lower() == bet_type.lower():
            bet = Bet(id=key, name=clean(issue["summary"]) or key, owner=clean(issue["assignee"]), description=description, source=f"Jira {key}")
            bet.aliases = {a.lower() for a in (key, iid) if a}
            bets.append(bet)
        else:
            work.append(Work(id=key, title=clean(issue["summary"]), bet=parent, source=f"Jira {key}"))
    if not bets:
        raise LoadError(f"the Jira pages hold no issues of type {bet_type}. Pass --jira-bet-type with the type your bets use.")
    check_unique(bets)
    return bets, work


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
