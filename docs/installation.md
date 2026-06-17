# Installation Guide

This guide walks you through installing The Jarvice on macOS from scratch.

## Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| **macOS** | 13+ (Ventura) | Primary target for v0.1.0 |
| **Python** | 3.10+ | Installed automatically by `setup.sh` |
| **Node.js** | 20+ | Installed automatically by `setup.sh` |
| **Ollama** | Latest | Installed automatically by `setup.sh` |
| **Homebrew** | Latest | Installed automatically by `setup.sh` |
| **Disk space** | 12 GB free | For model download (~9 GB) + data |
| **Internet** | Required | For dependency downloads and model pull |

> **Note:** The setup script handles most prerequisites automatically. You only need a Mac with macOS 13+ and internet access.

## Quick Install

```bash
git clone <repo-url>
cd the-jarvice
./setup/setup.sh
```

Then follow the on-screen instructions.

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repo-url>
cd the-jarvice
```

### 2. Run the Setup Script

```bash
./setup/setup.sh
```

The script is **idempotent** — safe to run multiple times. It will:

1. **Check OS** — Verifies macOS (required for v0.1.0)
2. **Install Homebrew** — If not present
3. **Install Python 3.10+** — Via Homebrew if needed
4. **Install Node.js 20+** — Via Homebrew if needed
5. **Install Ollama** — Via Homebrew if needed, then starts the service
6. **Check disk space** — Ensures ≥ 12 GB free (exits with error if insufficient)
7. **Create virtual environment** — At `~/.the-jarvice/venv/`
8. **Install Python dependencies** — `pip install -e .` from `pyproject.toml`
9. **Download AI model** — `ollama pull qwen3:14b` (~9 GB, with progress feedback)
10. **Create directory structure** — `~/.the-jarvice/` with subdirectories
11. **Set up config template** — Copies `config_schema.yaml` or generates default
12. **Install CLI entry point** — `the-jarvice` command

### 3. Activate the Virtual Environment

```bash
source ~/.the-jarvice/venv/bin/activate
```

**Tip:** Add this to your shell profile for convenience:

```bash
echo 'alias the-jarvice=~/.the-jarvice/venv/bin/the-jarvice' >> ~/.zshrc
source ~/.zshrc
```

### 4. Configure

```bash
the-jarvice configure
```

The interactive wizard will guide you through:

1. **Exchange** — Server URL, email, password (stored in Keychain)
2. **Teams** — IC3 token (stored in Keychain)
3. **Telegram** — Bot token and chat ID (stored in Keychain)
4. **AI Model** — Checks/downloads the Ollama model
5. **Schedule** — Timezone, morning/evening summary times

Each step validates connectivity before proceeding.

To skip a component:

```bash
the-jarvice configure --skip-exchange    # Skip Exchange
the-jarvice configure --skip-teams       # Skip Teams
the-jarvice configure --skip-telegram    # Skip Telegram
the-jarvice configure --skip-model      # Skip model download
```

To re-configure a single service:

```bash
the-jarvice configure --reauth exchange
the-jarvice configure --reauth teams
the-jarvice configure --reauth telegram
the-jarvice configure --reauth model
```

### 5. Verify

```bash
the-jarvice doctor
```

This checks all 10 components and reports status:

```
✅ Python 3.14.0
✅ Ollama running (localhost:11434)
✅ Model qwen3:14b downloaded (9.3 GB)
✅ Keyring accessible (macOS Keychain)
✅ Config valid (~/.the-jarvice/config.yaml)
✅ Exchange connected (mail.corp.ru, 23 folders)
✅ Teams token present
✅ Telegram bot connected (@jarvice_bot)
✅ Disk space (142 GB free)
✅ OpenClaw running (v2026.4.5)

✅ All 10 checks passed!
```

For detailed output:

```bash
the-jarvice doctor --verbose
```

For machine-readable JSON:

```bash
the-jarvice doctor --json
```

### 6. Run Your First Summary

```bash
the-jarvice run --once
```

With verbose output:

```bash
the-jarvice run --once --verbose
```

Without sending to Telegram (dry run):

```bash
the-jarvice run --once --dry-run
```

## Directory Structure

After installation, the following directories are created:

```
~/.the-jarvice/
├── config.yaml          # Main configuration (single source of truth)
├── state.json           # Cursor state (generated on first run)
├── venv/                # Python virtual environment
├── config/              # Config templates
├── data/
│   ├── exchange/        # Exchange scraper data
│   ├── teams/           # Teams scraper data
│   └── pii/
│       ├── RED/         # Raw PII data (chmod 700)
│       └── GREEN/       # Anonymized data
├── logs/                # Application logs
├── memory/              # AI context memory files
└── index/               # Search index
```

## Troubleshooting

### Ollama not running

```bash
# Start Ollama manually
ollama serve

# Or let the-jarvice doctor --fix attempt to start it
the-jarvice doctor --fix
```

### Model not downloaded

```bash
# Download manually
ollama pull qwen3:14b

# Check installed models
ollama list
```

### Keyring / Keychain issues

The Jarvice uses macOS Keychain via the Python `keyring` package. If you see errors:

```bash
# Test keyring access
python3 -c "import keyring; keyring.set_password('test', 'test', 'ok'); print(keyring.get_password('test', 'test'))"

# If that fails, check Keychain access in System Preferences > Privacy & Security
```

### Exchange connection fails

- Verify your EWS server URL (e.g., `https://mail.corp.ru/EWS/Exchange.asmx`)
- Check that Basic Auth or NTLM is enabled on your Exchange server
- OAuth (Microsoft 365) is not yet supported — planned for v0.3.0

### Teams token expired

IC3 tokens expire approximately every 24 hours. Re-authenticate:

```bash
the-jarvice configure --reauth teams
```

### Disk space insufficient

The AI model requires ~9 GB. Free up space or change the model:

```yaml
# In ~/.the-jarvice/config.yaml
models:
  primary: "qwen2.5:7b"   # Smaller model (~4.5 GB)
  fallback: "qwen2.5:3b"  # Even smaller
```

### Python version issues

```bash
# Check your Python version
python3 --version

# If below 3.10, install via Homebrew
brew install python@3.12
```

### Setup script fails

- Ensure you have internet access
- Check that Homebrew is working: `brew doctor`
- Make sure the script is executable: `chmod +x setup/setup.sh`
- Run with verbose output: `bash -x setup/setup.sh`

### Config validation errors

```bash
# Validate your config manually
python3 -c "from the_jarvice.core.config import load_config; c = load_config(); print('Valid!')"

# Reset to defaults
rm ~/.the-jarvice/config.yaml
the-jarvice configure
```

## Uninstalling

```bash
# Via CLI (interactive)
the-jarvice uninstall

# Via CLI (keep config and data)
the-jarvice uninstall --keep-config

# Via script
./setup/uninstall.sh

# Via script (no prompts, keep config)
./setup/uninstall.sh --keep-config --force
```

Uninstall removes:
- Keyring entries (`the-jarvice.*`)
- Cron jobs referencing `the-jarvice`
- Data directory (`~/.the-jarvice/`) unless `--keep-config`
- Virtual environment
- OpenClaw config (only if generated by The Jarvice)

With `--keep-config`, it preserves `config.yaml` and `data/` but removes `state.json`, `logs/`, `index/`, and `venv/`.