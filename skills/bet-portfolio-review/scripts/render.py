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

import decimal
import html
import json
import re
from pathlib import Path
from typing import Any

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


def linked_line(pf: Portfolio) -> str:
    if not pf.work_total:
        return "No work items were given."
    return f"{pf.linked_percent}% of {pf.work_total} work items link to a bet; {pf.judged_percent}% sit under a bet whose brief parses."


def status_text(r: Review) -> str:
    """The status did-it-land wrote into the loop record, printed as is. Never computed here."""
    return r.status or "no result yet"


def gap_list(r: Review) -> str:
    return "; ".join(LABELS[g] for g in r.gaps) or "None"


def figure_text(f: Any) -> str:
    if not isinstance(f, dict) or "value" not in f:
        return "not given"
    v = f["value"]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        value = str(v)
    else:
        whole, _, frac = format(decimal.Decimal(str(v)), "f").partition(".")
        value = f"{int(whole):,}" + (f".{frac}" if frac.strip("0") else "")
    return f"{value} {f.get('unit', '')}".strip()


def cost_lines(r: Review) -> list[str]:
    """Cost per task is cost-budget-check's figure. Shown from its `cost` key, never computed here."""
    cost = (r.record or {}).get("cost")
    if not isinstance(cost, dict) or not cost:
        return ["Cost: not checked. Run cost-budget-check."]
    tokens, price = cost.get("tokens_per_task"), cost.get("price_per_token")
    src = md(str(tokens.get("source", ""))) if isinstance(tokens, dict) else ""
    tail = f" (source: {src})." if src else "."
    return [f"Cost, from cost-budget-check: tokens per task {md(figure_text(tokens))}; price per token {md(figure_text(price))}{tail}"]


def definition(r: Review) -> str:
    b = r.brief
    assert b is not None  # noqa: S101
    return f"{md(b.metric)}, bar {md(b.bar_text)}, {'higher' if b.higher_is_better else 'lower'} is better, by {md(b.by)}"


def loop_cell(r: Review, loop: dict[str, Progress | None] | None) -> str:
    return progress_text(loop.get(r.bet.id)) if loop is not None else "not read"


def to_markdown(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    n = len(pf.reviews)
    out = [f"# Bet portfolio review: {md(title)}", ""]
    if illustrative:
        out += [f"> **{ILLUSTRATIVE}**", ""]
    out += [
        f"As of {pf.as_of}. {n} bets; {pf.complete} have a brief that parses. {linked_line(pf)}",
        "",
        "Status words (landed, watch, stalled) are did-it-land's, read from each bet's loop record. A metric moving is not proof that the bet moved it.",
        "",
        "## Do these first",
        "",
        *[f"{r.rank}. **{md(r.bet.name)} ({md(r.bet.id)}):** {md(r.next_step)}" for r in pf.reviews[:3]],
        "",
        "## Ranked review",
        "",
        "Rank 1 needs work first. Brief problems are landing_brief.py's own words. Loop shows which Landing Loop steps the bet's record holds.",
        "",
        "| Rank | Bet | Owner | Readiness | Gaps | Result | Loop | Next step |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in pf.reviews:
        out.append(
            f"| {r.rank} | {md(r.bet.name)} ({md(r.bet.id)}) | {md(r.bet.owner) or 'none'} | {r.points} of {TOTAL} ({r.percent}%) "
            f"| {gap_list(r)} | {status_text(r)} | {loop_cell(r, loop)} | {md(r.next_step)} |"
        )
    out += ["", "## Each bet", ""]
    for r in pf.reviews:
        out += [f"### {r.rank}. {md(r.bet.name)} ({md(r.bet.id)})", ""]
        out.append(f"- Source: {md(r.bet.source)}.")
        decides = md(r.brief.decides) if r.brief else "none named"
        out.append(f"- Owner: {md(r.bet.owner) or 'none'}. Decides the next step: {decides}.")
        out.append(f"- Readiness: {r.points} of {TOTAL} points ({r.percent}%).")
        out.append(f"- Gaps: {gap_list(r)}.")
        out += [f"  - landing_brief.py: {md(x)}" for x in r.problems if "no-brief" not in r.gaps]
        if r.brief is not None:
            out.append(f"- Definition of good: {definition(r)}.")
        out += [f"- {line}" for line in cost_lines(r)]
        out.append(f"- Result: {status_text(r)}.")
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
    out += ["", "Computed by scripts/review.py. The readiness weights are in scripts/score.py; brief problems come from landing_brief.py.", ""]
    return "\n".join(out)


def figures_table(pf: Portfolio, sources: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """Each portfolio figure, its value, and the files it was computed from."""
    s = sources or {}
    bets, work, records = s.get("bets", ""), s.get("work", ""), s.get("records", "")
    both = ", ".join(x for x in (bets, work) if x)
    status_from = f"{records} (landed.status, written by did-it-land)" if records else "no loop records read"
    rows = [
        ("Bets on the roadmap", str(len(pf.reviews)), bets),
        ("Bets whose brief parses (landing_brief.py)", str(pf.complete), bets),
        ("Work items", str(pf.work_total), work or "none given"),
        ("Work items linked to no bet", str(len(pf.orphans)), both),
    ]
    if pf.linked_percent is not None:
        rows.append(("Share of work linked to a bet", f"{pf.linked_percent}%", both))
        rows.append(("Share of work under a bet whose brief parses", f"{pf.judged_percent}%", both))
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
    facts = [("Bets", str(n)), ("Brief parses", str(pf.complete)), ("Work linked to no bet", str(len(pf.orphans)))]
    if pf.linked_percent is not None:
        facts += [("Work linked to a bet", f"{pf.linked_percent}%"), ("Work under a definition of good", f"{pf.judged_percent}%")]
    cover = (
        f'<section class="slide first">{BRAND}<div class="meta"><span>Bet portfolio review</span><span>As of {h(pf.as_of)}</span>{ill}</div>'
        f"<h1>{h(title)}</h1>"
        f"<p class=\"lede\">{h(linked_line(pf))} Status words are did-it-land's, read from each bet's loop record. "
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
        '<p class="lede">Rank 1 needs work first. Brief problems are landing_brief.py\'s own words. '
        "Loop shows which Landing Loop steps each bet's record holds.</p>"
        '<div class="tablewrap"><table><thead><tr><th class="num">Rank</th><th>Bet</th><th>Owner</th><th>Readiness</th><th>Gaps</th>'
        f"<th>Result</th><th>Loop</th><th>Next step</th></tr></thead><tbody>{rows}</tbody></table></div>",
    )
    cards = []
    for r in pf.reviews:
        items = [f"Source: {h(r.bet.source)}", f"Gaps: {h(gap_list(r))}"]
        items += [f"landing_brief.py: {h(x)}" for x in r.problems if "no-brief" not in r.gaps]
        if r.brief is not None:
            items.append(f"Definition of good: {h(definition(r))}")
        items += [h(x.rstrip(".")) for x in cost_lines(r)]
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
        + '<p class="asof">Computed by scripts/review.py. The readiness weights are in scripts/score.py; brief problems come from landing_brief.py.</p>',
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
                "brief_problems": r.problems,
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
