#!/usr/bin/env bash
# The Jarvice — Full System Setup Script
# Installs: OpenClaw + The Jarvice + Ollama + models + agent config
# Safe to run multiple times. Each step checks before acting.
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/negatix-creator/the-jarvice/main/setup.sh)
#   or: ./setup.sh
#   or: ./setup.sh --quick    (skip model downloads)
#   or: ./setup.sh --check    (diagnostic only, no changes)

set -uo pipefail
# Note: not using set -e to avoid breaking on non-critical failures

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

info()  { printf "${BLUE}ℹ️  %s${NC}\n" "$*"; }
ok()    { printf "${GREEN}✅ %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW}⚠️  %s${NC}\n" "$*"; }
err()   { printf "${RED}❌ %s${NC}\n" "$*" >&2; }
step()  { printf "\n${BOLD}── Step %s ──${NC}\n" "$*"; }

# Paths
JARVICE_DIR="$HOME/.the-jarvice"
VENV_DIR="$JARVICE_DIR/venv"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_WORKSPACE="$OPENCLAW_DIR/workspace"
GITHUB_REPO="https://github.com/negatix-creator/the-jarvice.git"

# Flags
QUICK_MODE=false
CHECK_MODE=false
for arg in "$@"; do
    case "$arg" in
        --quick|-q) QUICK_MODE=true ;;
        --check|-c|--dry-run) CHECK_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--quick] [--check]"
            echo "  --quick   Skip model downloads"
            echo "  --check   Diagnostic only, no changes"
            exit 0 ;;
    esac
done

echo ""
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo "${BOLD}  The Jarvice — Full System Setup 🤖${NC}"
echo "${BOLD}  OpenClaw + Jarvice + Ollama + Agent${NC}"
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo ""

if $CHECK_MODE; then
    echo "${YELLOW}  ⚠️  Check mode — no changes will be made${NC}"
    echo ""
fi

# ─── Step 1: System requirements ────────────────────────────────────────
step "1/13: System requirements"
if [[ "$(uname)" != "Darwin" ]]; then
    err "This script only supports macOS."
    exit 1
fi
ok "macOS $(sw_vers -productVersion)"

FREE_GB=$(df -g "$HOME" | tail -1 | awk '{print $4}')
if (( FREE_GB < 3 )); then
    err "Only ${FREE_GB}GB free (need 3GB minimum)"
    exit 1
fi
ok "${FREE_GB}GB free disk space"

# ─── Step 2: Homebrew ───────────────────────────────────────────────────
step "2/13: Homebrew"
if command -v brew &>/dev/null; then
    ok "Homebrew installed"
else
    if $CHECK_MODE; then err "Homebrew not found"; exit 1; fi
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zshrc"
    fi
    ok "Homebrew installed"
fi

# ─── Step 3: Python 3.10+ ────────────────────────────────────────────────
step "3/13: Python"
PYTHON_CMD=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYVER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || continue)
        PYMAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || continue)
        PYMINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || continue)
        if (( PYMAJOR >= 3 && PYMINOR >= 10 )); then
            PYTHON_CMD="$cmd"
            ok "Python $PYVER found ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    if $CHECK_MODE; then err "Python 3.10+ not found"; exit 1; fi
    info "Installing Python 3.12..."
    brew install python@3.12
    PYTHON_CMD="python3.12"
    ok "Python 3.12 installed"
fi

# ─── Step 4: Node.js ────────────────────────────────────────────────────
step "4/13: Node.js"
if command -v node &>/dev/null; then
    ok "Node.js $(node --version)"
else
    if $CHECK_MODE; then err "Node.js not found"; exit 1; fi
    info "Installing Node.js..."
    brew install node
    ok "Node.js installed"
fi

# ─── Step 5: OpenClaw ───────────────────────────────────────────────────
step "5/13: OpenClaw"
if command -v openclaw &>/dev/null; then
    ok "OpenClaw $(openclaw --version 2>/dev/null || echo 'installed')"
else
    if $CHECK_MODE; then err "OpenClaw not found"; exit 1; fi
    info "Installing OpenClaw..."
    npm install -g openclaw
    ok "OpenClaw installed"
fi

# ─── Step 6: Ollama ──────────────────────────────────────────────────────
step "6/13: Ollama"
if command -v ollama &>/dev/null; then
    ok "Ollama installed"
else
    if $CHECK_MODE; then warn "Ollama not found"; exit 1; fi
    info "Installing Ollama..."
    brew install ollama
    ok "Ollama installed"
fi

# Start Ollama if not running
if ! pgrep -x "ollama" &>/dev/null; then
    if ! $CHECK_MODE; then
        info "Starting Ollama..."
        if [ -d "/Applications/Ollama.app" ]; then
            open -a Ollama 2>/dev/null || true
        fi
        ollama serve &>/dev/null || true &
        # Wait for Ollama to be ready (up to 15 seconds)
        for i in 1 2 3 4 5 6 7 8; do
            curl -sf http://localhost:11434/api/tags &>/dev/null && break
            sleep 2
        done
        if curl -sf http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama is running"
        else
            warn "Ollama may need manual start: open -a Ollama"
        fi
    fi
fi

# ─── Step 7: AI Models ──────────────────────────────────────────────────
step "7/13: AI Models"
OLLAMA_READY=false
curl -sf http://localhost:11434/api/tags &>/dev/null && OLLAMA_READY=true

if [ "$OLLAMA_READY" = true ]; then
    MODEL="${JARVICE_MODEL:-glm-5.1:cloud}"
    EMBED_MODEL="nomic-embed-text:latest"

    # Primary model
    if ollama list 2>/dev/null | grep -q "$(echo $MODEL | cut -d: -f1)"; then
        ok "Model $MODEL available"
    else
        if $QUICK_MODE || $CHECK_MODE; then
            warn "Model $MODEL not downloaded. Run: ollama pull $MODEL"
        else
            info "Downloading $MODEL..."
            if ollama pull "$MODEL" 2>&1; then
                ok "Model $MODEL downloaded"
            else
                warn "Cloud model failed — downloading local fallback qwen3:14b (8.6 GB)..."
                if ollama pull "qwen3:14b" 2>&1; then
                    ok "Local model qwen3:14b downloaded"
                else
                    err "Failed to download any model. Continue without model."
                fi
            fi
        fi
    fi

    # Embeddings model
    if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
        ok "Embeddings model available"
    else
        if $QUICK_MODE || $CHECK_MODE; then
            warn "Embeddings model not downloaded. Run: ollama pull $EMBED_MODEL"
        else
            info "Downloading embeddings model (274 MB)..."
            ollama pull "$EMBED_MODEL" 2>&1 && ok "Embeddings model downloaded" || \
                warn "Embeddings failed — memory search may not work"
        fi
    fi
else
    warn "Ollama not running — skipping models. Start Ollama and run: ollama pull glm-5.1:cloud nomic-embed-text:latest"
fi

# ─── Step 8: Ollama Cloud Auth ──────────────────────────────────────────
step "8/13: Ollama Cloud Auth"
# Public cloud models (glm-5.1:cloud, deepseek-v4-pro:cloud, etc.)
# work without signin. Only prompt signin if models fail.
if [ "$OLLAMA_READY" = true ]; then
    # Quick test: can we use a cloud model?
    CLOUD_TEST=$(curl -sf --max-time 20 http://localhost:11434/api/generate \
        -d '{"model":"glm-5.1:cloud","prompt":"hi","stream":false}' 2>/dev/null || echo "")
    if [ -n "$CLOUD_TEST" ]; then
        ok "Ollama cloud models working (no signin needed)"
    else
        echo ""
        echo "  ${BOLD}${YELLOW}⚡ Cloud models need authentication${NC}"
        echo ""
        echo "  Run: ${BOLD}ollama signin${NC}"
        echo "  This opens a browser to sign in to ollama.com (free)."
        echo ""
        if ! $CHECK_MODE && ! $QUICK_MODE; then
            read -p "  Press Enter to open browser for Ollama signin, or 's' to skip: " SIGNIN_CHOICE
            if [ "$SIGNIN_CHOICE" != "s" ]; then
                ollama signin 2>/dev/null || warn "Signin failed — run 'ollama signin' manually"
            fi
        fi
    fi
fi

# ─── Step 9: The Jarvice ────────────────────────────────────────────────
step "9/13: The Jarvice"
if $CHECK_MODE; then
    warn "Skipping Jarvice install in check mode"
else
    mkdir -p "$JARVICE_DIR"

    # Create venv with the Python we found
    if [ ! -d "$VENV_DIR/bin" ]; then
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        ok "Python venv created with $PYTHON_CMD"
    fi

    # Activate venv
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || {
            err "Venv broken — removing and recreating..."
            rm -rf "$VENV_DIR"
            "$PYTHON_CMD" -m venv "$VENV_DIR"
            source "$VENV_DIR/bin/activate"
        }
    else
        err "Venv not found at $VENV_DIR"
        exit 1
    fi

    pip install --upgrade pip --quiet 2>/dev/null || true

    # Clone and install
    CLONE_DIR="$JARVICE_DIR/src/the-jarvice"
    if [ -d "$CLONE_DIR" ] && [ -f "$CLONE_DIR/pyproject.toml" ]; then
        cd "$CLONE_DIR"
        git pull --ff-only 2>/dev/null || git pull 2>/dev/null || true
    else
        info "Cloning from GitHub..."
        mkdir -p "$JARVICE_DIR/src"
        git clone "$GITHUB_REPO" "$CLONE_DIR" --depth 1
        cd "$CLONE_DIR"
    fi

    if [ -f "pyproject.toml" ]; then
        pip install . --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null
        ok "the-jarvice installed"
    else
        err "Could not find Jarvice source at $CLONE_DIR"
    fi

    cd "$HOME"

    # Add venv to PATH
    SHELL_RC="$HOME/.zshrc"
    if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi
    if ! grep -q ".the-jarvice/venv/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# The Jarvice" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.the-jarvice/venv/bin:$PATH"' >> "$SHELL_RC"
        ok "PATH updated in $SHELL_RC"
    else
        ok "PATH already configured"
    fi
    export PATH="$VENV_DIR/bin:$PATH"
fi

# ─── Step 10: OpenClaw Setup ────────────────────────────────────────────
step "10/13: OpenClaw Setup"
if $CHECK_MODE; then
    warn "Skipping OpenClaw setup in check mode"
else
    mkdir -p "$OPENCLAW_WORKSPACE"
    mkdir -p "$OPENCLAW_WORKSPACE/memory"

    # Create workspace files for the agent
    if [ ! -f "$OPENCLAW_WORKSPACE/AGENTS.md" ]; then
        cat > "$OPENCLAW_WORKSPACE/AGENTS.md" << 'AGENTSEOF'
# AGENTS.md — The Jarvice

## Роль

Ты — корпоративный ассистент. Собираешь данные, генерируешь сводки, доставляешь в Telegram.

## Зона ответственности

- Сбор данных из Exchange (email, calendar) и Teams
- PII-обезличивание перед отправкой в LLM
- Генерация сводок по расписанию (утром, вечером)
- Доставка сводок в Telegram
- Мониторинг здоровья системы

## Память — правила

- Каждый день — дамп в `memory/YYYY-MM-DD.md` (APPEND)
- Пароли → Keychain, не в .md
- Конкретные имена и термины в заголовках

## Алерты

- 🔴 CRITICAL → сразу писать владельцу
- 🟡 WARNING → логировать + писать если повторяется
- 🟢 INFO → только в лог
AGENTSEOF
        ok "Created AGENTS.md"
    fi

    if [ ! -f "$OPENCLAW_WORKSPACE/SOUL.md" ]; then
        cat > "$OPENCLAW_WORKSPACE/SOUL.md" << 'SOULEOF'
# SOUL.md — The Jarvice

## Кто я

Корпоративный ассистент — собираю данные, генерирую сводки, помогаю с информацией.

## Стиль

- Технически точный и лаконичный
- Сводки — структурированные, с заголовками
- Без воды, только суть
- На русском по умолчанию

## Язык

Русский по умолчанию. Технические термины как есть.
SOULEOF
        ok "Created SOUL.md"
    fi

    if [ ! -f "$OPENCLAW_WORKSPACE/MEMORY.md" ]; then
        cat > "$OPENCLAW_WORKSPACE/MEMORY.md" << 'MEMEOF'
# MEMORY.md — The Jarvice

## System Info

- OS: macOS
- Python: 3.12+
- OpenClaw: installed
- The Jarvice: installed
- Models: glm-5.1:cloud (primary), nomic-embed-text (embeddings)
MEMEOF
        ok "Created MEMORY.md"
    fi

    # Create Jarvice config with cloud models
    if [ ! -f "$JARVICE_DIR/config.yaml" ]; then
        cat > "$JARVICE_DIR/config.yaml" << 'CFGEOF'
# The Jarvice Configuration — v1
# Generated by setup.sh

version: 1

exchange:
  enabled: true
  server: ""
  email: ""
  auth_mode: "auto"
  keychain_service: "the-jarvice.exchange"
  scrape_interval_hours: 4

teams:
  enabled: true
  auth_mode: "ic3_token"
  keychain_service: "the-jarvice.teams"
  scrape_interval_hours: 4

telegram:
  enabled: true
  bot_token_keychain: "the-jarvice.telegram-bot"
  chat_id: ""
  keychain_service: "the-jarvice.telegram"

pii:
  enabled: true
  red_dir: "~/.the-jarvice/data/pii/RED"
  green_dir: "~/.the-jarvice/data/pii/GREEN"

models:
  primary: "glm-5.1:cloud"
  fallback: "qwen2.5:7b"
  embeddings: "nomic-embed-text"
  ollama_host: "http://localhost:11434"

schedule:
  timezone: "Europe/Moscow"
  morning_summary: "07:00"
  evening_summary: "19:00"
  weekly_summary: "Mon 09:00"

logging:
  level: "INFO"
  dir: "~/.the-jarvice/logs"
  max_size_mb: 50
  rotation: "daily"
CFGEOF
        ok "Created config.yaml with cloud models"
    else
        ok "config.yaml already exists"
    fi
fi

# ─── Step 11: Credentials ────────────────────────────────────────────────
step "11/13: Credentials"
echo ""
echo "  ${BOLD}Now let's connect your services.${NC}"
echo "  ${DIM}Press Enter to skip any step.${NC}"
echo ""

if ! $CHECK_MODE && ! $QUICK_MODE; then
    # ── Telegram Bot Token ──────────────────────────────────────────────
    echo "  ${BOLD}1/3 Telegram Bot Token${NC}"
    echo "  1. Open t.me/BotFather"
    echo "  2. Send /newbot"
    echo "  3. Choose a name (e.g. 'My Corp Assistant')"
    echo "  4. Choose a username (e.g. 'my_corp_assistant_bot')"
    echo "  5. Copy the token (looks like: 7123456789:AA...)"
    echo ""
    read -p "  Telegram bot token: " TG_TOKEN
    if [ -n "$TG_TOKEN" ]; then
        # Store in macOS Keychain
        security add-generic-password -U -s "the-jarvice.telegram-bot" -a "bot-token" -w "$TG_TOKEN" 2>/dev/null && \
            ok "Telegram bot token saved to Keychain" || \
            { echo "$TG_TOKEN" > "$JARVICE_DIR/.telegram-token"; chmod 600 "$JARVICE_DIR/.telegram-token"; ok "Telegram bot token saved to file"; }
    else
        info "Skipped — run 'the-jarvice configure --quick' later"
    fi

    # ── Exchange credentials (optional) ─────────────────────────────────
    echo ""
    echo "  ${BOLD}2/3 Exchange credentials${NC} (optional — for email/calendar summaries)"
    echo "  ${DIM}Skip if you don't use corporate Exchange${NC}"
    echo ""
    read -p "  Exchange email (or Enter to skip): " EX_EMAIL
    if [ -n "$EX_EMAIL" ]; then
        read -s -p "  Exchange password (hidden): " EX_PASS
        echo ""
        if [ -n "$EX_PASS" ]; then
            security add-generic-password -U -s "the-jarvice.exchange" -a "$EX_EMAIL" -w "$EX_PASS" 2>/dev/null && \
                ok "Exchange credentials saved to Keychain" || \
                warn "Could not save to Keychain — run 'the-jarvice configure --quick' later"
        fi
    else
        info "Skipped — run 'the-jarvice configure --quick' later"
    fi

    # ── OpenClaw Telegram channel ───────────────────────────────────────
    echo ""
    echo "  ${BOLD}3/3 Connect Telegram bot to OpenClaw${NC}"
    echo "  This links your bot to the agent system."
    echo ""
    if [ -n "${TG_TOKEN:-}" ]; then
        info "Adding Telegram channel to OpenClaw..."
        # openclaw channels add is interactive — we set the token in config
        openclaw channels add telegram --token "$TG_TOKEN" 2>/dev/null && ok "Telegram channel added" || {
            echo ""
            echo "  ${YELLOW}Automatic setup failed. Set up manually:${NC}"
            echo "  1. Run: ${BOLD}openclaw channels add${NC}"
            echo "  2. Choose Telegram"
            echo "  3. Enter bot token: ${DIM}$TG_TOKEN${NC}"
        }
    else
        echo "  After creating a bot token, run:"
        echo "    ${BOLD}openclaw channels add${NC}"
        echo "    ${BOLD}the-jarvice configure --quick${NC}"
    fi
fi

# ─── Step 12: Data directories ───────────────────────────────────────────
step "12/13: Data directories"
if ! $CHECK_MODE; then
    RED_DIR="$JARVICE_DIR/data/pii/RED"
    GREEN_DIR="$JARVICE_DIR/data/pii/GREEN"
    LOG_DIR="$JARVICE_DIR/logs"

    for dir in "$RED_DIR" "$GREEN_DIR" "$LOG_DIR"; do
        mkdir -p "$dir"
    done
    chmod 700 "$RED_DIR"
    ok "Data directories created (PII RED: chmod 700)"
fi

# ─── Step 13: Start Gateway ─────────────────────────────────────────────
step "13/13: Start Gateway"
if ! $CHECK_MODE; then
    # Check if gateway is already running
    if curl -sf http://localhost:19000/health &>/dev/null; then
        ok "OpenClaw Gateway is already running"
    else
        info "Starting OpenClaw Gateway..."
        openclaw gateway run &>/dev/null &
        sleep 3
        if curl -sf http://localhost:19000/health &>/dev/null; then
            ok "Gateway started"
        else
            warn "Gateway may need manual start: openclaw gateway run"
        fi
    fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo "${GREEN}${BOLD}  ✅ Setup Complete!${NC}"
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo ""

# Health check
ISSUES=0

if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    echo "  ${YELLOW}⚠️  Ollama not running — start: open -a Ollama${NC}"
    ISSUES=$((ISSUES + 1))
fi

if ! command -v the-jarvice &>/dev/null && [ ! -f "$VENV_DIR/bin/the-jarvice" ]; then
    echo "  ${YELLOW}⚠️  the-jarvice not in PATH — restart Terminal or: source ~/.zshrc${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -f "$JARVICE_DIR/config.yaml" ]; then
    echo "  ${YELLOW}⚠️  config.yaml not found — run: the-jarvice configure --quick${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$ISSUES" -eq 0 ]; then
    echo "  ${GREEN}All systems ready! 🎉${NC}"
else
    echo ""
    echo "  ${YELLOW}${ISSUES} issue(s) found — see above${NC}"
fi

echo ""
echo "  ${BOLD}Installed:${NC}"
echo "    ✅ OpenClaw (agent framework + gateway)"
echo "    ✅ The Jarvice (data pipeline + summaries)"
echo "    ✅ Ollama + models (glm-5.1:cloud, nomic-embed-text)"
echo "    ✅ Python venv + PATH"
echo "    ✅ PII directories (RED/GREEN)"
echo "    ✅ Config with cloud models"
echo ""

# Show what needs manual action
echo "  ${BOLD}Next steps:${NC}"
echo ""

if [ -z "${TG_TOKEN:-}" ]; then
    echo "  1. ${BOLD}Create Telegram bot:${NC}"
    echo "     Open t.me/BotFather → /newbot → copy token"
    echo "     Then: ${BOLD}openclaw channels add${NC}"
    echo "     Then: ${BOLD}the-jarvice configure --quick${NC}"
    echo ""
fi

if [ -z "${EX_EMAIL:-}" ]; then
    echo "  2. ${BOLD}Exchange credentials${NC} (optional):"
    echo "     ${BOLD}the-jarvice configure --quick${NC}"
    echo ""
fi

echo "  ${BOLD}Verify everything:${NC}"
echo "    the-jarvice doctor"
echo "    openclaw status"
echo ""
echo "  ${BOLD}First run:${NC}"
echo "    the-jarvice run --once"
echo ""
echo "  ${BOLD}Schedule summaries:${NC}"
echo "    the-jarvice enable"
echo ""
echo "  ${BOLD}Start gateway (if not running):${NC}"
echo "    openclaw gateway run"
echo ""
echo "  ${DIM}Config:    ~/.the-jarvice/config.yaml${NC}"
echo "  ${DIM}OpenClaw:  ~/.openclaw/${NC}"
echo "  ${DIM}Docs:      https://github.com/negatix-creator/the-jarvice${NC}"
echo ""