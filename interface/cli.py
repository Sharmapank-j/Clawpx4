"""interface/cli.py — Interactive CLI for local testing without Telegram.

Run with:
    python -m interface.cli

This lets you chat with Clawpx4 directly in the terminal — useful for
testing on Termux without setting up a Telegram bot token.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on the path when run directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

from bot.dispatcher import get_dispatcher
from bot.planner import get_planner
from brain.inference import generate
from memory.store import get_store

_BANNER = """
╔══════════════════════════════════════╗
║   Clawpx4 — Local AI Assistant CLI  ║
╚══════════════════════════════════════╝
Type your message and press Enter.
Commands: /reset  /status  /help  /quit
"""


def _print_status() -> None:
    tools = get_dispatcher().available_tools()
    tool_list = ", ".join(tools) if tools else "none"
    print(f"\n[Status] Available tools: {tool_list}\n")


def run() -> None:
    """Start the interactive CLI session."""
    print(_BANNER)

    planner = get_planner()
    dispatcher = get_dispatcher()
    store = get_store()
    user_id = "cli_user"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "exit", "quit"):
            print("Goodbye!")
            break

        if user_input.lower() == "/reset":
            store.clear_history(user_id)
            print("[History cleared]\n")
            continue

        if user_input.lower() in ("/status", "status"):
            _print_status()
            continue

        if user_input.lower() in ("/help", "help"):
            print(
                "\nCommands: /reset /status /help /quit\n"
                "Prefix: 'search <query>', 'calc <expr>'\n"
            )
            continue

        plan = planner.plan(user_input)

        if plan.action == "tool":
            result = dispatcher.dispatch(plan.tool_name, **plan.tool_kwargs)
            reply = str(result)
            store.save_message(user_id, "user", user_input)
            store.save_message(user_id, "assistant", reply)
        elif plan.action == "command":
            if plan.command == "reset":
                store.clear_history(user_id)
                reply = "[History cleared]"
            else:
                reply = "[Use /help for available commands]"
        else:
            history = store.get_history(user_id)
            store.save_message(user_id, "user", user_input)
            try:
                reply = generate(user_input, history=history)
            except RuntimeError as exc:
                reply = f"[LLM error] {exc}"
            store.save_message(user_id, "assistant", reply)

        print(f"\nClawpx4: {reply}\n")


if __name__ == "__main__":
    run()
