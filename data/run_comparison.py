"""Build a small, hand-labelled eval set from sample.csv and score the local
categoriser against it. Writes docs/llm-comparison.md with the numbers.

Honesty rule (PLAN §5.17: "the local numbers must still be real"): the doc
must say *which* classifier produced the numbers. When Ollama is unreachable
the pipeline falls back to the deterministic keyword classifier, and the hand
labels share substring keys with those rules — so the resulting accuracy is
trivially ~100% and says nothing about model quality. The generated table
labels the row accordingly instead of attributing fallback results to
llama3.2:3b.

Cloud column is left blank because no cloud LLM provider is reachable
in this environment — the attempted setup is documented in the doc.
"""
from __future__ import annotations

import csv
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE = ROOT / "data" / "sample.csv"
DB = ROOT / "data" / "ledger.sqlite"
OUT = ROOT / "docs" / "llm-comparison.md"  # noqa: F841

# (substring-in-merchant, expected_category). Hand labels for ~50 rows.
HAND_LABELS: list[tuple[str, str]] = [
    ("Tesco", "groceries"),
    ("Sainsbury", "groceries"),
    ("Costa", "coffee"),
    ("Pret", "eating_out"),
    ("TfL", "transport"),
    ("Shell", "transport"),
    ("Deliveroo", "eating_out"),
    ("Netflix", "subscriptions"),
    ("Spotify", "subscriptions"),
    ("British Gas", "utilities"),
    ("Octopus", "utilities"),
    ("Boots", "health"),
    ("Rent", "housing"),
    ("Council", "housing"),
    ("Payday", "income"),
    ("Transfer", "transfer"),
]

SEED = 7
SAMPLE_SIZE = 50


def label(merchant: str) -> str | None:
    m = merchant.lower()
    for needle, cat in HAND_LABELS:
        if needle.lower() in m:
            return cat
    return None


def select_labeled_rows() -> list[tuple[str, str]]:
    rows = list(csv.DictReader(SAMPLE.open()))
    labeled: list[tuple[str, str]] = []
    for r in rows:
        cat = label(r["Merchant"])
        if cat is not None:
            labeled.append((r["Merchant"], cat))
    rng = random.Random(SEED)
    rng.shuffle(labeled)
    return labeled[:SAMPLE_SIZE]


def predicted_category(merchant: str) -> str:
    """Read what the categoriser wrote into the DB (source 'rule' since
    Ollama is offline). We import lazily to ensure the DB exists."""
    from ledger.categorize import categorize_pending
    from ledger.db import connect

    with connect() as conn:
        cur = conn.execute(
            "SELECT category FROM transactions WHERE merchant = ? ORDER BY id DESC LIMIT 1",
            (merchant,),
        )
        row = cur.fetchone()
        if row and row["category"]:
            return row["category"]
    categorize_pending(limit=1000)
    with connect() as conn:
        row = conn.execute(
            "SELECT category FROM transactions WHERE merchant = ? ORDER BY id DESC LIMIT 1",
            (merchant,),
        ).fetchone()
        return row["category"] if row else "other"


def _classifier_provenance() -> tuple[tuple[int, int], bool, dict]:
    """Return ((prompt_tok, eval_tok), ollama_live, source_counts) — which
    classifier produced the DB's categories, per token usage and
    category_source rows."""
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        tok = conn.execute(
            "SELECT COALESCE(SUM(prompt_tokens),0) AS p, COALESCE(SUM(eval_tokens),0) AS e "
            "FROM token_usage"
        ).fetchone()
        sources = {
            r["category_source"]: r["n"]
            for r in conn.execute(
                "SELECT category_source, COUNT(*) AS n FROM transactions "
                "WHERE category IS NOT NULL GROUP BY category_source"
            ).fetchall()
        }
    prompt_tok, eval_tok = int(tok["p"]), int(tok["e"])
    model_rows = sources.get("model", 0)
    ollama_live = (prompt_tok + eval_tok) > 0 or model_rows > 0
    return (prompt_tok, eval_tok), ollama_live, sources


def main() -> None:
    eval_rows = select_labeled_rows()
    correct = 0
    confusion: dict[tuple[str, str], int] = {}
    for merchant, expected in eval_rows:
        predicted = predicted_category(merchant)
        if predicted == expected:
            correct += 1
        else:
            confusion[(expected, predicted)] = confusion.get((expected, predicted), 0) + 1
    accuracy = correct / len(eval_rows) if eval_rows else 0.0

    (prompt_tok, eval_tok), ollama_live, sources = _classifier_provenance()

    if ollama_live:
        local_label = "`llama3.2:3b` (local Ollama)"
        latency_cell = "_see run log_"
        accuracy_note = ""
    else:
        local_label = "rule-fallback classifier (Ollama offline — model **not evaluated**)"
        latency_cell = "n/a — no model calls made"
        accuracy_note = (
            "\n> ⚠️ The accuracy above is **not evidence of model quality**: the hand\n"
            "> labels share substring keys with `_fallback_classify`'s rules, so a\n"
            "> ~100% score is expected by construction. It only verifies that the\n"
            "> eval pipeline and the deterministic fallback agree with the labels.\n"
        )

    md = f"""# LLM comparison — local vs cloud categoriser

Sample: {len(eval_rows)} hand-labelled transactions drawn from
`data/sample.csv` (seed={SEED}, labelled by substring match against
the keys in `HAND_LABELS` in `data/run_comparison.py`).

| Model / classifier | Input tokens | Output tokens | Latency (s) | Accuracy | Cost (USD) |
|--------------------|-------------:|--------------:|------------:|---------:|-----------:|
| {local_label} | {prompt_tok} | {eval_tok} | {latency_cell} | {accuracy:.0%} ({correct}/{len(eval_rows)}) | 0.00 |
| Cloud model        | _not run — no provider reachable_ | — | — | — | — |
{accuracy_note}
Category sources in the database at generation time: `{sources}`.

## Cloud column — attempted setup

Per PLAN §5.17's escape hatch: no cloud provider is reachable from the
build environment (no provider configured in `opencode.json`, outbound
network unavailable), so the cloud run could not be executed. The table
structure is in place; re-running `data/run_comparison.py` in a session
with an authenticated cloud model fills the column from that session's
token report.

## Confusion (this sample)

"""
    if confusion:
        for (exp, got), n in sorted(confusion.items(), key=lambda kv: -kv[1]):
            md += f"- expected `{exp}` → got `{got}` ×{n}\n"
    else:
        md += "_(none)_\n"

    if ollama_live:
        conclusion = f"""Local `llama3.2:3b` (via Ollama) categorises {correct}/{len(eval_rows)}
of the hand-labelled sample correctly ({accuracy:.0%}), using
{prompt_tok + eval_tok} tokens recorded in `token_usage`. Cost is the
marginal electricity of running the model on the user's own machine —
zero marginal API spend."""
    else:
        conclusion = f"""`llama3.2:3b` was **not evaluated** — Ollama was unreachable in the
build environment, so the numbers above come from the deterministic
rule-based fallback classifier ({correct}/{len(eval_rows)} = {accuracy:.0%},
expected by construction; see the warning above). To produce the real
local-model row: start Ollama with `llama3.2:3b` pulled, wipe the
categories (`UPDATE transactions SET category=NULL, category_source=NULL;
DELETE FROM token_usage;`), re-run `categorise`, then re-run this script.
The harness, label set, and table structure are ready for that run."""

    md += f"""
## Conclusion

{conclusion}

The categorisation cache (kNN over transaction embeddings) makes the
repeat-call cost effectively zero once a merchant has been labelled
once — re-importing the same CSV reports 100% cache hits for
identical merchants, which is the S12 win.
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} — accuracy {accuracy:.0%} ({correct}/{len(eval_rows)}), ollama_live={ollama_live}")


if __name__ == "__main__":
    main()