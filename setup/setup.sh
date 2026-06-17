#!/usr/bin/env bash
# =============================================================================
# The Jarvice — Idempotent Installation Script v0.1.0
# =============================================================================
# Safe to run multiple times. Each step checks before acting.
# Requires: macOS 13+, internet connection for downloads.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

info()  { printf "${BLUE}ℹ️  %s${NC}\n" "$*"; }
ok()    { printf "${GREEN}✅ %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW}⚠️  %s${NC}\n" "$*"; }
err()   { printf "${RED}❌ %s${NC}\n" "$*" >&2; }
step()  { printf "\n${BOLD}── %s ──${NC}\n" "$*"; }

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
JARVICE_DIR="$HOME/.the-jarvice"
VENV_DIR="$JARVICE_DIR/venv"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_TEMPLATE="$REPO_DIR/the_jarvice/config/config_schema.yaml"
CONFIG_DEST="$JARVICE_DIR/config.yaml"
MIN_DISK_GB=12
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
REQUIRED_NODE_MAJOR=20

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
command_exists() {
    command -v "$1" &>/dev/null
}

version_gte() {
    # version_gte <actual> <required_major> <required_minor>
    local actual="$1"
    local req_major="$2"
    local req_minor="$3"
    local actual_major actual_minor
    actual_major="$(echo "$actual" | cut -d. -f1)"
    actual_minor="$(echo "$actual" | cut -d. -f2)"
    # Strip non-numeric suffixes
    actual_major="${actual_major%%[^0-9]*}"
    actual_minor="${actual_minor%%[^0-9]*}"
    [ "$actual_major" -gt "$req_major" ] && return 0
    [ "$actual_major" -eq "$req_major" ] && [ "$actual_minor" -ge "$req_minor" ] && return 0
    return 1
}

get_disk_free_gb() {
    df -g "$HOME" 2>/dev/null | awk 'NR==2 {print $4}' || echo "0"
}

# ---------------------------------------------------------------------------
# Step 1: Check OS
# ---------------------------------------------------------------------------
check_os() {
    step "Checking operating system"
    if [[ "$(uname)" != "Darwin" ]]; then
        err "The Jarvice v0.1.0 requires macOS. Detected: $(uname)"
        err "Linux support is planned for a future release."
        exit 1
    fi

    local macos_version
    macos_version="$(sw_vers -productVersion 2>/dev/null || echo "0")"
    local macos_major="${macos_version%%.*}"
    if [ "${macos_major:-0}" -lt 13 ]; then
        warn "macOS $(sw_vers -productVersion) detected. The Jarvice is tested on macOS 13+."
        warn "Some features may not work correctly."
    else
        ok "macOS $(sw_vers -productVersion)"
    fi
}

# ---------------------------------------------------------------------------
# Step 2: Check / Install Homebrew
# ---------------------------------------------------------------------------
check_homebrew() {
    step "Checking Homebrew"
    if command_exists brew; then
        ok "Homebrew found ($(brew --version 2>/dev/null | head -1))"
    else
        warn "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for Apple Silicon
        if [ -f /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        ok "Homebrew installed"
    fi
}

# ---------------------------------------------------------------------------
# Step 3: Check / Install Python 3.10+
# ---------------------------------------------------------------------------
check_python() {
    step "Checking Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+"
    local python_version=""
    local python_cmd=""

    if command_exists python3; then
        python_version="$(python3 --version 2>/dev/null | sed 's/Python //')"
        python_cmd="python3"
    fi

    if [ -z "$python_version" ] && command_exists python; then
        python_version="$(python --version 2>/dev/null | sed 's/Python //')"
        python_cmd="python"
    fi

    if [ -n "$python_version" ] && version_gte "$python_version" "$REQUIRED_PYTHON_MAJOR" "$REQUIRED_PYTHON_MINOR"; then
        ok "Python $python_version found ($python_cmd)"
    else
        if [ -n "$python_version" ]; then
            warn "Python $python_version found, but ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ is required"
        else
            warn "Python not found"
        fi
        info "Installing Python via Homebrew..."
        brew install python@3.12
        python_version="$(python3 --version 2>/dev/null | sed 's/Python //')"
        if version_gte "$python_version" "$REQUIRED_PYTHON_MAJOR" "$REQUIRED_PYTHON_MINOR"; then
            ok "Python $python_version installed"
        else
            err "Failed to install Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+"
            exit 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 4: Check / Install Node.js 20+
# ---------------------------------------------------------------------------
check_node() {
    step "Checking Node.js ${REQUIRED_NODE_MAJOR}+"
    local node_version=""

    if command_exists node; then
        node_version="$(node --version 2>/dev/null | sed 's/v//')"
        local node_major="${node_version%%.*}"
        if [ "$node_major" -ge "$REQUIRED_NODE_MAJOR" ]; then
            ok "Node.js $node_version found"
        else
            warn "Node.js $node_version found, but ${REQUIRED_NODE_MAJOR}+ is required"
            info "Installing Node.js via Homebrew..."
            brew install node
            ok "Node.js installed ($(node --version))"
        fi
    else
        warn "Node.js not found"
        info "Installing Node.js via Homebrew..."
        brew install node
        ok "Node.js installed ($(node --version))"
    fi
}

# ---------------------------------------------------------------------------
# Step 5: Check / Install Ollama
# ---------------------------------------------------------------------------
check_ollama() {
    step "Checking Ollama"
    if command_exists ollama; then
        ok "Ollama found ($(ollama --version 2>/dev/null || echo 'installed'))"
    else
        warn "Ollama not found. Installing via Homebrew..."
        brew install ollama
        ok "Ollama installed"
    fi

    # Check if Ollama service is running
    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
        ok "Ollama service is running"
    else
        warn "Ollama service not running. Starting..."
        ollama serve &>/dev/null &
        local retries=10
        while [ $retries -gt 0 ]; do
            if curl -sf http://localhost:11434/api/tags &>/dev/null; then
                ok "Ollama service started"
                break
            fi
            retries=$((retries - 1))
            sleep 1
        done
        if [ $retries -eq 0 ]; then
            warn "Could not start Ollama service. Please start it manually: ollama serve"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 6: Check disk space
# ---------------------------------------------------------------------------
check_disk_space() {
    step "Checking disk space (need ≥ ${MIN_DISK_GB}GB free)"
    local free_gb
    free_gb="$(get_disk_free_gb)"
    if [ "$free_gb" -ge "$MIN_DISK_GB" ]; then
        ok "${free_gb}GB free"
    else
        err "Only ${free_gb}GB free. Need at least ${MIN_DISK_GB}GB for model download."
        err "Free up disk space and re-run setup."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Step 7: Create venv and install dependencies
# ---------------------------------------------------------------------------
install_dependencies() {
    step "Setting up Python virtual environment"
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
        ok "Virtual environment exists at $VENV_DIR"
    else
        info "Creating virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        ok "Virtual environment created"
    fi

    # Activate venv for this script
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"

    step "Installing Python dependencies"
    if [ -f "$REPO_DIR/pyproject.toml" ]; then
        info "Installing from pyproject.toml..."
        pip install --upgrade pip --quiet 2>/dev/null
        pip install -e "$REPO_DIR" --quiet 2>&1 | tail -5
        ok "Python dependencies installed"
    else
        warn "pyproject.toml not found at $REPO_DIR/pyproject.toml"
        warn "Skipping Python package installation. Install manually later."
    fi
}

# ---------------------------------------------------------------------------
# Step 8: Download model if missing
# ---------------------------------------------------------------------------
check_model() {
    step "Checking AI model (qwen3:14b)"
    local model_name="qwen3:14b"

    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
        if ollama list 2>/dev/null | grep -q "$model_name"; then
            ok "Model $model_name is already downloaded"
        else
            info "Model $model_name not found. Downloading..."
            info "This may take a while (≈9GB download). Press Ctrl+C to skip."
            if ollama pull "$model_name"; then
                ok "Model $model_name downloaded successfully"
            else
                warn "Failed to download model. You can download it later: ollama pull $model_name"
            fi
        fi
    else
        warn "Ollama not running. Cannot check/download model."
        warn "After starting Ollama, run: ollama pull $model_name"
    fi
}

# ---------------------------------------------------------------------------
# Step 9: Create directory structure
# ---------------------------------------------------------------------------
create_directories() {
    step "Creating directory structure"
    local dirs=(
        "$JARVICE_DIR"
        "$JARVICE_DIR/config"
        "$JARVICE_DIR/data/exchange"
        "$JARVICE_DIR/data/teams"
        "$JARVICE_DIR/data/pii/RED"
        "$JARVICE_DIR/data/pii/GREEN"
        "$JARVICE_DIR/logs"
        "$JARVICE_DIR/memory"
        "$JARVICE_DIR/index"
    )

    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            ok "Directory exists: ${dir/#$HOME/~}"
        else
            mkdir -p "$dir"
            ok "Created: ${dir/#$HOME/~}"
        fi
    done

    # Secure PII directory
    chmod 700 "$JARVICE_DIR/data/pii"
    chmod 700 "$JARVICE_DIR/data/pii/RED"
    ok "PII directories secured (chmod 700)"
}

# ---------------------------------------------------------------------------
# Step 10: Copy config template
# ---------------------------------------------------------------------------
copy_config() {
    step "Setting up configuration"
    if [ -f "$CONFIG_DEST" ]; then
        ok "config.yaml already exists at ${CONFIG_DEST/#$HOME/~}"
        warn "Not overwriting. Edit manually if needed."
    else
        if [ -f "$CONFIG_TEMPLATE" ]; then
            cp "$CONFIG_TEMPLATE" "$CONFIG_DEST"
            ok "Config template copied to ${CONFIG_DEST/#$HOME/~}"
        else
            warn "Config template not found at $CONFIG_TEMPLATE"
            warn "Creating default config..."
            cat > "$CONFIG_DEST" << 'CONFIGEOF'
# The Jarvice Configuration — v1
# Edit this file to configure your instance.
# Run: the-jarvice configure  (for interactive setup)

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
  primary: "qwen3:14b"
  fallback: "qwen2.5:7b"
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
CONFIGEOF
            ok "Default config created at ${CONFIG_DEST/#$HOME/~}"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 11: Install CLI entry point
# ---------------------------------------------------------------------------
install_cli() {
    step "Installing CLI entry point"
    if [ -f "$VENV_DIR/bin/the-jarvice" ]; then
        ok "CLI command 'the-jarvice' is available"
    else
        if [ -f "$REPO_DIR/pyproject.toml" ]; then
            pip install -e "$REPO_DIR" --quiet 2>&1 | tail -3
            if [ -f "$VENV_DIR/bin/the-jarvice" ]; then
                ok "CLI command 'the-jarvice' installed"
            else
                warn "CLI entry point not found. You may need to reinstall the package."
            fi
        else
            warn "pyproject.toml not found. Skipping CLI installation."
        fi
    fi
}

# ---------------------------------------------------------------------------
# Welcome message
# ---------------------------------------------------------------------------
print_welcome() {
    echo ""
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║                                                          ║${NC}"
    echo -e "${BOLD}${GREEN}║          🤖  The Jarvice — Installation Complete!  🤖     ║${NC}"
    echo -e "${BOLD}${GREEN}║                                                          ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo ""
    echo -e "  ${BLUE}1.${NC} Configure your instance:"
    echo -e "     ${BOLD}source ~/.the-jarvice/venv/bin/activate${NC}"
    echo -e "     ${BOLD}the-jarvice configure${NC}"
    echo ""
    echo -e "  ${BLUE}2.${NC} Verify everything is set up:"
    echo -e "     ${BOLD}the-jarvice doctor${NC}"
    echo ""
    echo -e "  ${BLUE}3.${NC} Run your first summary:"
    echo -e "     ${BOLD}the-jarvice run --once${NC}"
    echo ""
    echo -e "  ${BLUE}4.${NC} View version info:"
    echo -e "     ${BOLD}the-jarvice version${NC}"
    echo ""
    echo -e "${YELLOW}Tip: Add to your shell profile for easy access:${NC}"
    echo -e "     ${BOLD}echo 'alias the-jarvice=~/.the-jarvice/venv/bin/the-jarvice' >> ~/.zshrc${NC}"
    echo ""
    echo -e "${BLUE}Docs: https://github.com/your-org/the-jarvice${NC}"
    echo -e "${BLUE}Support: Run 'the-jarvice doctor' for diagnostics${NC}"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo -e "${BOLD}${BLUE}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║            The Jarvice — Setup v0.1.0                   ║"
    echo "║          Local-first AI for corporate data              ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_os
    check_homebrew
    check_python
    check_node
    check_ollama
    check_disk_space
    install_dependencies
    check_model
    create_directories
    copy_config
    install_cli
    print_welcome
}

main "$@"