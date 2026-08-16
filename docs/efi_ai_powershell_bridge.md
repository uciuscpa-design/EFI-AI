# EFI-AI PowerShell Bridge V1

## Purpose

Bridge V1 is a local OpenAI API companion for the EFI-AI repository. It reduces manual terminal copy/paste while keeping a deliberately narrow safety boundary.

It is **not** the same ChatGPT conversation/session. It is a local API client that can inspect the current repo through a fixed set of tools and maintain its own API conversation state while the process is running.

## Safety boundary

Bridge V1 can:

- read Git status;
- read the current short Git commit;
- read the eight most recent commits;
- read normal repository text/code files with approved extensions;
- run one existing `tests/test_gexy_*.py` file through pytest.

Bridge V1 cannot:

- run arbitrary shell commands;
- read `.env`, credentials, token, API-key, secret, or private-key paths;
- access paths outside the repository;
- run paid Databento downloads;
- run destructive Git operations;
- delete files;
- commit, push, reset, or rewrite branches;
- install packages as a model-selected action.

These limits are enforced in local Python code, not only in model instructions.

## API key

The bridge reads `OPENAI_API_KEY` from the current process environment. Never paste an API key into chat or commit it to Git.

## Safeguard test

From the EFI-AI repo root:

```powershell
uv run --with pytest pytest tests/test_efi_ai_bridge.py -q
```

Expected result: six tests pass.

## Start Bridge V1

From the EFI-AI repo root, with `OPENAI_API_KEY` already loaded in the same PowerShell session:

```powershell
uv run --with openai python scripts/efi_ai_powershell_bridge.py
```

Startup banner should include:

- `EFI-AI POWERSHELL BRIDGE V1`
- model name;
- `SAFE MODE`;
- the blocked-action summary.

At the `bridge>` prompt, examples include:

```text
What commit am I on?
Show me git status.
Read docs/gexy_tradeflow_temporal_extension_holdout_cost_plan.md and summarize the pending step.
Run tests/test_gexy_tradeflow_chronological_drift.py.
```

Local control commands:

- `/help`
- `/reset`
- `/quit`

## Cost

Every model turn uses the OpenAI API and therefore uses API billing. Local Git/file/test actions themselves do not add OpenAI tool charges, but their returned text becomes API input on the continuation turn. Keep requests focused and avoid sending unnecessarily large files.

## Next versions

A later bridge version may add explicit locally confirmed actions, but paid market-data requests and destructive operations must remain behind hard local approval/cost gates. No widening of this boundary is implied by V1.
