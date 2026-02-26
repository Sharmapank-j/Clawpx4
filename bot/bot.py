"""bot/bot.py — Clawpx4 Telegram bot entry point.

Start the bot:
    python -m bot.bot

Or directly:
    python bot/bot.py

Environment variables (set in .env):
    TELEGRAM_BOT_TOKEN – required
    ALLOWED_USER_IDS   – optional comma-separated allowlist
    RATE_LIMIT_RPM     – optional requests-per-minute cap (default 10)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load .env before importing local modules that read env vars
load_dotenv()

from bot.dispatcher import get_dispatcher
from bot.planner import get_planner
from bot.security import get_guard
from brain.inference import generate
from memory.store import get_store

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BOT_NAME = "Clawpx4"

_HELP_TEXT = (
    f"*{BOT_NAME}* — Termux AI Assistant\n\n"
    "Commands:\n"
    "  /start  — Welcome message\n"
    "  /help   — Show this help\n"
    "  /reset  — Clear your conversation history\n"
    "  /status — Show bot and model status\n\n"
    "Just send any message to chat with the AI.\n"
    "Prefix with *search …* to query the web, or *calc …* for maths."
)


async def _send(update: Update, text: str) -> None:
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ok, reason = get_guard().validate(user.id)
    if not ok:
        await _send(update, reason)
        return
    await _send(
        update,
        f"👋 Hello {user.first_name}! I'm *{BOT_NAME}*, your local AI assistant.\n\n"
        + _HELP_TEXT,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ok, reason = get_guard().validate(update.effective_user.id)
    if not ok:
        await _send(update, reason)
        return
    await _send(update, _HELP_TEXT)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    ok, reason = get_guard().validate(user_id)
    if not ok:
        await _send(update, reason)
        return
    get_store().clear_history(str(user_id))
    await _send(update, "🗑 Conversation history cleared.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ok, reason = get_guard().validate(update.effective_user.id)
    if not ok:
        await _send(update, reason)
        return

    tools = get_dispatcher().available_tools()
    tool_list = "\n".join(f"  • *{n}*: {d}" for n, d in tools.items()) or "  None enabled"
    model_path = os.getenv("LLAMA_MODEL_PATH", "not set")
    status_text = (
        f"*{BOT_NAME} Status*\n\n"
        f"🤖 Model: `{model_path}`\n\n"
        f"🔧 Available tools:\n{tool_list}"
    )
    await _send(update, status_text)


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    message = update.message.text or ""

    ok, reason = get_guard().validate(user.id)
    if not ok:
        await _send(update, reason)
        return

    planner = get_planner()
    dispatcher = get_dispatcher()
    store = get_store()

    plan = planner.plan(message)
    logger.info("user=%s plan=%s", user_id, plan)

    # -- Internal /commands (also reachable as plain text, belt-and-braces) --
    if plan.action == "command":
        if plan.command == "reset":
            store.clear_history(user_id)
            await _send(update, "🗑 Conversation history cleared.")
        elif plan.command in ("help", "start"):
            await _send(update, _HELP_TEXT)
        elif plan.command == "status":
            await cmd_status(update, context)
        return

    # -- Tool execution --
    if plan.action == "tool":
        result = dispatcher.dispatch(plan.tool_name, **plan.tool_kwargs)
        reply = str(result)
        await _send(update, reply)
        store.save_message(user_id, "user", message)
        store.save_message(user_id, "assistant", reply)
        return

    # -- LLM fallback --
    history = store.get_history(user_id)
    store.save_message(user_id, "user", message)
    try:
        reply = generate(message, history=history)
    except RuntimeError as exc:
        reply = f"⚠️ {exc}"
    await _send(update, reply)
    store.save_message(user_id, "assistant", reply)


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def build_app() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Copy .env.example to .env and fill in your token."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


def main() -> None:
    logger.info("Starting %s…", BOT_NAME)
    build_app().run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
