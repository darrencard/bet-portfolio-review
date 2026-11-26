#!/usr/bin/env python3
"""Write the review as Markdown, as one self-contained HTML file, and as JSON for the claim check.

Every number printed here comes from score.py. Every piece of text read from a source is escaped: in Markdown,
pipes, angle brackets and line breaks are neutralised; in HTML, everything goes through html.escape.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

import landing_brief
from score import LABELS, TOTAL, Portfolio, Review, orphan_move

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
ILLUSTRATIVE = "Illustrative: every figure in this review comes from an invented company's sample data."


def md(text: str, limit: int = 300) -> str:
    """Source text made safe for one Markdown table cell or line."""
    text = " ".join(str(text).split())[:limit]
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("`", "'")


def fmt(value: float, prefix: str = "", unit: str = "") -> str:
    return f"{prefix}{value:,.6g}{unit}"


def linked_line(pf: Portfolio) -> str:
    if not pf.work_total:
        return "No work items were given."
    return f"{pf.linked_percent}% of {pf.work_total} work items link to a bet; {pf.judged_percent}% sit under a bet with a definition of good."


def status_text(r: Review) -> str:
    if r.status:
        return r.status
    if r.bet.reading is not None:
        return "no status word: the reading has no source" if r.passed["metric"] else "no status word: no definition of good"
    return "no reading"


def gap_list(r: Review) -> str:
    return "; ".join(LABELS[g] for g in r.gaps) or "None"


def cost_lines(r: Review) -> list[str]:
    p = r.parts
    if not r.passed["cost_budget"]:
        return ["Cost budget: missing."]
    if r.cost_per_task is None:
        return ["Tokens per task: none.", "Price per token: none (the line is fixed code)."]
    price = landing_brief.number(p["price_per_token"])
    assert price is not None  # noqa: S101  (the cost check passed)
    return [
        f"Tokens per task: {md(p['tokens_per_task'])}.",
        f"Price per token: {md(p['price_per_token'])}.",
        f"Cost per task, computed: {fmt(r.cost_per_task, price[0])}.",
    ]


def reading_line(r: Review) -> str:
    reading = r.bet.reading
    if reading is None:
        return "Reading: none recorded."
    if not r.passed["metric"]:
        return f"Reading: {fmt(reading.current)} recorded ({md(reading.where)}), but there is no definition of good to read it against."
    bar = landing_brief.number(r.parts["bar"])
    assert bar is not None  # noqa: S101
    prior = f"; prior {fmt(reading.prior, bar[0], bar[2])}" if reading.prior is not None else "; no prior reading"
    src = f"source: {md(reading.source)}" if reading.source else "no source named"
    when = f" on {md(reading.date)}" if reading.date else ""
    return f"Reading: {md(r.parts['metric'])} is {fmt(reading.current, bar[0], bar[2])}{when}{prior} ({src}; {md(reading.where)})."


def to_markdown(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool) -> str:
    n = len(pf.reviews)
    out = [f"# Bet portfolio review: {md(title)}", ""]
    if illustrative:
        out += [f"> **{ILLUSTRATIVE}**", ""]
    linked = linked_line(pf)
    out += [
        f"As of {pf.as_of}. {n} bets; {pf.complete} have a complete brief. {linked}",
        "",
        "Status words print only where a reading with a named source exists: landed, watch or stalled. A metric moving is not proof that the bet moved it.",
        "",
        "## Do these first",
        "",
        *[f"{r.rank}. **{md(r.bet.name)} ({md(r.bet.id)}):** {md(r.next_step)}" for r in pf.reviews[:3]],
        "",
        "## Ranked review",
        "",
        "Rank 1 needs work first.",
        "",
        "| Rank | Bet | Owner | Brief score | Gaps | Status | Next step |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in pf.reviews:
        out.append(
            f"| {r.rank} | {md(r.bet.name)} ({md(r.bet.id)}) | {md(r.bet.owner) or 'none'} | {r.points} of {TOTAL} ({r.percent}%) "
            f"| {gap_list(r)} | {status_text(r)} | {md(r.next_step)} |"
        )
    out += ["", "## Each bet", ""]
    for r in pf.reviews:
        p = r.parts
        out += [f"### {r.rank}. {md(r.bet.name)} ({md(r.bet.id)})", ""]
        out.append(f"- Source: {md(r.bet.source)}.")
        out.append(f"- Owner: {md(r.bet.owner) or 'none'}. Decides the next step: {md(p.get('decides', '')) or 'none named'}.")
        out.append(f"- Brief score: {r.points} of {TOTAL} points ({r.percent}%).")
        out.append(f"- Gaps: {gap_list(r)}.")
        for kind, note in r.details.items():
            if kind in LABELS:
                out.append(f"  - {LABELS[kind]}: {md(note)}")
        if r.passed["metric"]:
            direction = "higher" if p["better"].lower() == "higher" else "lower"
            out.append(f"- Definition of good: {md(p['metric'])}, bar {md(p['bar'])}, {direction} is better, by {md(p['by'])}.")
        out += [f"- {line}" for line in cost_lines(r)]
        out.append(f"- {reading_line(r)}")
        out.append(f"- Status: {status_text(r)}.")
        out.append(f"- Linked work: {len(r.work)} item{'' if len(r.work) == 1 else 's'}.")
        out.append(f"- **Next step:** {md(r.next_step)}")
        out.append("")
    out += ["## Work linked to no bet", "", orphan_move(pf.orphans), ""]
    if pf.orphans:
        out += ["| Item | Title | Why | Source |", "|---|---|---|---|"]
        out += [f"| {md(o.work.id)} | {md(o.work.title)} | {md(o.why)} | {md(o.work.source)} |" for o in pf.orphans]
        out.append("")
    out += ["## Gaps across the portfolio", "", "| Gap | Bets |", "|---|---|"]
    out += [f"| {LABELS[g]} | {c} |" for g, c in pf.gap_counts.items() if c]
    out += ["", "## Evidence", "", "| Figure | Value | Computed from |", "|---|---|---|"]
    for name, value, src in figures_table(pf, sources):
        out.append(f"| {name} | {value} | {md(src)} |")
    out += ["", "Computed by scripts/review.py. The brief score weights are in scripts/score.py.", ""]
    return "\n".join(out)


def figures_table(pf: Portfolio, sources: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """Each portfolio figure, its value, and the files it was computed from."""
    s = sources or {}
    bets, work, readings = s.get("bets", ""), s.get("work", ""), s.get("readings", "")
    both = ", ".join(x for x in (bets, work) if x)
    status_from = ", ".join(x for x in (bets, readings) if x)
    rows = [
        ("Bets on the roadmap", str(len(pf.reviews)), bets),
        ("Bets with a complete brief", str(pf.complete), both),
        ("Work items", str(pf.work_total), work or "none given"),
        ("Work items linked to no bet", str(len(pf.orphans)), both),
    ]
    if pf.linked_percent is not None:
        rows.append(("Share of work linked to a bet", f"{pf.linked_percent}%", both))
        rows.append(("Share of work under a bet with a definition of good", f"{pf.judged_percent}%", both))
    rows += [(f"Bets {k}", str(c), status_from) for k, c in pf.statuses.items()]
    return rows


CSS = """
:root{--bg:#0f1115;--fg:#e8e6e1;--muted:#9a978f;--line:#2a2d33;--card:#171a20;--red:#ff6b5e;--gold:#c9a45c}
@media (prefers-color-scheme: light){:root{--bg:#fbfaf7;--fg:#1b1c1f;--muted:#5f5c55;--line:#dedad2;--card:#fff;--red:#c0362c;--gold:#8a6a26}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 16px}h1{font-size:26px;margin:0 0 8px}h2{font-size:18px;margin:32px 0 8px}
.muted{color:var(--muted)}.banner{border:1px solid var(--gold);color:var(--gold);padding:8px 12px;border-radius:6px;margin:12px 0}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600}.status{font-weight:700}.stalled{color:var(--red)}.none{color:var(--muted);font-weight:400}
.bet{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}.bet h3{margin:0 0 6px;font-size:16px}
.bet ul{margin:0;padding-left:18px}.next{margin-top:8px}
"""


def h(text: Any) -> str:
    return html.escape(str(text), quote=True)


def status_html(r: Review) -> str:
    if r.status is None:
        return f'<span class="status none">{h(status_text(r))}</span>'
    return f'<span class="status {h(r.status)}">{h(r.status)}</span>'


def to_html(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool) -> str:
    n = len(pf.reviews)
    linked = linked_line(pf)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>Bet portfolio review</title><style>{CSS}</style></head><body><main>",
        f"<h1>Bet portfolio review: {h(title)}</h1>",
    ]
    if illustrative:
        parts.append(f"<div class='banner'>{h(ILLUSTRATIVE)}</div>")
    parts.append(f"<p class='muted'>As of {h(pf.as_of)}. {n} bets; {pf.complete} have a complete brief. {h(linked)}</p>")
    firsts = "".join(f"<li><strong>{h(r.bet.name)}</strong> <span class='muted'>({h(r.bet.id)})</span>: {h(r.next_step)}</li>" for r in pf.reviews[:3])
    parts.append(f"<h2>Do these first</h2><ol>{firsts}</ol>")
    parts.append("<h2>Ranked review</h2><div class='wrap'><table><thead><tr><th>Rank</th><th>Bet</th><th>Owner</th><th>Brief score</th>")
    parts.append("<th>Gaps</th><th>Status</th><th>Next step</th></tr></thead><tbody>")
    for r in pf.reviews:
        parts.append(
            f"<tr><td>{r.rank}</td><td>{h(r.bet.name)} <span class='muted'>({h(r.bet.id)})</span></td><td>{h(r.bet.owner) or 'none'}</td>"
            f"<td>{r.points} of {TOTAL} ({r.percent}%)</td><td>{h(gap_list(r))}</td><td>{status_html(r)}</td><td>{h(r.next_step)}</td></tr>"
        )
    parts.append("</tbody></table></div><h2>Each bet</h2>")
    for r in pf.reviews:
        items = [f"Source: {h(r.bet.source)}", f"Gaps: {h(gap_list(r))}"]
        items += [h(x.rstrip(".")) for x in cost_lines(r)]
        items.append(h(reading_line(r).rstrip(".")))
        lis = "".join(f"<li>{x}</li>" for x in items)
        parts.append(
            f"<section class='bet'><h3>{r.rank}. {h(r.bet.name)} <span class='muted'>({h(r.bet.id)})</span> {status_html(r)}</h3>"
            f"<ul>{lis}</ul><p class='next'><strong>Next step:</strong> {h(r.next_step)}</p></section>"
        )
    parts.append(f"<h2>Work linked to no bet</h2><p>{h(orphan_move(pf.orphans))}</p>")
    if pf.orphans:
        parts.append("<div class='wrap'><table><thead><tr><th>Item</th><th>Title</th><th>Why</th><th>Source</th></tr></thead><tbody>")
        parts += [f"<tr><td>{h(o.work.id)}</td><td>{h(o.work.title)}</td><td>{h(o.why)}</td><td>{h(o.work.source)}</td></tr>" for o in pf.orphans]
        parts.append("</tbody></table></div>")
    parts.append("<h2>Evidence</h2><div class='wrap'><table><thead><tr><th>Figure</th><th>Value</th><th>Computed from</th></tr></thead><tbody>")
    parts += [f"<tr><td>{h(a)}</td><td>{h(b)}</td><td>{h(c)}</td></tr>" for a, b, c in figures_table(pf, sources)]
    parts.append("</tbody></table></div></main></body></html>")
    return "\n".join(parts)


def to_json(pf: Portfolio, markdown: str, sources: dict[str, str], illustrative: bool) -> str:
    import validate  # the same line-to-bet rule the check uses

    lines = markdown.splitlines()
    ids = [r.bet.id for r in pf.reviews]
    per_bet: dict[str, set[str]] = {i: set() for i in ids}
    for line, owner in zip(lines, validate.owners(lines, ids)):
        if owner is not None:
            per_bet[owner].update(NUMBER.findall(line))
    data = {
        "as_of": pf.as_of,
        "illustrative": illustrative,
        "sources": sources,
        "total_points": TOTAL,
        "portfolio": {name: {"value": v, "computed_from": src} for name, v, src in figures_table(pf, sources)},
        "gap_counts": pf.gap_counts,
        "bets": [
            {
                "rank": r.rank,
                "id": r.bet.id,
                "name": r.bet.name,
                "owner": r.bet.owner,
                "source": r.bet.source,
                "points": r.points,
                "percent": r.percent,
                "gaps": r.gaps,
                "status": r.status,
                "cost_per_task": r.cost_per_task,
                "linked_work": [w.id for w in r.work],
                "next_step": r.next_step,
                # Every number printed on this bet's lines. validate.py refuses any other on them.
                "figures": sorted(per_bet[r.bet.id]),
            }
            for r in pf.reviews
        ],
        "orphans": [{"id": o.work.id, "why": o.why, "source": o.work.source} for o in pf.orphans],
        # Every number printed in the Markdown review. validate.py refuses an edited review that prints any other.
        "figures": sorted(set(NUMBER.findall(markdown))),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
