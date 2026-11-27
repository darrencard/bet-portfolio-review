#!/usr/bin/env python3
"""Write the review as Markdown, as one self-contained HTML page, and as JSON for the claim check.

The HTML uses the Leader Report's own stylesheet and fonts, read from its vendored template
(assets/leader-report-template.html), and draws its picture with svgkit (scripts/vendor/svgkit.py, vendored
byte-identical from landing-loop), so it sits in the Landing Loop's one visual family. Markdown is the plain-text twin.

The page reads top down for someone who has never seen the loop: the shared header, the verdict as the heading,
the signature picture (each project placed by whether its plan is complete and whether work is linked to it, the
one to do first circled), then one thing to do next with its owner in brass. Every project follows in two columns,
then the work linked to no project. The evidence ledger and everything for engineers (gap codes, the parser's own
words, file names, flags, the record key) sit in folds. Public copy uses plain words: project, target, landing brief
(defined at first use), build plan.

Colour means one thing each: brass for the person who owns the next step, green and red only inside the printed
words landed and stalled. The picture draws only names the page prints, and its aria-label states the answer.

Every number printed here comes from score.py. Every piece of text read from a source is escaped: in Markdown,
pipes, angle brackets and line breaks are neutralised; in HTML, everything goes through html.escape.

Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import decimal
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

from loop import TOOL, progress
from score import LABELS, TOTAL, Portfolio, Review, orphan_move

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

import svgkit as sk  # noqa: E402  (vendored, unchanged; see VENDORED.json)

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "leader-report-template.html"
NAME = "Portfolio review"  # the page prints its plain name; the code name sits in the engineers' fold
CODE_NAME = "bet-portfolio-review"
MIN_FONT_PX = 11  # no text on the page prints smaller, at any width
Progress = dict[str, Any]

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
ILLUSTRATIVE = "Illustrative: every figure in this review comes from an invented company's sample data."
NUMBER_WORDS = ("No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve")

# Gaps that stop a project being judged. A project with none of them is ready.
BLOCKING = ("no-owner", "no-brief", "brief-problems", "no-work", "date-passed")
# Why a project needs work, in the heading's words.
WHY = {
    "no-owner": "it has no owner",
    "no-brief": "it has no landing brief",
    "brief-problems": "its landing brief is incomplete",
    "no-work": "no work is linked to it",
    "date-passed": "its date has passed",
}
# The loop steps a project file can hold, in plain words. The record's keys stay spec, evals, cost and landed.
STEPS = (("spec", "build plan checked"), ("evals", "quality tested"), ("cost", "cost checked"))

# Stored text (the next step, the brief parser's words, the evidence names) in the page's words. The record and
# the JSON keep the original text.
WORDS = (
    (
        r"Write the landing brief: problem, definition of good, non-goals, cost budget, the line\.",
        "Write the landing brief: the problem, what good looks like, what is out of scope, the cost budget, and who does what (a person or the software).",
    ),
    (
        r"Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts\.",
        "Next: check the build plan against this landing brief before build starts.",
    ),
    (r"Run did-it-land on (.+?)(,| once)", r"Read \1 against its target\2"),
    (r"\bFix the brief\b", "Fix the landing brief"),
    (r"^Record it as landed\.", "Mark it landed in the project file."),
    (r"\bnon goals\b", "what is out of scope"),
    (r"\btokens per task\b", "AI usage per task"),
    (r"\bprice per token\b", "AI price per unit"),
    (r"^Bets (landed|watch|stalled)$", r"Projects marked \1"),
    (r"\bthe bet's\b", "the project's"),
    (r"\bthis bet\b", "this project"),
    (r"\bthe bet\b", "the project"),
    (r"\bbets\b", "projects"),
    (r"\bBets\b", "Projects"),
    (r"\bbet\b", "project"),
    (r"\bthe bar\b", "the target"),
    (r"\bBar\b", "Target"),
    (r"\bbar\b", "target"),
    (r"brief parses \(landing_brief\.py\)", "landing brief is complete"),
    (r"brief parses", "landing brief is complete"),
)


def plain(text: str) -> str:
    """Stored text in the page's words: project, target, build plan."""
    for pattern, to in WORDS:
        text = re.sub(pattern, to, text)
    return text


def split_who(step: str, r: Review) -> tuple[str, str, str]:
    """The next step without its role label, the label (Owner or Decides) and the person it names."""
    m = re.search(r"(Owner|Decider): ([^.]+)\.\s*", step)
    if not m:
        return step, "Owner", r.bet.owner or "none named"
    rest = (step[: m.start()] + step[m.end() :]).strip()
    return rest, "Owner" if m.group(1) == "Owner" else "Decides", m.group(2)


def when(r: Review) -> str:
    """When the next step is due: now for a passed date, before build for a gap that blocks it, else the brief's date."""
    if "date-passed" in r.gaps:
        return "now"
    if set(r.gaps) & set(BLOCKING) or r.brief is None:
        return "before build starts"
    return f"by {r.brief.by}"


def md(text: str, limit: int = 300) -> str:
    """Source text made safe for one Markdown table cell or line."""
    text = " ".join(str(text).split())[:limit]
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("`", "'")


def count_word(n: int) -> str:
    return NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)


def plural(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"


def and_join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def ready(r: Review) -> bool:
    return not set(r.gaps) & set(BLOCKING)


def first_why(r: Review) -> str | None:
    return next((WHY[g] for g in r.gaps if g in WHY), None)


def verdict(pf: Portfolio) -> str:
    """The heading: how many projects are ready, any that stalled, and which to start with and why."""
    n = len(pf.reviews)
    if not n:
        return "No projects to review."
    k = sum(1 for r in pf.reviews if ready(r))
    if k == n:
        parts = [f"All {count_word(n).lower()} projects are ready."]
    else:
        parts = [f"{count_word(k)} of {count_word(n).lower()} projects {'is' if k == 1 else 'are'} ready."]
    stalled = [r.bet.name for r in pf.reviews if r.status == "stalled"]
    if stalled:
        parts.append(f"{and_join(stalled)} stalled.")
    why = first_why(pf.reviews[0])
    if why:
        parts.append(f"Start with {pf.reviews[0].bet.name}: {why}.")
    return " ".join(parts)


def linked_line(pf: Portfolio) -> str:
    if not pf.work_total:
        return "No work items were given."
    return f"{pf.linked_percent}% of {pf.work_total} work items link to a project; {pf.judged_percent}% sit under a project whose landing brief is complete."


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
    unit = str(f.get("unit", ""))
    return f"{value} {'' if unit in ('token', 'tokens') else unit}".strip()  # AI usage reads as a count, not in tokens


def cost_text(r: Review) -> str:
    """Cost is cost-budget-check's figure. Shown from its `cost` key, never computed here."""
    cost = (r.record or {}).get("cost")
    if not isinstance(cost, dict) or not cost:
        return "not checked yet (cost-budget-check)"
    tokens, price = cost.get("tokens_per_task"), cost.get("price_per_token")
    src = str(tokens.get("source", "")) if isinstance(tokens, dict) else ""
    tail = f" (source: {src})" if src else ""
    return f"AI usage per task {figure_text(tokens)}; AI price per unit {figure_text(price)}, from cost-budget-check{tail}"


def target(r: Review) -> str:
    """The definition of good in plain words: the metric, the target, which way, by when."""
    b = r.brief
    if b is None:
        return "No landing brief yet" if "no-brief" in r.gaps else "Landing brief incomplete"
    return f"{b.metric}: {b.bar_text} or {'higher' if b.higher_is_better else 'lower'} by {b.by}"


def steps_text(p: Progress | None) -> str:
    """Which loop steps the project's file holds, in plain words. No record yet reads the same as an empty one."""
    p = p or progress({})
    parts = [f"{word} {'yes' if p[k] else 'no'}" for k, word in STEPS]
    parts.append(f"result {p['landed_status']}" if p["landed_status"] else f"result {'yes' if p['landed'] else 'no'}")
    return ", ".join(parts)


def loop_cell(r: Review, loop: dict[str, Progress | None] | None) -> str:
    return steps_text(loop.get(r.bet.id)) if loop is not None else "not read"


def to_markdown(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    n = len(pf.reviews)
    out = [f"# Portfolio review: {md(title)}", ""]
    if illustrative:
        out += [f"> **{ILLUSTRATIVE}**", ""]
    out += [
        f"**{md(verdict(pf))}**",
        "",
        f"As of {pf.as_of}. A project is a piece of work you expect to move a number. Each one is checked against its landing brief, "
        "a one-page plan: what good looks like, by when, at what cost. Ready means one owner, a complete landing brief and work linked to it.",
        "",
        f"{n} projects; {pf.complete} have a complete landing brief. {linked_line(pf)}",
        "",
        "Status words (landed, watch, stalled) come from did-it-land, read from each project's file. A number moving is not proof that the project moved it.",
        "",
    ]
    if pf.reviews:
        r = pf.reviews[0]
        step, role, who = split_who(plain(r.next_step), r)
        out += ["## What to do next", "", f"**{md(r.bet.name)} ({md(r.bet.id)}):** {md(step)} {role}: {md(who)}. When: {when(r)}.", ""]
    out += ["## Where each project stands", "", "| Project | Complete landing brief | Work linked | Owner |", "|---|---|---|---|"]
    out += [
        f"| {md(r.bet.name)} ({md(r.bet.id)}) | {'yes' if r.passed['brief'] else 'no'} | {'yes' if r.passed['linked_work'] else 'no'} | {md(r.bet.owner) or 'none'} |"
        for r in pf.reviews
    ]
    out += [
        "",
        "## Every project, in order",
        "",
        "Rank 1 needs work first. Steps done shows which Landing Loop steps the project's file holds.",
        "",
        "| Rank | Project | Owner | Readiness | Missing | Result | Steps done | Next step |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in pf.reviews:
        out.append(
            f"| {r.rank} | {md(r.bet.name)} ({md(r.bet.id)}) | {md(r.bet.owner) or 'none'} | {r.points} of {TOTAL} ({r.percent}%) "
            f"| {gap_list(r)} | {status_text(r)} | {loop_cell(r, loop)} | {md(plain(r.next_step))} |"
        )
    out += ["", "## Each project", ""]
    for r in pf.reviews:
        out += [f"### {r.rank}. {md(r.bet.name)} ({md(r.bet.id)})", ""]
        out.append(f"- Target: {md(target(r))}.")
        decides = md(r.brief.decides) if r.brief else "none named"
        out.append(f"- Owner: {md(r.bet.owner) or 'none'}. Decides the next step: {decides}.")
        out.append(f"- Missing: {gap_list(r)}.")
        out += [f"  - The landing brief check says: {md(plain(x))}" for x in r.problems if "no-brief" not in r.gaps]
        out.append(f"- Work linked: {plural(len(r.work), 'item')}.")
        out.append(f"- Cost: {md(cost_text(r))}.")
        out.append(f"- Result: {status_text(r)}.")
        out.append(f"- Steps done: {loop_cell(r, loop)}.")
        out.append(f"- Readiness: {r.points} of {TOTAL} points ({r.percent}%).")
        out.append(f"- **Next step:** {md(plain(r.next_step))}")
        out.append("")
    out += ["## Work linked to no project", "", plain(orphan_move(pf.orphans)), ""]
    if pf.orphans:
        out += ["| Item | Title | Why | Source |", "|---|---|---|---|"]
        out += [f"| {md(o.work.id)} | {md(o.work.title)} | {md(plain(o.why))} | {md(o.work.source)} |" for o in pf.orphans]
        out.append("")
    out += ["## What is missing, across projects", "", "| Missing | Projects |", "|---|---|"]
    out += [f"| {LABELS[g]} | {c} |" for g, c in pf.gap_counts.items() if c]
    out += ["", "## Evidence", "", "| Figure | Value | Computed from |", "|---|---|---|"]
    for name, value, src in figures_table(pf, sources):
        out.append(f"| {plain(name)} | {value} | {plain_source(src, sources)} |")
    out += ["", "## For your engineers", "", f"Skill: {CODE_NAME} {TOOL.rsplit(' ', 1)[-1]}. Files read: {md(files_read(sources))}.", ""]
    out += [f"- {md(r.bet.name)} ({md(r.bet.id)}): {md(r.bet.source)}." for r in pf.reviews]
    out += ["", "Computed by scripts/review.py. The readiness weights are in scripts/score.py; the landing brief check is landing_brief.py.", ""]
    return "\n".join(out)


def plain_source(src: str, sources: dict[str, str] | None) -> str:
    """Where a figure came from, in plain words. The file names sit in the engineers' fold and the JSON."""
    s = sources or {}
    bets, work, records = s.get("bets", ""), s.get("work", ""), s.get("records", "")
    words = {
        bets: "the roadmap",
        work: "the work list",
        ", ".join(x for x in (bets, work) if x): "the roadmap and the work list",
        f"{records} (landed.status, written by did-it-land)": "each project's file, as did-it-land wrote it",
        "no loop records read": "no project files read",
        "none given": "none given",
        "": "not named",
    }
    return words.get(src, "the files read")


def files_read(sources: dict[str, str] | None) -> str:
    """The files behind the review, by name, for the engineers' fold."""
    s = sources or {}
    named = [(s.get("bets", ""), "the roadmap"), (s.get("work", ""), "the work list"), (s.get("records", ""), "the project files")]
    return ", ".join(f"{v} ({k})" for v, k in named if v) or "none named"


def floor_fonts(css: str) -> str:
    """Every font size in the page's CSS at MIN_FONT_PX or more. The vendored template and svgkit stay byte-identical;
    their smaller label sizes are raised here, as the page is written. A line height (after the slash) is left alone."""

    def raise_px(decl: re.Match[str]) -> str:
        return re.sub(r"(?<![/\d.])(\d+(?:\.\d+)?)px", lambda m: f"{MIN_FONT_PX}px" if float(m.group(1)) < MIN_FONT_PX else m.group(0), decl.group(0))

    return re.sub(r"font(?:-size)?:[^;}]*", raise_px, css)


def figures_table(pf: Portfolio, sources: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """Each portfolio figure, its value, and the files it was computed from. The names are the JSON's keys."""
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


# Layout for this page only, on top of the Leader Report stylesheet and svgkit.CSS, as did-it-land's page does.
# The template's green selection and focus ring are set to ink: green is did-it-land's landed only.
PAGE_CSS = """
main.solo{margin-left:0}
.solo .slide{min-height:0}
.solo .slide.cover{min-height:0;padding-top:40px;padding-bottom:48px;justify-content:flex-start}
.solo h1{font-size:clamp(34px,4.6vw,60px);line-height:1;letter-spacing:-.04em;max-width:22ch;margin-bottom:20px}
.solo .lede{margin-bottom:28px}
.solo .lede b{color:var(--t1);font-weight:500}
.cols{display:grid;grid-template-columns:minmax(0,640px) minmax(260px,1fr);gap:28px 48px;align-items:start}
.side{display:grid;gap:24px}
.next{display:grid;gap:10px;border:1px solid var(--brass);border-radius:12px;padding:20px 22px;background:var(--brass-bg)}
.next>b{font:400 11px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--brass)}
.next p{margin:0;font-size:16px;line-height:1.5;color:var(--t1)}
.next p span{color:var(--t2)}
.who{display:flex;flex-wrap:wrap;gap:4px 24px;font:400 11.5px/18px var(--mono);color:var(--brass)}
.who i{font-style:normal;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);margin-right:8px}
.who .d{color:var(--t2)}
.figs{margin:0;display:grid}
.figs>div{display:grid;grid-template-columns:120px minmax(0,1fr);gap:4px 16px;border-top:1px solid var(--line);padding:10px 0}
.figs dt{font:400 11px/22px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.figs dd{margin:0;font-size:13.5px;line-height:1.55;color:var(--t2)}
.figs dd b{color:var(--t1);font-weight:500}
.figs .own dt{color:var(--brass)}
.figs .own .o{display:block;margin-top:4px;font:400 11.5px/18px var(--mono);color:var(--brass)}
.projects{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--s1)}
.project{padding:20px 24px 14px;box-shadow:-1px 0 0 var(--line),0 -1px 0 var(--line)}
.project h3{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:0 0 10px;font:600 18px/1.25 var(--display);letter-spacing:-.02em;color:var(--t1)}
.project h3 .rk{font:400 11px/16px var(--mono);letter-spacing:.1em;color:var(--t3);margin-right:10px}
.project .figs>div:first-child{border-top:0}
.nos{white-space:nowrap;font:400 11px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip.off{color:var(--t3);border-style:dashed}
.solo details{margin-top:20px}
.solo details .tablewrap{margin-top:12px}
.note{max-width:80ch;font-size:12.5px;line-height:1.6;color:var(--t2);margin:12px 0 0}
.eng td{font-size:12px;vertical-align:top}
.eng .chip{margin:0 4px 4px 0}
td.src{white-space:normal;min-width:96px}
::selection{background:var(--t1);color:var(--bg)}
:focus-visible{outline-color:var(--t1)}
.foot{max-width:1120px;margin:0 auto;padding:28px 40px 64px;color:var(--t3);font-size:12px}
@media (max-width:1100px){.cols{grid-template-columns:minmax(0,1fr)}}
@media (max-width:980px){.foot{padding:24px 16px 48px}.solo .slide.cover{padding-top:24px}.projects{grid-template-columns:minmax(0,1fr)}}
@media (max-width:560px){.figs>div{grid-template-columns:1fr;gap:0}.project{padding:16px 16px 12px}}
"""


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


def steps_html(r: Review, loop: dict[str, Progress | None] | None) -> str:
    if loop is None:
        return '<span class="nos">not read</span>'
    p = loop.get(r.bet.id) or progress({})  # no record yet reads the same as an empty one, so a rerun prints the same page
    chips = [f'<span class="chip{"" if p[k] else " off"}">{word}</span>' for k, word in STEPS]
    if p["landed_status"]:
        chips.append(f'<span class="st {h(p["landed_status"])}">{h(p["landed_status"])}</span>')
    else:
        chips.append(f'<span class="chip{"" if p["landed"] else " off"}">result</span>')
    return f'<span class="chips">{"".join(chips)}</span>'


# The signature picture: plan complete? across, work linked? down, one dot per project, the first circled.


def _wrap(text: str, chars: int) -> list[str]:
    lines: list[str] = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= chars:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines or [""]


def _ring(x: float, y: float, r: float) -> str:
    return f'<circle cx="{sk.num(x)}" cy="{sk.num(y)}" r="{sk.num(r)}" fill="none" stroke="{sk.INK}" stroke-width="{sk.num(sk.STROKE)}"/>'


def _upright(x: float, y: float, text: str) -> str:
    """A row label turned to read upwards, centred on (x, y)."""
    return f'<g transform="translate({sk.num(x)} {sk.num(y)}) rotate(-90)">{sk.label(0, 0, text, anchor="middle")}</g>'


def _cells(pf: Portfolio) -> dict[tuple[bool, bool], list[Review]]:
    """Projects by (plan complete, work linked), each list in rank order."""
    cells: dict[tuple[bool, bool], list[Review]] = {(p, w): [] for w in (True, False) for p in (False, True)}
    for r in pf.reviews:
        cells[(r.passed["brief"], r.passed["linked_work"])].append(r)
    return cells


def grid(pf: Portfolio, variant: str) -> str:
    """The signature picture. 640 wide beside the next step on desktop, 340 wide on phones, where names wrap."""
    wide = variant == "wide"
    width = 640.0 if wide else float(sk.TALL)
    gut, top = 24.0, 30.0
    col = (width - gut) / 2
    chars = 99 if wide else int((col - 40) / sk.label_width("x"))
    first = pf.reviews[0]
    cells = _cells(pf)

    def item_height(r: Review) -> float:
        lines = len(_wrap(r.bet.name.upper(), chars))
        return lines * 15 + (24 if r is first and not wide else 0) + 11

    def cell_height(rs: list[Review]) -> float:
        return 30 + (sum(item_height(r) for r in rs) if rs else 20)

    rows = {w: max(64.0, cell_height(cells[(False, w)]), cell_height(cells[(True, w)])) for w in (True, False)}
    height = top + rows[True] + rows[False] + 2
    y0 = {True: top, False: top + rows[True]}
    bottom = height - 1
    parts = [sk.zone(gut + col, top, col, rows[True])]  # plan and work both in place: shaded neutral, never green
    parts += [sk.rule(gut, y, width, y) for y in (top, top + rows[True], bottom)]
    parts += [sk.rule(x, top, x, bottom) for x in (gut, gut + col, width)]
    parts.append(sk.label(gut + 14, 18, "Plan incomplete"))
    parts.append(sk.label(gut + col + 14, 18, "Plan complete", tone=sk.INK2))
    parts.append(_upright(10, top + rows[True] / 2, "Work linked"))
    parts.append(_upright(10, top + rows[True] + rows[False] / 2, "No work"))
    for (p, w), rs in cells.items():
        x = gut + (col if p else 0) + 14
        y = y0[w] + 28
        if not rs:
            parts.append(sk.label(x, y, "None", tone=sk.LINE3))
            continue
        for r in rs:
            lines = _wrap(r.bet.name.upper(), chars)
            cy = y - 4
            parts.append(sk.point(x + 5, cy, r=5) if r.bet.owner else sk.hollow(x + 5, cy, r=4.5))
            parts += [sk.label(x + 22, y + i * 15, line, tone=sk.INK) for i, line in enumerate(lines)]
            if r is first:
                parts.append(_ring(x + 5, cy, 10))
                last = y + (len(lines) - 1) * 15
                if wide:
                    parts.append(sk.chip(x + 34 + sk.label_width(lines[-1]), last - 13, "Do first", tone=sk.INK))
                else:
                    parts.append(sk.chip(x + 22, last + 6, "Do first", tone=sk.INK))
            y += item_height(r)
    return sk.frame("".join(parts), label=grid_label(pf, cells), height=height, width=width, variant=variant)


def grid_label(pf: Portfolio, cells: dict[tuple[bool, bool], list[Review]]) -> str:
    """The picture's answer in one sentence."""
    first = pf.reviews[0]
    why = first_why(first)
    lead = f"{first.bet.name} is circled to do first" + (f" because {why}" if why else "")
    both = len(cells[(True, True)])
    return f"{lead}; {count_word(both).lower()} of {count_word(len(pf.reviews)).lower()} projects have both a complete plan and linked work."


GRID_CAPTION = (
    "Each dot is one project, placed by whether its landing brief is complete and whether any work is linked to it. "
    "The shaded corner has both. A hollow dot has no owner. The ring marks the project to do first."
)


def next_box(r: Review) -> str:
    step, role, who = split_who(plain(r.next_step), r)
    return (
        f'<div class="next"><b>What to do next</b><p>{h(r.bet.name)}. <span>{h(step)}</span></p>'
        f'<span class="who"><span class="o"><i>{h(role)}</i>{h(who)}</span><span class="d"><i>When</i>{h(when(r))}</span></span></div>'
    )


def glance(pf: Portfolio) -> str:
    n = len(pf.reviews)
    rows = [("Projects", f"<b>{n}</b> on the roadmap"), ("Complete plan", f"<b>{pf.complete}</b> of {n} have a complete landing brief")]
    if pf.linked_percent is not None:
        rows.append(("Work linked", f"<b>{pf.linked_percent}%</b> of {pf.work_total} work items link to a project"))
        rows.append(("Can be judged", f"<b>{pf.judged_percent}%</b> of work sits under a complete landing brief"))
    rows.append(("Unlinked work", f"<b>{len(pf.orphans)}</b> {'item links' if len(pf.orphans) == 1 else 'items link'} to no project"))
    return '<dl class="figs">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>"


def project_card(r: Review, loop: dict[str, Progress | None] | None) -> str:
    step, role, who = split_who(plain(r.next_step), r)
    decides = h(r.brief.decides) if r.brief else "none named"
    rows = [
        ("Target", h(target(r))),
        ("Owner", f"{h(r.bet.owner) or 'none named'}. Decides: {decides}"),
        ("Missing", h("; ".join(LABELS[g] for g in r.gaps if g != "no-result") or "Nothing")),
        ("Work linked", h(plural(len(r.work), "item"))),
        ("Cost", h(cost_text(r)[0].upper() + cost_text(r)[1:])),
        ("Steps done", steps_html(r, loop)),
    ]
    body = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
    own = f'<div class="own"><dt>Next step</dt><dd>{h(step)}<span class="o">{h(role)}: {h(who)}, {h(when(r))}</span></dd></div>'
    return f'<article class="project"><h3><span><span class="rk">{r.rank:02d}</span>{h(r.bet.name)}</span>{status_html(r)}</h3><dl class="figs">{body}{own}</dl></article>'


def table(heads: list[str], rows: str, num: tuple[int, ...] = (), cls: str = "") -> str:
    th = "".join(f"<th{' class=num' if i in num else ''}>{h(x)}</th>" for i, x in enumerate(heads))
    return f'<div class="tablewrap{" " + cls if cls else ""}"><table><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table></div>'


def section(label: str, title: str, body: str) -> str:
    return f'<section class="slide"><div class="meta"><span>{h(label)}</span></div><h2>{h(title)}</h2>{body}</section>'


def engineers(pf: Portfolio, sources: dict[str, str] | None = None) -> str:
    """Gap codes, the parser's own words, files, flags and the record key: none of it is needed to act on the review."""
    rows = []
    for r in pf.reviews:
        codes = "".join(f'<span class="chip">{h(g)}</span>' for g in r.gaps) or "none"
        said = "<br>".join(h(x) for x in r.problems) or "none"
        rows.append(
            f'<tr><td class="num">{r.rank}</td><td class="mo">{h(r.bet.id)}</td><td>{h(r.bet.name)}</td><td class="num">{r.points} of {TOTAL}</td>'
            f'<td>{codes}</td><td>{said}</td><td class="mo src">{h(r.bet.source)}</td></tr>'
        )
    note = (
        f'<p class="note">Skill: <code>{CODE_NAME}</code> {h(TOOL.rsplit(" ", 1)[-1])}. Files read: {h(files_read(sources))}. '
        "Every figure is computed by scripts/review.py from those files.</p>"
        '<p class="note">With <code>--landing</code>, the review adds its page to each project file: the <code>portfolio</code> key of '
        "<code>landing/&lt;slug&gt;.json</code>, and no other key. <code>--fail-on no-owner,no-brief</code> exits 2 for CI when any project has "
        f"one of those gaps. Readiness is scored in scripts/score.py: owner 3, landing brief 10, linked work 1, out of {TOTAL}. Whether a brief is "
        "complete is landing_brief.py's call, shown above in its own words. Status words are read from <code>landed.status</code>, never computed.</p>"
    )
    head = ["Rank", "Id", "Project", "Readiness", "Gap codes", "landing_brief.py says", "Source"]
    return f"<details><summary>For your engineers</summary>{table(head, ''.join(rows), num=(0, 3), cls='eng')}{note}</details>"


def to_html(pf: Portfolio, title: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    version = "v" + TOOL.rsplit(" ", 1)[-1]
    header = sk.page_header(NAME, date=f"Review {pf.as_of}", version=version, illustrative=illustrative)
    lede = (
        "A project is a piece of work you expect to move a number. Each one is checked against its <b>landing brief</b>, a one-page plan: "
        "what good looks like, by when, at what cost. Ready means one owner, a complete landing brief and work linked to it."
    )
    pic = sk.figure(grid(pf, "wide"), grid(pf, "tall"), caption=GRID_CAPTION, illustrative=illustrative) if pf.reviews else ""
    side = (next_box(pf.reviews[0]) if pf.reviews else "") + glance(pf)
    cover = (
        f'<section class="slide cover">{header}<h1>{h(verdict(pf))}</h1><p class="lede">{lede}</p>'
        f'<div class="cols"><div>{pic}</div><div class="side">{side}</div></div></section>'
    )
    every = section(
        "Projects",
        "Every project, in order",
        '<p class="lede">The first needs work first. Status words come from did-it-land; this review prints them and never computes one.</p>'
        f'<div class="projects">{"".join(project_card(r, loop) for r in pf.reviews)}</div>',
    )
    orphan_rows = "".join(f'<tr><td class="mo">{h(o.work.id)}</td><td>{h(o.work.title)}</td><td>{h(plain(o.why))}</td></tr>' for o in pf.orphans)
    gaps = "".join(f"<div><dt>{h(LABELS[g])}</dt><dd><b>{c}</b> {'project' if c == 1 else 'projects'}</dd></div>" for g, c in pf.gap_counts.items() if c)
    orphans = section(
        "Work",
        "Work linked to no project",
        f'<p class="lede">{h(plain(orphan_move(pf.orphans)))}</p>'
        f'<div class="cols"><div>{table(["Item", "Title", "Why"], orphan_rows) if pf.orphans else ""}</div>'
        f'<div><dl class="figs">{gaps}</dl></div></div>',
    )
    figures = figures_table(pf, sources)
    ev_rows = "".join(f'<tr><td>{h(plain(a))}</td><td class="num">{h(b)}</td><td>{h(plain_source(c, sources))}</td></tr>' for a, b, c in figures)
    detail = (
        '<section class="slide"><div class="meta"><span>Detail</span></div>'
        f"<details><summary>Evidence ledger ({plural(len(figures), 'figure')})</summary>"
        f"{table(['Figure', 'Value', 'Computed from'], ev_rows, num=(1,))}</details>"
        f"{engineers(pf, sources)}</section>"
    )
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Portfolio review: {h(title)}</title><style>{floor_fonts(stylesheet() + sk.CSS + PAGE_CSS)}</style></head><body><main class="solo">'
        f"{cover}{every}{orphans}{detail}"
        '<p class="foot">A number moving is not proof that the project moved it. This review says whether each project is set up to be judged, '
        "not whether it worked. Every figure is computed in code from the files named.</p></main></body></html>\n"
    )


def to_json(pf: Portfolio, markdown: str, sources: dict[str, str], illustrative: bool, loop: dict[str, Progress | None] | None = None) -> str:
    import validate  # the same line-to-bet rule the check uses

    lines = markdown.splitlines()
    ids = [r.bet.id for r in pf.reviews]
    per_bet: dict[str, set[str]] = {i: set() for i in ids}
    for line, owner in zip(lines, validate.owners(lines, ids), strict=False):
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
