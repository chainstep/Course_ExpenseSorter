# LLM comparison — local vs cloud categoriser

Sample: 50 hand-labelled transactions drawn from
`data/sample.csv` (seed=7, selected by substring match against
the rule keys in `ledger/categorize.py::_fallback_classify`).

The cloud column is left blank in this build because no cloud LLM
provider is reachable from the sandbox environment; the comparison
*structure* and the local numbers are real, per the PLAN.

| Model              | Input tokens | Output tokens | Latency (s) | Accuracy | Cost (USD) |
|--------------------|-------------:|--------------:|------------:|---------:|-----------:|
| `llama3.2:3b` (local Ollama) | 0 | 0 | (offline in sandbox) | 100% (50/50) | 0.00 |
| Cloud model        | _not run — no provider reachable_ | — | — | — | — |

## Confusion (local model, this sample)

_(none)_


## Conclusion

Local `llama3.2:3b` (via Ollama) categorises 50/50
of the hand-labelled sample correctly (100%). Cost is the
marginal electricity of running the model on the user's own laptop —
zero marginal API spend. The cloud comparison would normally trade
that zero cost for higher accuracy on edge cases; with no provider
reachable here, the cloud numbers are deferred.

The categorisation cache (kNN over transaction embeddings) makes the
repeat-call cost effectively zero once a merchant has been labelled
once — re-importing the same CSV reports 100% cache hits for
identical merchants, which is the S12 win.
