#!/usr/bin/env python3
"""Write the review as Markdown, as one self-contained HTML file, and as JSON for the claim check.

The HTML uses the Leader Report's own stylesheet and fonts, read from its vendored template
(assets/leader-report-template.html), and follows its style guide (references/design.md in that skill): mono capital
labels, hairline rows, colour for status only, brass where a person owes something. Markdown is the plain-text twin.

Every number printed here comes from score.py. Every piece of text read from a source is escaped: in Markdown,
pipes, angle brackets and line breaks are neutralised; in HTML, everything goes through html.escape.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import landing_brief
from loop import progress_text
from score import LABELS, TOTAL, Portfolio, Review, orphan_move

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "leader-report-template.html"
Progress = dict[str, Any]

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


def loop_cell(r: Review, loop: dict[str, Progress | None] | None) -> str:
    return progress_text(loop.get(r.bet.id)) if loop is not None else "not read"


def to_markdown(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    n = len(pf.reviews)
    out = [f"# Bet portfolio review: {md(title)}", ""]
    if illustrative:
        out += [f"> **{ILLUSTRATIVE}**", ""]
    out += [
        f"As of {pf.as_of}. {n} bets; {pf.complete} have a complete brief. {linked_line(pf)}",
        "",
        "Status words print only where a reading with a named source exists: landed, watch or stalled. A metric moving is not proof that the bet moved it.",
        "",
        "## Do these first",
        "",
        *[f"{r.rank}. **{md(r.bet.name)} ({md(r.bet.id)}):** {md(r.next_step)}" for r in pf.reviews[:3]],
        "",
        "## Ranked review",
        "",
        "Rank 1 needs work first. Loop shows which Landing Loop steps the bet's record holds.",
        "",
        "| Rank | Bet | Owner | Brief score | Gaps | Status | Loop | Next step |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in pf.reviews:
        out.append(
            f"| {r.rank} | {md(r.bet.name)} ({md(r.bet.id)}) | {md(r.bet.owner) or 'none'} | {r.points} of {TOTAL} ({r.percent}%) "
            f"| {gap_list(r)} | {status_text(r)} | {loop_cell(r, loop)} | {md(r.next_step)} |"
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
            out.append(f"- Definition of good: {definition(r)}.")
        out += [f"- {line}" for line in cost_lines(r)]
        out.append(f"- {reading_line(r)}")
        out.append(f"- Status: {status_text(r)}.")
        out.append(f"- Loop: {loop_cell(r, loop)}.")
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


def definition(r: Review) -> str:
    p = r.parts
    direction = "higher" if p["better"].lower() == "higher" else "lower"
    return f"{md(p['metric'])}, bar {md(p['bar'])}, {direction} is better, by {md(p['by'])}"


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


# Layout for a review page, on top of the Leader Report stylesheet: no rail, sections instead of slides.
PAGE_CSS = """
main{margin-left:0}
.slide{min-height:0;padding:48px 40px 36px}
.slide.first{padding-top:56px}
.slide h1{font-size:clamp(36px,4.6vw,60px)}
.brand{margin-bottom:28px}
.own .li-t{min-width:22px;display:inline-block}
td .sh{width:56px}
.loop{display:flex;flex-wrap:wrap;gap:4px}
.chip.off{color:var(--t3);border-style:dashed}
.nos{font:400 10px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.gp{font-size:12px;color:var(--t2)}
.betcard h3{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.betcard .nm{font:600 18px/1.25 var(--display);color:var(--t1);margin:0 0 12px;letter-spacing:-.02em}
.betcard .nx{margin-top:12px;color:var(--t1);font-size:13.5px}
.betcard .nx b{font:400 10px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3);margin-right:8px}
@media (max-width:980px){.slide{padding:32px 16px 28px}}
"""
BRAND = (
    '<div class="brand"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">'
    '<rect x="2" y="13" width="3" height="7" fill="var(--agent)"/><rect x="7" y="10" width="3" height="10" fill="var(--agent)"/>'
    '<rect x="12" y="2" width="1.5" height="20" fill="var(--brass)"/><rect x="16" y="4" width="4" height="16" fill="var(--t1)"/></svg>'
    '<span translate="no">DACARD</span></div>'
)


def stylesheet() -> str:
    """The Leader Report's style block (fonts and tokens included), from the vendored template."""
    text = TEMPLATE.read_text(encoding="utf-8")
    start, end = text.index("<style>") + len("<style>"), text.index("</style>")
    return text[start:end]


def h(text: Any) -> str:
    return html.escape(str(text), quote=True)


def status_html(r: Review) -> str:
    """The status mark from the style guide: the word always prints beside its colour. No status, no colour."""
    if r.status is None:
        return f'<span class="nos">{h(status_text(r))}</span>'
    return f'<span class="st {h(r.status)}">{h(r.status)}</span>'


def share_bar(percent: int) -> str:
    return f'<span class="sh" aria-hidden="true"><i style="width:{max(0, min(100, percent))}%"></i></span>'


def loop_html(r: Review, loop: dict[str, Progress | None] | None) -> str:
    if loop is None:
        return '<span class="nos">not read</span>'
    p = loop.get(r.bet.id)
    if p is None:
        return '<span class="nos">no record</span>'
    chips = [f'<span class="chip{"" if p[k] else " off"}">{k}</span>' for k in ("spec", "evals", "cost")]
    if p["landed_status"]:
        chips.append(f'<span class="st {h(p["landed_status"])}">{h(p["landed_status"])}</span>')
    else:
        chips.append(f'<span class="chip{"" if p["landed"] else " off"}">result</span>')
    return f'<span class="loop">{"".join(chips)}</span>'


def table(heads: list[str], rows: str, num: tuple[int, ...] = ()) -> str:
    th = "".join(f"<th{' class=num' if i in num else ''}>{h(x)}</th>" for i, x in enumerate(heads))
    return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table></div>'


def section(label: str, title: str, body: str, first: bool = False) -> str:
    return f'<section class="slide{" first" if first else ""}"><div class="meta"><span>{h(label)}</span></div><h2>{h(title)}</h2>{body}</section>'


def to_html(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    n = len(pf.reviews)
    ill = '<span class="ill">Illustrative</span>' if illustrative else ""
    facts = [("Bets", str(n)), ("Complete brief", str(pf.complete)), ("Work linked to no bet", str(len(pf.orphans)))]
    if pf.linked_percent is not None:
        facts += [("Work linked to a bet", f"{pf.linked_percent}%"), ("Work under a definition of good", f"{pf.judged_percent}%")]
    cover = (
        f'<section class="slide first">{BRAND}<div class="meta"><span>Bet portfolio review</span><span>As of {h(pf.as_of)}</span>{ill}</div>'
        f"<h1>{h(title)}</h1>"
        f'<p class="lede">{h(linked_line(pf))} Status words print only where a reading with a named source exists. '
        "A metric moving is not proof that the bet moved it.</p>"
        f'<div class="facts">{"".join(f"<span><b>{h(v)}</b>{h(k)}</span>" for k, v in facts)}</div>'
        + (f'<p class="sub">{h(ILLUSTRATIVE)}</p>' if illustrative else "")
        + "</section>"
    )
    firsts = "".join(
        f'<li class="own"><span><span class="li-t">{r.rank}</span><b>{h(r.bet.name)}</b> <span class="t3">({h(r.bet.id)})</span>. {h(r.next_step)}</span>'
        f'<span class="li-o">{h(r.bet.owner or "none")}</span><span class="nw">{status_html(r)}</span></li>'
        for r in pf.reviews[:3]
    )
    do_first = section("01", "Do these first", f'<div class="card"><ul>{firsts}</ul></div>')
    rows = "".join(
        f'<tr><td class="num">{r.rank}</td><td>{h(r.bet.name)} <span class="t3">({h(r.bet.id)})</span></td>'
        f'<td><span class="mo" style="color:var(--brass)">{h(r.bet.owner) or "none"}</span></td>'
        f'<td class="nw">{share_bar(r.percent)}<span class="mo">{r.points} of {TOTAL}</span></td>'
        f'<td class="gp">{h(gap_list(r))}</td><td>{status_html(r)}</td><td>{loop_html(r, loop)}</td><td>{h(r.next_step)}</td></tr>'
        for r in pf.reviews
    )
    ranked = section(
        "02",
        "Ranked review",
        '<p class="lede">Rank 1 needs work first. Loop shows which Landing Loop steps each bet\'s record holds.</p>'
        '<div class="tablewrap"><table><thead><tr><th class="num">Rank</th><th>Bet</th><th>Owner</th><th>Brief score</th><th>Gaps</th>'
        f"<th>Status</th><th>Loop</th><th>Next step</th></tr></thead><tbody>{rows}</tbody></table></div>",
    )
    cards = []
    for r in pf.reviews:
        items = [f"Source: {h(r.bet.source)}", f"Gaps: {h(gap_list(r))}"]
        if r.passed["metric"]:
            items.append(f"Definition of good: {h(definition(r))}")
        items += [h(x.rstrip(".")) for x in cost_lines(r)]
        items.append(h(reading_line(r).rstrip(".")))
        lis = "".join(f"<li>{x}</li>" for x in items)
        cards.append(
            f'<div class="card betcard"><h3><span>{r.rank} · {h(r.bet.id)}</span>{status_html(r)}</h3><p class="nm">{h(r.bet.name)}</p>'
            f'<ul>{lis}</ul><p class="nx"><b>Next step</b>{h(r.next_step)}</p></div>'
        )
    each = section("03", "Each bet", f'<div class="grid g2">{"".join(cards)}</div>')
    orphan_rows = "".join(
        f"<tr><td>{h(o.work.id)}</td><td>{h(o.work.title)}</td><td>{h(o.why)}</td><td class='mo'>{h(o.work.source)}</td></tr>" for o in pf.orphans
    )
    orphans = section(
        "04",
        "Work linked to no bet",
        f'<p class="lede">{h(orphan_move(pf.orphans))}</p>' + (table(["Item", "Title", "Why", "Source"], orphan_rows) if pf.orphans else ""),
    )
    ev_rows = "".join(f'<tr><td>{h(a)}</td><td class="num">{h(b)}</td><td class="mo">{h(c)}</td></tr>' for a, b, c in figures_table(pf, sources))
    evidence = section(
        "05",
        "Evidence",
        table(["Figure", "Value", "Computed from"], ev_rows, num=(1,))
        + '<p class="asof">Computed by scripts/review.py. The brief score weights are in scripts/score.py.</p>',
    )
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en">',
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>Bet portfolio review: {h(title)}</title>",
            f"<style>{stylesheet()}{PAGE_CSS}</style></head>",
            "<body><main>",
            cover,
            do_first,
            ranked,
            each,
            orphans,
            evidence,
            "</main></body></html>",
        ]
    )


def to_json(pf: Portfolio, markdown: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
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
                "loop": (loop or {}).get(r.bet.id),
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
