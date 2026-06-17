# Configuration Reference

The Jarvice uses a single `config.yaml` file as the source of truth. OpenClaw's `openclaw.json` is auto-generated from it during `the-jarvice configure`.

**Location:** `~/.the-jarvice/config.yaml`

## Generating the Config

Run the interactive wizard:

```bash
the-jarvice configure
```

Or create/edit `~/.the-jarvice/config.yaml` manually using the reference below.

## Full Reference

```yaml
# The Jarvice Configuration — v1
# This is the single source of truth for all settings.
# OpenClaw config (openclaw.json) is generated from this file.

version: 1
```

### `version`

- **Type:** `integer`
- **Default:** `1`
- **Required:** Yes
- **Description:** Config schema version. Currently only version `1` is supported. Future versions may include migration logic.

---

## `exchange`

Exchange (EWS) email scraper settings.

```yaml
exchange:
  enabled: true
  server: ""
  email: ""
  auth_mode: "auto"
  keychain_service: "the-jarvice.exchange"
  scrape_interval_hours: 4
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `true` | Enable/disable Exchange scraping |
| `server` | `string` | `""` | EWS server URL, e.g. `https://mail.corp.ru/EWS/Exchange.asmx` |
| `email` | `string` | `""` | User email address (used as Keychain account) |
| `auth_mode` | `string` | `"auto"` | Authentication mode: `"auto"`, `"basic"`, or `"ntlm"` |
| `keychain_service` | `string` | `"the-jarvice.exchange"` | macOS Keychain service name for the password |
| `scrape_interval_hours` | `int` | `4` | Hours between scrapes (1–168) |

**`auth_mode` values:**

| Value | Description |
|-------|-------------|
| `"auto"` | Try Basic Auth first, fallback to NTLM |
| `"basic"` | Use HTTP Basic Authentication |
| `"ntlm"` | Use NTLM Authentication |

**Password storage:** The Exchange password is stored in macOS Keychain under the service `the-jarvice.exchange` with the account set to the user's email address. It is **never** written to `config.yaml`.

---

## `teams`

Microsoft Teams scraper settings.

```yaml
teams:
  enabled: true
  auth_mode: "ic3_token"
  keychain_service: "the-jarvice.teams"
  scrape_interval_hours: 4
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `true` | Enable/disable Teams scraping |
| `auth_mode` | `string` | `"ic3_token"` | Authentication mode: `"ic3_token"` (current) or `"graph_api"` (future) |
| `keychain_service` | `string` | `"the-jarvice.teams"` | macOS Keychain service name for the IC3 token |
| `scrape_interval_hours` | `int` | `4` | Hours between scrapes (1–168) |

**`auth_mode` values:**

| Value | Description |
|-------|-------------|
| `"ic3_token"` | IC3 token extracted from browser (current method) |
| `"graph_api"` | Microsoft Graph API (planned for v0.3.0) |

**Token storage:** The IC3 token is stored in macOS Keychain under the service `the-jarvice.teams` with account `ic3_token`. IC3 tokens expire approximately every 24 hours — use `the-jarvice configure --reauth teams` to refresh.

**Known limitation:** Playwright (~300MB) is required for Teams token refresh.

---

## `telegram`

Telegram bot delivery settings.

```yaml
telegram:
  enabled: true
  bot_token_keychain: "the-jarvice.telegram-bot"
  chat_id: ""
  keychain_service: "the-jarvice.telegram"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `true` | Enable/disable Telegram delivery |
| `bot_token_keychain` | `string` | `"the-jarvice.telegram-bot"` | Keychain service name for the bot token |
| `chat_id` | `string` | `""` | Telegram chat ID for message delivery |
| `keychain_service` | `string` | `"the-jarvice.telegram"` | Keychain service name for general Telegram credentials |

**Bot token:** Created via [@BotFather](https://t.me/BotFather) on Telegram. Stored in macOS Keychain under `the-jarvice.telegram-bot` with account `bot_token`.

**Chat ID:** The numeric chat ID where summaries are delivered. Obtain by sending `/start` to your bot and checking the `update` payload, or use `the-jarvice configure` which captures it automatically.

---

## `pii`

PII (Personally Identifiable Information) anonymization pipeline settings.

```yaml
pii:
  enabled: true
  red_dir: "~/.the-jarvice/data/pii/RED"
  green_dir: "~/.the-jarvice/data/pii/GREEN"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `true` | Enable/disable PII anonymization |
| `red_dir` | `string` | `"~/.the-jarvice/data/pii/RED"` | Directory for raw (PII-containing) data. **chmod 700** |
| `green_dir` | `string` | `"~/.the-jarvice/data/pii/GREEN"` | Directory for anonymized data |

**Security:** The `RED` directory contains raw, unanonymized data with PII. It is created with `chmod 700` permissions. The `GREEN` directory contains anonymized data safe for AI processing.

**Path expansion:** Tilde (`~`) is automatically expanded to the home directory.

---

## `models`

Ollama model settings for local LLM inference.

```yaml
models:
  primary: "qwen3:14b"
  fallback: "qwen2.5:7b"
  ollama_host: "http://localhost:11434"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `primary` | `string` | `"qwen3:14b"` | Primary model for summary generation (~9 GB) |
| `fallback` | `string` | `"qwen2.5:7b"` | Fallback model if primary is unavailable (~4.5 GB) |
| `ollama_host` | `string` | `"http://localhost:11434"` | Ollama API endpoint |

**Model sizes:**

| Model | Approx. Size | Quality | Speed |
|-------|-------------|---------|-------|
| `qwen3:14b` | ~9 GB | Best | Moderate |
| `qwen2.5:7b` | ~4.5 GB | Good | Fast |
| `qwen2.5:3b` | ~2 GB | Acceptable | Very fast |

**Disk space:** Ensure at least 12 GB free for the primary model download.

**Ollama host:** Change this if you're running Ollama on a different host or port. Can also be set via the `OLLAMA_HOST` environment variable.

---

## `schedule`

Summary delivery schedule.

```yaml
schedule:
  timezone: "Europe/Moscow"
  morning_summary: "07:00"
  evening_summary: "19:00"
  weekly_summary: "Mon 09:00"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timezone` | `string` | `"Europe/Moscow"` | IANA timezone for schedule times |
| `morning_summary` | `string` | `"07:00"` | Morning summary time (HH:MM format) |
| `evening_summary` | `string` | `"19:00"` | Evening summary time (HH:MM format) |
| `weekly_summary` | `string` | `"Mon 09:00"` | Weekly summary (Day HH:MM format) |

**Validation:** Time values must be in `HH:MM` format (24-hour). The `weekly_summary` uses three-letter day abbreviation (`Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`).

---

## `logging`

Application logging settings.

```yaml
logging:
  level: "INFO"
  dir: "~/.the-jarvice/logs"
  max_size_mb: 50
  rotation: "daily"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | `string` | `"INFO"` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `dir` | `string` | `"~/.the-jarvice/logs"` | Directory for log files |
| `max_size_mb` | `int` | `50` | Maximum log file size in MB (1–10000) |
| `rotation` | `string` | `"daily"` | Log rotation strategy: `"daily"` or `"size-based"` |

**`rotation` values:**

| Value | Description |
|-------|-------------|
| `"daily"` | Create a new log file each day |
| `"size-based"` | Rotate when file exceeds `max_size_mb` |

---

## State File

The Jarvice tracks scraper cursors in `~/.the-jarvice/state.json`:

```json
{
  "version": 1,
  "scrapers": {
    "exchange": {
      "last_scrape": "2026-05-21T14:30:00+03:00",
      "error_count": 0
    },
    "teams": {
      "last_scrape": "2026-05-21T14:30:00+03:00"
    }
  },
  "last_run": "2026-05-21T14:30:00+03:00"
}
```

This file is auto-managed. Do not edit it manually unless debugging.

## OpenClaw Config Generation

During `the-jarvice configure`, an `openclaw.json` file is generated at `~/.openclaw/openclaw.json` from the template at `the_jarvice/config/openclaw_template.json`. Values from `config.yaml` are substituted into `{{PLACEHOLDER}}` fields.

The generation can also be triggered programmatically:

```python
from the_jarvice.core.config import load_config, generate_openclaw_config

config = load_config()
generate_openclaw_config(config)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Override Ollama API endpoint | `http://localhost:11434` |

## Keychain Services

All credentials are stored in macOS Keychain via the Python `keyring` package:

| Service | Account | Purpose |
|---------|---------|---------|
| `the-jarvice.exchange` | User email | Exchange/EWS password |
| `the-jarvice.teams` | `ic3_token` | Teams IC3 auth token |
| `the-jarvice.telegram-bot` | `bot_token` | Telegram bot API token |
| `the-jarvice.telegram` | (varies) | Telegram chat ID |

**To view stored credentials:**

```bash
# macOS Keychain Access app → search "the-jarvice"

# Or via command line:
security find-generic-password -s "the-jarvice.exchange" -a "user@example.com" -w
```

**To delete a credential:**

```bash
security delete-generic-password -s "the-jarvice.exchange" -a "user@example.com"
```