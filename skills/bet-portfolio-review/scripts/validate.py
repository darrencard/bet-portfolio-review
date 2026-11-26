#!/usr/bin/env python3
"""Check an edited review against what review.py computed. Exit 1 on any error.

Usage:
  python3 scripts/validate.py run/review.md --computed run/review.json

Rules:
  figure-not-computed  a number appears that the computed review never printed
  status-changed       a bet's line carries a status word other than the computed one, or one it has not earned
  causal-claim         the text says a bet caused, drove or delivered a change in a metric
  bet-dropped          a bet in the computed review is missing from the edited one

The model may rewrite the words. It may not add a number, change a status word, claim cause or drop a bet.

Standard library only. Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
STATUS = re.compile(r"\b(landed|watch|stalled)\b", re.I)
CAUSAL = re.compile(
    r"\b(caused|causing|drove|driven by|thanks to|as a result of|because of (?:this|the) (?:bet|project|work)|delivered (?:a|an|the)?\s*\d)",
    re.I,
)


def owners(lines: list[str], ids: list[str]) -> list[str | None]:
    """The bet each line is about: a line that names one bet as "(ID)", or a line inside that bet's ### section."""
    out: list[str | None] = []
    current = None
    for line in lines:
        named = [i for i in ids if f"({i})" in line]
        if line.startswith("#"):
            current = named[0] if line.startswith("### ") and len(named) == 1 else None
        out.append(named[0] if len(named) == 1 else (None if named else current))
    return out


def check(text: str, computed: dict) -> list[str]:
    errors = []
    allowed = set(computed.get("figures", []))
    per_bet = {b["id"]: set(b.get("figures", [])) for b in computed.get("bets", [])}
    lines = text.splitlines()
    for line_no, (line, owner) in enumerate(zip(lines, owners(lines, list(per_bet))), start=1):
        for n in NUMBER.findall(line):
            if owner is not None and n not in per_bet[owner]:
                errors.append(f"line {line_no}: figure-not-computed: {n} is not one of {owner}'s computed figures.")
            elif n not in allowed:
                errors.append(f"line {line_no}: figure-not-computed: {n} was not in the computed review.")
        if CAUSAL.search(line):
            errors.append(f'line {line_no}: causal-claim: "{CAUSAL.search(line).group(0)}". A metric moving is not proof the bet moved it.')
    for bet in computed.get("bets", []):
        mentions = [(i, x) for i, x in enumerate(lines, start=1) if f"({bet['id']})" in x]
        if not mentions:
            errors.append(f"bet-dropped: {bet['id']} is in the computed review but not in this one.")
        for i, x in mentions:
            words = {w.lower() for w in STATUS.findall(x)}
            # The bet's own status, and the status did-it-land wrote into its loop record, are the only words allowed.
            earned = {bet["status"]} - {None}  # did-it-land's word from the loop record, never computed
            wrong = words - earned
            if wrong:
                want = bet["status"] or "no status word (no result in the loop record)"
                errors.append(f"line {i}: status-changed: {bet['id']} shows {', '.join(sorted(wrong))}; computed: {want}.")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check an edited review against the computed one.")
    ap.add_argument("review", type=Path)
    ap.add_argument("--computed", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        text = args.review.read_text(encoding="utf-8")
        computed = json.loads(args.computed.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise SystemExit(f"validate: cannot read the inputs ({e}).") from None
    errors = check(text, computed)
    for e in errors:
        print(f"validate: {e}")
    print(f"validate: {len(errors)} error(s).", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
