# Framework decision — no framework

**Choice:** plain Python modules, stdlib + `fastmcp` + `pydantic` +
`matplotlib`. No agent framework, no orchestrator.

**Why this passes the S9 decision tree.** The S9 decision tree says:
"one agent + a few tools → opencode or PydanticAI, stop reading."
opencode already gives us the two named agents (`categoriser`,
`planner`) and their permissions, the SQLite database is the durable
state shared between them, and the runs are seconds long so
checkpointing is overhead, not value. The categorisation step is a
single JSON call to Ollama — wrapping it in a typed-loop framework
would add an abstraction layer without changing the LLM's behaviour.
Pydantic is already in the import list, but used narrowly: validating
the model's JSON output against the closed `CATEGORIES` enum.

**Why not PydanticAI.** PydanticAI's value is in typed multi-step
agent loops with retry-on-validation-error. Our loop has exactly one
LLM call per row, the enum is checked once, and we cache categorisation
by embedding. PydanticAI would mostly be plumbing. It becomes
attractive the moment a second typed output (a `Transaction` summary,
a `BudgetDecision`) shows up — at that point we switch.

**Why not LangGraph.** LangGraph shines when the monthly loop needs
durable multi-step recovery (restartable nodes, human-in-the-loop
edges). Our monthly report is a single-shot aggregate-and-write —
no graph, no recovery edge case.

**Sandbox fallback.** Ollama was not reachable in the build sandbox
(no `localhost:11434`). `ledger/embeddings.py` and
`ledger/categorize.py` therefore fall back to a deterministic
hash-seeded pseudo-embedding and a keyword-based rule classifier
respectively. The real Ollama path is primary; the fallback exists so
the pipeline can be exercised end-to-end during CI / demo runs
without requiring the model server. The MCP server's local-only
guard is unchanged.
