# Clawpx4

**Termux-based modular AI assistant** with a Telegram interface and a local LLM backend (llama.cpp), optimised for low-RAM Android devices.

---

## Project Structure

```
Clawpx4/
├── bot/                  # Telegram bot, planner, dispatcher, security
│   ├── bot.py            # Entry point — start with: python -m bot.bot
│   ├── planner.py        # Intent planner (keyword → tool routing)
│   ├── dispatcher.py     # Tool dispatcher / registry
│   └── security.py       # Allowlist + rate limiting
├── brain/                # Local LLM interface
│   ├── inference.py      # Public generate() API
│   └── llm.py            # llama.cpp subprocess wrapper
├── memory/               # Persistent storage
│   ├── store.py          # Unified memory façade
│   ├── sqlite_store.py   # Chat history + key-value (SQLite)
│   └── chroma_store.py   # Semantic / vector search (ChromaDB)
├── tools/                # Modular Python executors
│   ├── base.py           # BaseTool abstract class
│   ├── calculator.py     # Safe arithmetic evaluator
│   ├── web_search.py     # DuckDuckGo search
│   ├── file_manager.py   # Sandboxed file read/write
│   └── shell_tool.py     # Whitelisted shell commands
├── automation/           # Scheduled tasks
│   └── scheduler.py      # APScheduler wrapper
├── interface/            # Alternative interfaces
│   └── cli.py            # Interactive CLI (no Telegram needed)
├── tests/                # Unit tests (pytest)
├── .env.example          # Configuration template
├── requirements.txt      # Python dependencies
└── .github/workflows/    # GitHub Actions CI
    └── python.yml
```

---

## Quick Start (Termux)

```bash
# 1. Install Python and dependencies
pkg install python git
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
nano .env   # set TELEGRAM_BOT_TOKEN and LLAMA_MODEL_PATH

# 3. Run the Telegram bot
python -m bot.bot

# Or test locally without Telegram
python -m interface.cli
```

---

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | *(required)* |
| `ALLOWED_USER_IDS` | Comma-separated allowed Telegram user IDs | *(all)* |
| `LLAMA_BINARY` | Path to `llama-cli` binary | `llama-cli` |
| `LLAMA_MODEL_PATH` | Path to your `.gguf` model file | *(required)* |
| `LLAMA_THREADS` | CPU threads for inference | `4` |
| `LLAMA_MAX_TOKENS` | Max tokens to generate | `512` |
| `LLAMA_CTX_SIZE` | Context window size | `2048` |
| `LLAMA_GPU_LAYERS` | GPU layers (0 = CPU only) | `0` |
| `SQLITE_DB_PATH` | SQLite database path | `data/clawpx4.db` |
| `CHROMA_DB_PATH` | ChromaDB persistence dir | `data/chroma_db` |
| `RATE_LIMIT_RPM` | Requests per user per minute | `10` |
| `TOOL_SHELL_ENABLED` | Enable shell tool | `false` |
| `SHELL_ALLOWED_COMMANDS` | Whitelisted shell commands | `ls,cat,pwd,echo,date,uname` |

---

## Tools

| Tool | Trigger example | Env flag |
|---|---|---|
| Calculator | `calc sqrt(144)` or `12 * 4` | `TOOL_CALCULATOR_ENABLED` |
| Web Search | `search Python tutorials` | `TOOL_WEB_SEARCH_ENABLED` |
| File Manager | `read file /tmp/notes.txt` | `TOOL_FILE_MANAGER_ENABLED` |
| Shell | `run: ls -la` | `TOOL_SHELL_ENABLED` *(off by default)* |

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Adding a New Tool

1. Create `tools/my_tool.py` subclassing `BaseTool`
2. Set `name`, `description`, and implement `run(**kwargs) -> ToolResult`
3. Register it in `bot/dispatcher.py` → `_build_default_dispatcher()`
