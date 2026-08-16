from __future__ import annotations

import json
import os
from pathlib import Path

from packages.bridge import read_repo_file, run_gexy_test, run_safe_action


MODEL = os.getenv("EFI_BRIDGE_MODEL", "gpt-5.6")

INSTRUCTIONS = """
You are EFI-AI Bridge V1, a local companion for the EFI-AI repository.

Safety and scope rules:
- You are not the same conversation/session as ChatGPT. You are a local API companion.
- Prefer concise, baby-step guidance.
- You may inspect the repository only through the supplied tools.
- You have no arbitrary shell tool.
- Never request, print, reveal, or read API keys, .env files, credentials, tokens, or secrets.
- Never claim a paid market-data request ran unless a tool result explicitly proves it.
- Paid Databento downloads, destructive Git operations, file deletion, commits, pushes, resets,
  branch rewrites, package installation, and arbitrary command execution are outside Bridge V1.
- If the user asks for an action Bridge V1 cannot perform, explain that it is blocked and give the
  smallest safe manual next step instead of inventing execution.
- For GEXY research, preserve frozen protocol constraints and distinguish $0/local-only work from
  paid data acquisition.
""".strip()

TOOLS = [
    {
        "type": "function",
        "name": "repo_action",
        "description": (
            "Run one predefined read-only repository action. No arbitrary command strings are accepted."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["git_status", "git_head", "git_recent"],
                }
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_repo_file",
        "description": (
            "Read a non-secret text/code file inside the repository. Secret-bearing paths, .env files, "
            "credentials, tokens, keys, and paths outside the repo are blocked locally."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "run_gexy_test",
        "description": (
            "Run exactly one existing tests/test_gexy_*.py test file with pytest. Arbitrary pytest "
            "arguments and other test paths are blocked locally."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"test_file": {"type": "string"}},
            "required": ["test_file"],
            "additionalProperties": False,
        },
    },
]


def _dispatch_tool(name: str, arguments: str, repo_root: Path) -> str:
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as exc:
        return f"BLOCKED: invalid tool arguments: {exc}"

    if name == "repo_action":
        return run_safe_action(str(args.get("action", "")), repo_root=repo_root)
    if name == "read_repo_file":
        return read_repo_file(str(args.get("path", "")), repo_root=repo_root)
    if name == "run_gexy_test":
        return run_gexy_test(str(args.get("test_file", "")), repo_root=repo_root)
    return f"BLOCKED: unknown tool {name!r}"


def _respond(client, *, user_text: str, previous_response_id: str | None, repo_root: Path):
    kwargs = {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "tools": TOOLS,
        "input": user_text,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = client.responses.create(**kwargs)

    while True:
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        if not calls:
            return response

        outputs = []
        for call in calls:
            result = _dispatch_tool(call.name, call.arguments, repo_root)
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": result,
                }
            )

        response = client.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            tools=TOOLS,
            previous_response_id=response.id,
            input=outputs,
        )


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not loaded in this PowerShell session.")

    repo_root = Path.cwd().resolve()
    if not (repo_root / ".git").exists():
        raise SystemExit("Run the bridge from the EFI-AI repository root.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "openai is not installed for this run. Start with: "
            "uv run --with openai python scripts/efi_ai_powershell_bridge.py"
        ) from exc

    client = OpenAI()
    previous_response_id: str | None = None

    print("EFI-AI POWERSHELL BRIDGE V1")
    print(f"MODEL: {MODEL}")
    print("SAFE MODE: read-only repo inspection + one-file GEXY pytest only")
    print("BLOCKED: arbitrary shell, paid Databento, destructive Git, secret-file reads")
    print("Commands: /help, /reset, /quit")

    while True:
        try:
            user_text = input("\nbridge> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBridge closed.")
            return

        if not user_text:
            continue
        if user_text.lower() in {"/quit", "quit", "exit"}:
            print("Bridge closed.")
            return
        if user_text.lower() == "/reset":
            previous_response_id = None
            print("Conversation state reset.")
            continue
        if user_text.lower() == "/help":
            print(
                "Ask about repo status, recent commits, a code/doc file, or a single GEXY test. "
                "Bridge V1 cannot execute paid or destructive actions."
            )
            continue

        try:
            response = _respond(
                client,
                user_text=user_text,
                previous_response_id=previous_response_id,
                repo_root=repo_root,
            )
        except Exception as exc:  # Keep the local loop alive on API/network errors.
            print(f"BRIDGE ERROR: {type(exc).__name__}: {exc}")
            continue

        previous_response_id = response.id
        text = (response.output_text or "").strip()
        print(text if text else "[No text response returned]")


if __name__ == "__main__":
    main()
