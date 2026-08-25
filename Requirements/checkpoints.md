# Checkpoints — Expense Sorter

Mid-week demos. Each row is something you can show working by the named day.
The Friday demo (see [README](README.md)) shows checkpoints 1–4 live;
checkpoint 5 is shown as the chart PNG and the `llm-comparison.md` numbers.

| Day | What you can show | How you show it |
|-----|-------------------|-----------------|
| 1   | CLI works on a real CSV | `ledger import`; `ledger categorise`; `ledger budget` |
| 2   | MCP exposes your data; local agent uses it | opencode session: `categoriser` queries via `budget://status` |
| 3   | Custom tools run; injection is neutralised | import the seeded poisoned CSV; verify the merchant is recorded, not the category |
| 4   | Monthly report writes markdown + chart | `ledger report 2026-08` writes `reports/2026-08.md` and `reports/2026-08.png` |
| 5   | Local-only verified | network capture shows zero outbound to model providers during the run |

## Bare minimum to ship

If you can only do three things, do these:

1. CLI `ledger categorise` works on at least one real CSV (or a synthetic
   one if you don't want to share your data).
2. The poisoned merchant string does not change the category.
3. A 5-minute live demo without a single "let me restart the import".
