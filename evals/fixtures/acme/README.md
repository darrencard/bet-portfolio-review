# Demo and test fixture

A second, smaller fixture, separate from the sample in `examples/acme/`. It runs behind `--demo` and the tests. Its bets (Job summary drafting, Overdue reminders, Supplier feed matching and the rest) are not the Landing Loop's canonical Acme bets, and its briefs are its own. Acme is an invented company; every figure, bet, owner and reading here is made up. Owners are roles scoped to a team ("Lead, Payments squad"), not people, and the next step is decided by the Head of Product, Quoting squad.

- `bets.csv`, `work.csv`, `readings.csv`: the CSV format, one bet per gap the review must catch.
- `linear-projects.json`, `linear-issues.json`: the same idea in the shape the Linear connector returns.
- `jira-export.csv`: the same idea as a Jira CSV export (epics are bets).
