#!/usr/bin/env python3
"""Read and write the Landing Loop record: one JSON file per bet, landing/<bet-slug>.json.

The contract (darrencard/landing-loop CONTRACT.md, schema "landing-loop/1"):
  - each skill writes only its own key; this one writes `portfolio` and keeps every other key exactly as found
  - every figure carries value, unit, source, window (from, to) and as_of
  - status words are landed, watch or stalled only; `landed.status` belongs to did-it-land, never to this skill

This skill also starts a record that does not exist yet: it sets `schema`, `bet` and `brief` (the brief's source and
the SHA-256 of its text). When a record already has a brief whose hash differs, the record keeps its brief and the
portfolio key says the brief changed.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from load import Bet, LoadError
from score import STATUS_WORDS, TOTAL, Portfolio, Review

SCHEMA = "landing-loop/1"
TOOL = "bet-portfolio-review 0.3.1"
STEPS = ("spec", "evals", "cost", "landed")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80] or "bet"


def slugs(bets: list[Bet]) -> dict[str, str]:
    """One file name per bet. A name two bets share gets the bet id added."""
    names = [slug(b.name) for b in bets]
    return {b.id: name if names.count(name) == 1 else f"{name}-{slug(b.id)}" for b, name in zip(bets, names)}


def read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise LoadError(f"cannot read the loop record {path} ({e}). Fix or move it; nothing was written.") from None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise LoadError(f'{path} is not a "{SCHEMA}" loop record. Move it; this skill will not overwrite it.')
    return data


def progress(record: dict[str, Any] | None) -> dict[str, Any]:
    """Which loop steps the record holds. For `landed`, its status word when it is one of the three."""
    record = record or {}
    out: dict[str, Any] = {k: isinstance(record.get(k), dict) and bool(record.get(k)) for k in STEPS}
    landed = record.get("landed")
    word = landed.get("status") if isinstance(landed, dict) else None
    out["landed_status"] = word if word in STATUS_WORDS else None  # printed, never computed
    return out


def progress_text(p: dict[str, Any] | None) -> str:
    # No record yet reads the same as an empty one, so running the review twice prints the same thing.
    p = p or progress({})
    # The landed step is called "result" here, so the word landed only ever prints as a status.
    parts = [f"{k} {'yes' if p[k] else 'no'}" for k in ("spec", "evals", "cost")]
    parts.append(f"result {p['landed_status']}" if p["landed_status"] else f"result {'yes' if p['landed'] else 'no'}")
    return ", ".join(parts)


def figure(value: float | int, unit: str, source: str, as_of: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "source": source, "window": {"from": as_of, "to": as_of}, "as_of": as_of}


def portfolio_key(r: Review, pf: Portfolio, sources: dict[str, str], note: str = "") -> dict[str, Any]:
    work_src = sources.get("work") or "no work file"
    key: dict[str, Any] = {
        "tool": TOOL,
        "as_of": pf.as_of,
        "rank": figure(r.rank, f"rank of {len(pf.reviews)} bets, 1 needs work first", sources.get("bets", ""), pf.as_of),
        "brief_score": figure(r.points, f"points of {TOTAL}", r.bet.source, pf.as_of),
        "brief_score_percent": figure(r.percent, "%", r.bet.source, pf.as_of),
        "linked_work": figure(len(r.work), "work items", work_src, pf.as_of),
        "owner": r.bet.owner,
        "decides": r.brief.decides if r.brief else "",
        "gaps": r.gaps,
        # landing_brief.parse's own words, so they match spec-auditor's brief findings exactly.
        "brief_problems": r.problems,
        "next_step": r.next_step,
    }
    if note:
        key["note"] = note
    return key


def collect(folder: Path, bets: list[Bet]) -> dict[str, dict[str, Any] | None]:
    """The records that already exist, by bet id. Read before anything is written."""
    names = slugs(bets)
    return {b.id: read(folder / f"{names[b.id]}.json") for b in bets}


def write(folder: Path, pf: Portfolio, sources: dict[str, str], existing: dict[str, dict[str, Any] | None]) -> list[Path]:
    """Write the portfolio key into each bet's record. Every other key stays exactly as it was."""
    folder.mkdir(parents=True, exist_ok=True)
    names = slugs([r.bet for r in pf.reviews])
    written = []
    for r in pf.reviews:
        path = folder / f"{names[r.bet.id]}.json"
        record = existing.get(r.bet.id) or {"schema": SCHEMA, "bet": names[r.bet.id]}
        digest = hashlib.sha256(r.bet.description.encode("utf-8")).hexdigest()
        note = ""
        if not isinstance(record.get("brief"), dict):
            record["brief"] = {"path": r.bet.source, "sha256": digest}
        elif record["brief"].get("sha256") != digest:
            note = "The brief has changed since this record was started; the record keeps the original brief hash."
        record["portfolio"] = portfolio_key(r, pf, sources, note)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written
