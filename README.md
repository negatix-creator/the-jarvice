# The Jarvice 🤖

**Full-stack AI assistant with corporate data summaries, memory, and scheduling**

The Jarvice installs a complete system: OpenClaw agent framework + data scrapers + PII anonymization + AI summaries + Telegram delivery — all on your machine.

## ✨ What you get

- 📧 **Exchange scraping** — email + calendar via EWS
- 💬 **Teams scraping** — chats + meetings via IC3 token
- 🔒 **PII anonymization** — RED/GREEN pipeline, names/emails never leave your machine
- 🤖 **AI summaries** — cloud models (glm-5.1:cloud) or local (qwen3:14b)
- 🧠 **Memory & embeddings** — nomic-embed-text for semantic search
- 📲 **Telegram delivery** — HTML summaries with smart chunking
- ⏰ **Scheduled summaries** — morning + evening via cron
- 🛡️ **Security-first** — Keychain credentials, log sanitization, audit log
- 🔧 **Full system** — OpenClaw + Jarvice + Ollama + agent, one command

## ⚡ Quick Start

One command installs everything:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/negatix-creator/the-jarvice/main/setup.sh)
```

This installs:
1. **Homebrew** (if missing)
2. **Python 3.12** (if missing)
3. **Node.js** (for OpenClaw)
4. **OpenClaw** (agent framework)
5. **Ollama** + models (glm-5.1:cloud + nomic-embed-text)
6. **The Jarvice** (data pipeline + summaries)
7. **OpenClaw workspace** (AGENTS.md, SOUL.md, MEMORY.md)
8. **Config** with cloud models preconfigured

Then the script interactively asks for:
- **Telegram bot token** (from @BotFather)
- **Exchange credentials** (optional, for email/calendar)
- **OpenClaw channel setup** (links bot to agent)

### Manual steps after setup

```bash
# Verify everything works
the-jarvice doctor && openclaw status

# Run first summary
the-jarvice run --once

# Schedule daily summaries
the-jarvice enable

# Start OpenClaw gateway (if not running)
openclaw gateway run
```

## 📋 Example Summary

```
📅 Morning Summary — May 21, 2026

🏢 Important:
• [SENDER_1]: Q2 Budget Review — deadline Friday
• [SENDER_2]: Production incident — P1 escalation

📋 Follow-ups:
• [SENDER_3]: Contract renewal — response needed by May 25
• [SENDER_4]: Team standup moved to 11:00

📌 Deadlines:
• Q2 budget submission — May 23
• Security audit response — May 26
```

> All names are anonymized ([SENDER_N]). Only you see real names in Telegram.

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `the-jarvice configure` | Full configuration wizard |
| `the-jarvice configure --quick` | Quick setup (email + password + bot token) |
| `the-jarvice configure --reauth exchange` | Re-configure Exchange credentials |
| `the-jarvice run --once` | Run pipeline once |
| `the-jarvice run --once --dry-run` | Run without sending to Telegram |
| `the-jarvice doctor` | Diagnose system health (12+ checks) |
| `the-jarvice enable` | Enable scheduled summaries |
| `the-jarvice disable` | Disable scheduled summaries |
| `the-jarvice version` | Show version |
| `the-jarvice uninstall` | Remove The Jarvice |
| `openclaw status` | Check gateway, channels, models |
| `openclaw channels add` | Add Telegram/Signal channel |
| `openclaw gateway run` | Start the agent gateway |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  OpenClaw Gateway                │
│         (agent framework, memory, cron)          │
├─────────────────────────────────────────────────┤
│                                                  │
│  Exchange/Teams ──► PII Anonymizer ──► LLM      │
│                     (RED → GREEN)     (summary)   │
│                         │               │         │
│                    Keychain          Ollama       │
│                    (creds)        (cloud/local)  │
│                                        │         │
└────────────────────────────────────────┼─────────┘
                                        │
                                   Telegram ──► You
```

- **Cloud Mode** — anonymized data to glm-5.1:cloud (default, no GPU needed)
- **Local Mode** — everything on-device with qwen3:14b (8.6 GB)
- **Enhanced Mode** — cloud + knowledge graph (planned)

## 📋 Requirements

- macOS 12+ (Apple Silicon or Intel)
- 3 GB free disk space (cloud models) or 12 GB (local models)
- Internet connection (for cloud models and Telegram)
- Telegram account (for bot creation)

## 🔒 Security

- **PII never leaves your machine** — RED directory (`chmod 700`) holds raw data
- **Credentials in Keychain** — macOS Keychain / Linux keyring, not config files
- **Anonymized before LLM** — all names/emails replaced with [SENDER_N] tokens
- **Path traversal protection** — PII directories validated
- **Ollama prompt hardening** — system prompt prevents injection
- **Log sanitization** — tokens and passwords masked in all output

## 🔍 Troubleshooting

```bash
# Full system check
the-jarvice doctor && openclaw status

# Re-configure credentials
the-jarvice configure --quick

# Ollama issues
ollama list                    # check models
ollama pull glm-5.1:cloud      # re-download model
open -a Ollama                 # restart Ollama

# View logs
cat ~/.the-jarvice/logs/cron.log

# Reset and re-setup
the-jarvice uninstall
bash <(curl -fsSL https://raw.githubusercontent.com/negatix-creator/the-jarvice/main/setup.sh)
```

## 📁 Directory Layout

```
~/.the-jarvice/
├── config.yaml          # Main configuration
├── venv/                # Python virtual environment
├── src/the-jarvice/     # Source code (git clone)
├── data/pii/
│   ├── RED/             # Raw PII data (chmod 700)
│   └── GREEN/           # Anonymized data
└── logs/                # Application logs

~/.openclaw/
├── openclaw.json        # OpenClaw gateway config
└── workspace/
    ├── AGENTS.md        # Agent role definition
    ├── SOUL.md          # Agent personality
    ├── MEMORY.md        # Agent memory
    └── memory/          # Daily memory dumps
```

## 📄 License

MIT

---

*The Jarvice v0.3.0 — Full-stack AI assistant with privacy-first approach*