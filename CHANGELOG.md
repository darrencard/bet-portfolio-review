# Changelog

## 0.2.0 (2026-11-26)

- Landing Loop: writes the `portfolio` key of `landing/<bet-slug>.json` per bet, keeps every other key as found, and shows each bet's loop progress (spec, evals, cost, result).
- Live data first: Linear projects and issues (connector pages, or Linear's projects CSV) and Jira search pages, read with the Leader Report's `from_linear.py` and `from_jira.py`, vendored at a pinned commit. Canceled Linear items are left out unless `--include-closed`.
- HTML in the Leader Report's style, from its vendored template. Markdown stays the plain-text twin.
- A landed bet with no linked work is told to record it, not to cut it.

## 0.1.0 (2026-11-26)

- First version: brief score, gaps, orphan work, ranked review, one next step per bet, claim check, `--demo`, `--fail-on`.
