# Competition payload

Import the official sample here when available, with `agent.yaml` at this directory's root.
Do not invent a replacement YAML schema. Keep agent prompts, ADK skills, and optional
adapters here. Local Python orchestration and model server configuration stay outside.

The local `--model` option selects the inference endpoint's model; it does not rewrite
agent.yaml. Before evaluation, ensure all YAML agents use the selected official model
alias. Use the official validator to confirm compatibility.

This scaffold is not yet a competition-valid submission.
