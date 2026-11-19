# Local vLLM runtime

Local environment created on 2026-11-15:

- Python 3.12.3; vLLM 0.33.0; PyTorch 2.14.0+cu130.
- NVIDIA driver 580.178.04; two A16 GPUs, compute capability 8.6.
- Public upstream checkpoint: `google/gemma-4-E4B-it-qat-w4a16-ct`.
- Revision: `6cd26aaa2357fb2bad8c51699a7558a4d1a965bb`.
- Downloaded model SHA256 verified against the upstream LFS object ID.
- Installed versions are captured in `configs/local-requirements.lock`.

Runtime configuration: two GPUs with tensor parallel 2, text-only model loading,
8K context, 512-token chunked prefill, and Gemma 4 tool/reasoning parsers.

Single-GPU startup loaded the model but failed during Inductor autotuning because
of an additional 5.25 GiB temporary allocation. The two-GPU configuration shards
the model instead. This is a local hardware finding, not a competition constraint.

This local runtime is separate from the competition's official dependency versions.

```bash
source .venv/bin/activate
./gemma-lab serve --model e4b
# Separate terminal:
./gemma-lab health --model e4b
python scripts/smoke_inference.py
python scripts/monitor_server.py --duration 60
```

The server binds to localhost only. Keep logs in `runs/`; generated response and timing
are saved to `runs/smoke.json`. The reported end-to-end rate includes prefill and HTTP
overhead; it is not a decode-only benchmark. Initial model loading, kernel compilation
and CUDA graph capture may take longer than subsequent starts.

A detached server launched during setup records its API process ID in
`runs/vllm-server.pid` and log in `runs/vllm-server-tp2.log`. Check the process before stopping:

```bash
ps -p "$(cat runs/vllm-server.pid)" -o pid,args
kill -TERM "$(cat runs/vllm-server.pid)"
```

Do not start a second server on the same port/GPU while this one is active.

## Verified smoke results

Two-GPU TP=2 run completed successfully with compilation and CUDA graphs enabled.
The server used approximately 12,786 MiB on each GPU, including allocated KV cache.

- Code generation: 198 output tokens, 4.44 seconds on the initial request.
- Three warm streaming requests: 65.91, 67.22, 67.24 output tokens/second end to end.
- Approximate decode rate: 68.74–68.83 output tokens/second.
- First content latency: 125, 64, 62 milliseconds.
- Prompt: 39 tokens, repeated across runs with prefix caching enabled; thinking disabled.
- Generated function passed 6 assertions, including unhashable lists and dictionaries.
- Automatic `read_file` tool-call name and JSON arguments parsed correctly.

These are short-prompt inference smoke checks, not SWE task solve rates or a long-context
benchmark. See `runs/smoke.json`, `runs/stream-benchmark.json`,
`runs/smoke-tools.json`, and `runs/smoke-code-validation.json` for exact output.

```bash
.venv/bin/python scripts/smoke_inference.py
.venv/bin/python scripts/smoke_tools.py
.venv/bin/python scripts/benchmark_stream.py
.venv/bin/python scripts/monitor_server.py --duration 60
```
