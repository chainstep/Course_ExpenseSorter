# Starter agents — Expense Sorter

You do not have to start from scratch. The Session 6 workshop builds a
notes-style MCP server; the smallest delta is to point it at a SQLite
table of transactions and add a CSV import.

## Reuse

- The **FastMCP server pattern** from
  [Session 6](../sessions/session_6_mcp.md):
  - Three tools (`categorise`, `query`, `monthly_report`).
  - One resource (`budget://status`).
- The **tool anatomy** and **permission rules** from
  [Session 7](../sessions/session_7_tools.md).
- The **local Ollama model** as the default tier from
  [Session 5](../sessions/session_5_agents.md).
- The **model-tiering** and **cost comparison** material from
  [Session 12](../sessions/session_12_saving_tokens.md).
- The **prompt-construction diagram** for `AGENTS.md` placement from
  [Session 3](../sessions/session_3_context.md).

## Architecture (suggested)

```
   ┌────────────────────────────┐
   │  CSV bank exports          │
   │  → import (S7 custom tool) │
   └─────────────┬──────────────┘
                 │
                 ▼
   ┌────────────────────────────┐
   │  ledger_mcp                │
   │  (S6, S7)                  │
   └─────────────┬──────────────┘
                 │
                 ▼
   ┌────────────────────────────┐
   │  SQLite + vec             │
   │  (transactions, categories)│
   └─────────────┬──────────────┘
                 │
                 ▼
   ┌────────────────────────────┐         ┌──────────────────────┐
   │  categoriser agent         │         │  planner agent       │
   │  (Ollama, read-only)       │ ──escal.─▶│  (flagship, monthly) │
   └────────────────────────────┘         └──────────────────────┘
                                                       │
                                                       ▼
                                              reports/<YYYY-MM>.md
                                              reports/<YYYY-MM>.png
```

Deviate freely — the sketch is to anchor the vocabulary, not to constrain
the shape. The two agents do **not** share a context window; the
planner only sees a summary of the categorisation, never the raw
merchants (S12).

## First commit

In your own repo, drop in a copy of the Session 6 notes server, point it
at a SQLite table of transactions, and add a `categorise()` over Ollama.
No session covers embeddings directly — the two lightest options:

- **sqlite-vec** — a SQLite extension; vectors live in the same file as
  the transactions: <https://github.com/asg017/sqlite-vec>
- **Chroma** — an embedded Python vector store:
  <https://docs.trychroma.com/>

That is your baseline. The seeded poisoned merchant string is the next
commit: a single CSV row with a merchant field that contains an injected
instruction, used by the wrapper's regression test.

## Do not copy

- The Session 6 example assumes friendly input. Replace it with the S10
  untrusted-content boundary before you ingest any CSV you did not
  author; merchant strings are user-controlled text.
- The Session 6 example uses stdio transport. Stay on stdio; the agent
  is on the same host as the database.
- The `categoriser` agent must not have write access to the database
  beyond the `categorise` tool. The S10 boundary is enforced by the
  agent config, not by the prompt.
- The chart is a path, not bytes. Return the path from the report tool
  (S7 + S12).
