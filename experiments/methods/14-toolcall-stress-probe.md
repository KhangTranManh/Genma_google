# Tool-call stress probe v1

Keep all prior experiments frozen. Configuration: configs/toolcall-stress.toml.

Run 24 capture-only requests: two models, three arms, four cases each.
- short_direct: fresh direct-tool control.
- long_direct: same direct cases and tool schemas, synthetic background calibrated by server tokenizer to 8192 ±128 input tokens. This is not multi-turn history.
- short_skill: actual ADK run_skill_script declaration; read/test with separate list/object arguments. Different interface/task mix, so aggregate accuracy is not a causal estimate of JSON nesting.

All arms advertise the same five schemas. Temperature zero, thinking disabled, non-streaming, output limit512, model context16384. No tool execution. Save raw token IDs and API parsed calls from the same generation; replay installed Gemma4Parser and independently decode native syntax. Unsupported syntax is ambiguous, not evidence of parser corruption. One sample per case cannot estimate stable failure rates.

Source and input hashes: runs/toolcall-stress-v1/frozen-inputs.json. State and logs in the same directory. Execution is owned by gemma-toolcall-stress-v1.service; it completes and stops automatically. No recurring rerun trigger.

Reports: reports/toolcall-stress-v1/comparison.html, comparison.md, comparison.json. Preserve separate model/arm/case capture folders.
