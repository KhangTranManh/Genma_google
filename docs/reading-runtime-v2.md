# Focused reading runtime v2

V1 stopped on its first R1/12B/w3lib run at 39 LLM calls because a request exceeded
8192 input tokens. No other v1 cells ran. That result is preserved as an infrastructure
failure; 8 read requests and zero identical read results do not establish a quality gain.

ADK's EventsCompactionConfig trigger is post-invocation. It does not guarantee that
a long sequence of tool calls inside one invocation stays below 8192 tokens.

V2 changes the local serving context to 16384 tokens for BOTH models and all R0/R1/R2
arms. Existing 31B logs reported roughly 19238-token GPU KV cache capacity; startup at
16k is checked explicitly before enabling the new queue. This remains smaller than
the official 32768-token runtime and is not a guarantee that overflow is impossible.

Prompt, skill, 48 turns / 96 tools / 15 minutes and compaction settings remain fixed.
No v1 results are used as paired controls. There are 18 new v2 development cells.
31B runs first to reuse the capacity-checked model, followed by 12B. Per issue the
order remains R1 → R0 → R2. No claim of randomized order or statistical significance.

Separate service namespace gemma-lab-reading-v2-vllm@ uses
configs/reading-runtime-v2.toml. The original project default remains 8192. The v2
starter checks the actual /v1/models max_model_len instead of assuming the server
matches the intended config. Existing model services are stopped before a switch;
all tasks still run one model on both GPUs at a time.

State/results: runs/reading-v2/. Report: reports/reading-v2/comparison.html. V1 stays
at runs/reading-v1/ and reports/reading-v1/. Source files matching v1's frozen hashes
were archived before the new runner option was added. An input change, interruption
or new overflow stops v2 for review; no silent increase of budgets or model switch.
