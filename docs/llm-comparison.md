# LLM comparison — local vs cloud categoriser

Sample: 50 hand-labelled transactions drawn from
`data/sample.csv` (seed=7, labelled by substring match against
the keys in `HAND_LABELS` in `data/run_comparison.py`).

| Model / classifier | Input tokens | Output tokens | Latency (s) | Accuracy | Cost (USD) |
|--------------------|-------------:|--------------:|------------:|---------:|-----------:|
| rule-fallback classifier (Ollama offline — model **not evaluated**) | 0 | 0 | n/a — no model calls made | 100% (50/50) | 0.00 |
| Cloud model        | _not run — no provider reachable_ | — | — | — | — |

> ⚠️ The accuracy above is **not evidence of model quality**: the hand
> labels share substring keys with `_fallback_classify`'s rules, so a
> ~100% score is expected by construction. It only verifies that the
> eval pipeline and the deterministic fallback agree with the labels.

Category sources in the database at generation time: `{'cache': 105, 'rule': 13}`.

## Cloud column — attempted setup

Per PLAN §5.17's escape hatch: no cloud provider is reachable from the
build environment (no provider configured in `opencode.json`, outbound
network unavailable), so the cloud run could not be executed. The table
structure is in place; re-running `data/run_comparison.py` in a session
with an authenticated cloud model fills the column from that session's
token report.

## Confusion (this sample)

_(none)_

## Conclusion

`llama3.2:3b` was **not evaluated** — Ollama was unreachable in the
build environment, so the numbers above come from the deterministic
rule-based fallback classifier (50/50 = 100%,
expected by construction; see the warning above). To produce the real
local-model row: start Ollama with `llama3.2:3b` pulled, wipe the
categories (`UPDATE transactions SET category=NULL, category_source=NULL;
DELETE FROM token_usage;`), re-run `categorise`, then re-run this script.
The harness, label set, and table structure are ready for that run.

The categorisation cache (kNN over transaction embeddings) makes the
repeat-call cost effectively zero once a merchant has been labelled
once — re-importing the same CSV reports 100% cache hits for
identical merchants, which is the S12 win.
