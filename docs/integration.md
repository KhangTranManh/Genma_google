# Official harness integration

1. Obtain the competition's `HARNESS_README.md`, `sample_submission/`, tasks,
   sandbox assets and harness wheels when available. Keep originals in `third_party/`.
2. Copy the official sample contents into `submission/`. Compare its supported model
   identifiers, tools and skill structure against the current rules.
3. Install official harness dependencies in an isolated Python environment. Pin exact
   versions after validating the official bundle. Do not replace the runtime with a
   homegrown agent loop. The local development loop in `gemma_lab.agent` is for
   experiments; official runs must still use the official compiler and harness.
4. Set `harness.command` and `harness.validator_command` to argv arrays matching the
   documented CLIs. No shell interpolation occurs. Available placeholders are
   `{submission}`, `{model}`, `{base_url}`, `{tasks}`, `{instance_id}`, `{run_dir}`,
   `{agent_input}`. Keep each argument separate. Literal braces must be doubled.
5. The wrapper runs the trusted official harness on the host; that harness must execute
   repository code and agent tools inside its documented Docker sandbox. Do not run
   repository setup scripts directly through this wrapper.
6. Keep reference patches and evaluator tests out of agent-visible mounts. The generated
   `agent_input.json` contains only instance ID, repo, base commit, issue and hints.
   `{tasks}` refers to the full evaluation dataset and is only for a trusted harness,
   never an agent tool or agent-visible file.
7. Confirm the endpoint's served alias matches every LLM agent in the YAML. The local
   model selection does not modify submission YAML or validate it semantically.
8. Run one public task, inspect trajectory and patch, then evaluate on a held-out group
   across repos. Record timing, tokens and pass/fail from official evaluator output.

No official schema or CLI flags are guessed by this scaffold. The package command
requires the configured validator unless explicitly building an unvalidated archive.
Keep credentials in environment variables, never TOML or run metadata.
