# The Jarvice 🤖

**Full-stack AI assistant with corporate data summaries, memory, and scheduling**

The Jarvice installs a complete system: OpenClaw agent framework + data scrapers + PII anonymization + AI summaries + Telegram delivery — all on your machine.

## ✨ What you get

- 📧 **Exchange scraping** — email + calendar via EWS
- 💬 **Teams scraping** — chats + meetings via IC3 token
- 🔒 **PII anonymization** — RED/GREEN pipeline, names/emails never leave your machine
- 🤖 **AI summaries** — cloud models (glm-5.2:cloud primary, glm-5.1:cloud fallback)
- 🧠 **Memory & embeddings** — nomic-embed-text for semantic search
- 📲 **Telegram delivery** — HTML summaries with smart chunking
- ⏰ **Scheduled summaries** — morning + evening via cron
- 🛡️ **Security-first** — Keychain credentials, log sanitization, audit log
- 🔧 **Full system** — OpenClaw + Jarvice + Ollama + agent, one command
- 🚀 **One-command deploy** — `scripts/deploy-openclaw-{macos,linux}.sh`

## ⚡ Quick Start

### Option A: The Jarvice full pipeline (with scrapers)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/negatix-creator/the-jarvice/main/setup.sh)
```

This installs: Homebrew, Python 3.12, Node.js, OpenClaw, Ollama + models, The Jarvice pipeline, workspace, config.

### Option B: Just OpenClaw + bot (no scrapers)

For deploying an OpenClaw agent on any macOS or Linux machine — no scrapers, just bot + memory + cloud models:

**macOS:**
```bash
scp scripts/deploy-openclaw-macos.sh user@host:/tmp/
scp ~/.ollama/id_ed25519 user@host:~/.ollama/id_ed25519
scp ~/.ollama/id_ed25519.pub user@host:~/.ollama/id_ed25519.pub
ssh user@host 'BOT_TOKEN=<token> OWNER_TG_ID=<id> OLLAMA_KEY=*** bash /tmp/deploy-openclaw-macos.sh'
```

**Linux (Ubuntu/Debian/Fedora/CentOS/Alpine):**
```bash
scp scripts/deploy-openclaw-linux.sh user@host:/tmp/
scp ~/.ollama/id_ed25519 user@host:~/.ollama/id_ed25519
scp ~/.ollama/id_ed25519.pub user@host:~/.ollama/id_ed25519.pub
ssh user@host 'BOT_TOKEN=<token> OWNER_TG_ID=<id> OLLAMA_KEY=*** bash /tmp/deploy-openclaw-linux.sh'
```

Both deploy scripts:
- Install packages (Node, OpenClaw, Ollama)
- Copy Ollama SSH-key for cloud model authorization
- Create config (glm-5.2:cloud + glm-5.1:cloud, Telegram bot, memory health)
- Set up auto-start services (LaunchAgent on macOS, systemd on Linux)
- Run 8-9 smoke tests

### After setup

```bash
the-jarvice doctor && openclaw status   # verify
the-jarvice run --once                   # first summary
the-jarvice enable                        # schedule daily summaries
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

- **Cloud Mode** — anonymized data to glm-5.2:cloud (primary) + glm-5.1:cloud (fallback). No GPU needed.
- **Enhanced Mode** — cloud + knowledge graph (planned)

## 📋 Requirements

- macOS 12+ (Apple Silicon or Intel) OR Linux (Ubuntu/Debian/Fedora/CentOS)
- 3 GB free disk space
- Internet connection (for cloud models and Telegram)
- Telegram account (for bot creation)
- Ollama SSH-key (for cloud model authorization — provided by deploy script)

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
ollama pull glm-5.2:cloud      # re-download model

# Cloud model 403 error?
# → Ollama SSH-key not authorized. Run deploy script with OLLAMA_KEY param.

# Gateway crash loop?
# → Check config: openclaw config validate
# → Common cause: invalid plugins.entries.*.config (remove unsupported fields)

# View logs
# macOS:
cat /tmp/openclaw-gateway.log
# Linux:
sudo journalctl -u openclaw-gateway --no-pager -n 30

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

*The Jarvice v0.4.0 — Full-stack AI assistant with privacy-first approach*