# The Jarvice 🤖

**Local-first AI assistant for corporate data summaries**

The Jarvice scrapes your Exchange email and Teams chats, anonymizes personal data, summarizes with a local LLM, and delivers daily briefings to your Telegram — all on your machine, no cloud required.

## ✨ Features

- 📧 **Exchange scraping** — email + calendar via EWS
- 💬 **Teams scraping** — chats + meetings via IC3 token
- 🔒 **PII anonymization** — RED/GREEN pipeline, names/emails never leave your machine
- 🤖 **Local AI** — Ollama summarizes on-device (optional cloud providers in v0.3)
- 📲 **Telegram delivery** — HTML summaries with smart chunking
- 🛡️ **Security-first** — path traversal protection, keyring credentials, log sanitization, audit log
- 🔧 **12 diagnostics** — `doctor` command checks everything
- ⚡ **Quick setup** — 3 fields to start (`configure --quick`)
- 📅 **Cron scheduling** — `enable`/`disable` system crontab
- 🧪 **Dry run** — `run --dry-run` to test without sending

## ⚡ Quick Start (5 minutes)

```bash
# 1. Install
bash <(curl -fsSL https://github.com/your-org/the-jarvice/raw/main/setup.sh)
# Or from source:
git clone https://github.com/your-org/the-jarvice.git && cd the-jarvice
bash setup.sh

# 2. Configure (just 3 fields!)
the-jarvice configure --quick

# 3. Run
the-jarvice run --once

# 4. Schedule
the-jarvice enable
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
| `the-jarvice doctor` | Diagnose system health (12 checks) |
| `the-jarvice enable` | Enable scheduled summaries |
| `the-jarvice disable` | Disable scheduled summaries |
| `the-jarvice version` | Show version |
| `the-jarvice uninstall` | Remove The Jarvice |

## 🔒 Security

- **PII never leaves your machine** — RED directory (`chmod 700`) holds raw data, GREEN holds anonymized
- **Credentials in Keychain** — passwords and tokens stored in macOS Keychain / Linux keyring, not config files
- **Path traversal protection** — PII directories validated to stay within `~/.the-jarvice/`
- **Ollama prompt hardening** — system prompt prevents injection attacks
- **Log sanitization** — tokens and passwords masked in all log output

## 🏗️ Architecture

```
Exchange/Teams ──► PII Anonymizer ──► Ollama/OpenAI ──► Telegram
                   (RED → GREEN)        (summary)         (HTML)
```

- **Private Mode** — all data stays on your machine (Ollama)
- **Enhanced Mode** — anonymized data sent to cloud model (optional)
- **Knowledge Mode** — Enhanced + knowledge graph (planned)

## 📋 Requirements

- macOS (Linux planned for v0.2.1)
- Python 3.10+
- Ollama (auto-installed by setup.sh)
- Exchange or Teams account
- Telegram bot token

## 🔍 Troubleshooting

```bash
# Check everything
the-jarvice doctor

# Re-configure a service
the-jarvice configure --reauth exchange
the-jarvice configure --reauth telegram

# View logs
cat ~/.the-jarvice/logs/cron.log

# Disable and re-enable
the-jarvice disable
the-jarvice enable
```

## 📄 License

MIT

---

*The Jarvice v0.2.0 — Built with 🔒 privacy-first approach*