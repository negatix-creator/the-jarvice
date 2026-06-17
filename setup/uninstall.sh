#!/usr/bin/env bash
# =============================================================================
# The Jarvice — Uninstall Script v0.1.0
# =============================================================================
# Removes The Jarvice from this machine.
# Options:
#   --keep-config    Preserve config.yaml and data directory
#   --force          Skip confirmation prompt
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
NC='\033[0m'

info()  { printf "${BLUE}ℹ️  %s${NC}\n" "$*"; }
ok()    { printf "${GREEN}✅ %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW}⚠️  %s${NC}\n" "$*"; }
err()   { printf "${RED}❌ %s${NC}\n" "$*" >&2; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
KEEP_CONFIG=false
FORCE=false
JARVICE_DIR="$HOME/.the-jarvice"
VENV_DIR="$JARVICE_DIR/venv"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep-config)
            KEEP_CONFIG=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: uninstall.sh [--keep-config] [--force]"
            echo ""
            echo "Options:"
            echo "  --keep-config    Keep config.yaml and data directory"
            echo "  --force          Skip confirmation prompt"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            err "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------
if [ "$FORCE" = false ]; then
    echo -e "${BOLD}${YELLOW}⚠️  This will remove The Jarvice from your machine.${NC}"
    echo ""
    echo "The following will be removed:"
    echo "  • Virtual environment (~/.the-jarvice/venv/)"
    echo "  • Python packages"
    echo "  • Keyring entries (the-jarvice.*)"
    echo "  • Cron jobs"
    if [ "$KEEP_CONFIG" = false ]; then
        echo "  • Configuration (~/.the-jarvice/config.yaml)"
        echo "  • Data directory (~/.the-jarvice/data/)"
        echo "  • Memory directory (~/.the-jarvice/memory/)"
        echo "  • Logs (~/.the-jarvice/logs/)"
        echo "  • State file (~/.the-jarvice/state.json)"
    else
        echo -e "  ${GREEN}• Keeping: config.yaml and data/${NC}"
    fi
    echo ""
    read -rp "Remove The Jarvice? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Uninstall cancelled."
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Remove keyring entries
# ---------------------------------------------------------------------------
info "Removing keyring entries..."

# Try Python keyring first
if command -v python3 &>/dev/null && [ -d "$VENV_DIR" ]; then
    # shellcheck source=/dev/null
    if source "$VENV_DIR/bin/activate" 2>/dev/null; then
        python3 -c "
import keyring
prefix = 'the-jarvice'
removed = 0
known_services = [
    'the-jarvice.exchange',
    'the-jarvice.teams',
    'the-jarvice.telegram',
    'the-jarvice.telegram-bot',
]
for service in known_services:
    try:
        cred = keyring.get_credential(service, None)
        if cred:
            keyring.delete_password(service, cred.username)
            removed += 1
            print(f'  Removed: {service}/{cred.username}')
        else:
            for username in ['', 'password', 'token', 'default']:
                try:
                    keyring.delete_password(service, username)
                    removed += 1
                    print(f'  Removed: {service}/{username}')
                except keyring.errors.PasswordDeleteError:
                    pass
    except Exception as e:
        print(f'  Skipped: {service} ({e})')
print(f'Removed {removed} keyring entries')
" 2>/dev/null && ok "Keyring entries removed" || warn "Some keyring entries could not be removed"
        deactivate 2>/dev/null || true
    fi
else
    # Fallback: use macOS security command
    info "Using macOS Keychain to remove entries..."
    for service in "the-jarvice.exchange" "the-jarvice.teams" "the-jarvice.telegram" "the-jarvice.telegram-bot"; do
        if security delete-generic-password -s "$service" &>/dev/null; then
            ok "Removed Keychain entry: $service"
        else
            info "No Keychain entry for: $service"
        fi
    done
fi

# ---------------------------------------------------------------------------
# Remove cron jobs
# ---------------------------------------------------------------------------
info "Checking for cron jobs..."
CRON_TEMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "the-jarvice" > "$CRON_TEMP" 2>/dev/null || true
if crontab "$CRON_TEMP" 2>/dev/null; then
    ok "Cron jobs removed"
else
    info "No the-jarvice cron jobs found"
fi
rm -f "$CRON_TEMP"

# ---------------------------------------------------------------------------
# Remove data and config (unless --keep-config)
# ---------------------------------------------------------------------------
if [ "$KEEP_CONFIG" = true ]; then
    info "Preserving config.yaml and data (per --keep-config)"

    # Remove venv
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        ok "Virtual environment removed"
    fi

    # Remove logs
    if [ -d "$JARVICE_DIR/logs" ]; then
        rm -rf "$JARVICE_DIR/logs"
        ok "Logs removed"
    fi

    # Remove index
    if [ -d "$JARVICE_DIR/index" ]; then
        rm -rf "$JARVICE_DIR/index"
        ok "Index removed"
    fi

    # Remove state
    if [ -f "$JARVICE_DIR/state.json" ]; then
        rm -f "$JARVICE_DIR/state.json"
        ok "State file removed"
    fi

else
    # Remove everything
    if [ -d "$JARVICE_DIR" ]; then
        rm -rf "$JARVICE_DIR"
        ok "Directory ~/.the-jarvice/ removed"
    else
        info "Directory ~/.the-jarvice/ not found (already removed)"
    fi
fi

# ---------------------------------------------------------------------------
# Remove shell alias (if we can find it)
# ---------------------------------------------------------------------------
ALIAS_CHECK_FILES=("$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile")
for rc_file in "${ALIAS_CHECK_FILES[@]}"; do
    if [ -f "$rc_file" ] && grep -q "the-jarvice" "$rc_file" 2>/dev/null; then
        info "Found the-jarvice reference in $rc_file"
        info "You may want to remove it manually."
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          🤖  The Jarvice has been removed.  🤖            ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$KEEP_CONFIG" = true ]; then
    echo -e "${YELLOW}Note: Config and data were preserved at ~/.the-jarvice/${NC}"
    echo -e "${YELLOW}Remove manually if desired: rm -rf ~/.the-jarvice/${NC}"
fi

echo -e "${BLUE}To reinstall: git clone <repo> && cd the-jarvice && ./setup/setup.sh${NC}"
echo ""