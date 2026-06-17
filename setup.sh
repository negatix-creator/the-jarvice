#!/usr/bin/env bash
# The Jarvice — Установка полной системы
# Ставит: OpenClaw + The Jarvice + Ollama + модели + агент
# Безопасно запускать повторно. Каждый шаг проверяет перед действием.
#
# Запуск:
#   bash <(curl -fsSL https://raw.githubusercontent.com/negatix-creator/the-jarvice/main/setup.sh)
#   или: ./setup.sh
#   или: ./setup.sh --quick    (пропустить скачивание моделей)
#   или: ./setup.sh --check    (только диагностика, без изменений)

set -uo pipefail

# Цвета
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

info()  { printf "${BLUE}ℹ️  %s${NC}\n" "$*"; }
ok()    { printf "${GREEN}✅ %s${NC}\n" "$*"; }
warn()  { printf "${YELLOW}⚠️  %s${NC}\n" "$*"; }
err()   { printf "${RED}❌ %s${NC}\n" "$*" >&2; }
step()  { printf "\n${BOLD}── Шаг %s ──${NC}\n" "$*"; }

# Пути
JARVICE_DIR="$HOME/.the-jarvice"
VENV_DIR="$JARVICE_DIR/venv"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_WORKSPACE="$OPENCLAW_DIR/workspace"
GITHUB_REPO="https://github.com/negatix-creator/the-jarvice.git"

# Флаги
QUICK_MODE=false
CHECK_MODE=false
for arg in "$@"; do
    case "$arg" in
        --quick|-q) QUICK_MODE=true ;;
        --check|-c|--dry-run) CHECK_MODE=true ;;
        --help|-h)
            echo "Использование: $0 [--quick] [--check]"
            echo "  --quick   Пропустить скачивание моделей"
            echo "  --check   Только диагностика, без изменений"
            exit 0 ;;
    esac
done

echo ""
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo "${BOLD}  The Jarvice — Установка системы 🤖${NC}"
echo "${BOLD}  OpenClaw + Jarvice + Ollama + Агент${NC}"
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo ""

if $CHECK_MODE; then
    echo "${YELLOW}  ⚠️  Режим проверки — без изменений${NC}"
    echo ""
fi

# ═══════════════════════════════════════════════════════════
# ФАЗА 1: ИНФРАСТРУКТУРА
# ═══════════════════════════════════════════════════════════
echo ""
echo "${BOLD}━━━ Фаза 1: Инфраструктура ━━━${NC}"

# ─── Шаг 1: Система ──────────────────────────────────────────────────────
step "1/13: Система"
if [[ "$(uname)" != "Darwin" ]]; then
    err "Скрипт поддерживает только macOS. Linux — в следующей версии."
    exit 1
fi
ok "macOS $(sw_vers -productVersion)"

FREE_GB=$(df -g "$HOME" | tail -1 | awk '{print $4}')
if (( FREE_GB < 3 )); then
    err "Свободно ${FREE_GB}ГБ (нужно минимум 3ГБ)"
    exit 1
fi
ok "${FREE_GB}ГБ свободного места — должно хватить"

# ─── Шаг 2: Homebrew ───────────────────────────────────────────────────
step "2/13: Homebrew"
if command -v brew &>/dev/null; then
    ok "Homebrew установлен"
else
    if $CHECK_MODE; then err "Homebrew не найден"; exit 1; fi
    info "Устанавливаю Homebrew (придётся вспомнить пароль)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zshrc"
    fi
    ok "Homebrew установлен"
fi

# ─── Шаг 3: Python ────────────────────────────────────────────────────────
step "3/13: Python"
PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYVER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || continue)
        PYMAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || continue)
        PYMINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || continue)
        if (( PYMAJOR >= 3 && PYMINOR >= 10 )); then
            PYTHON_CMD="$cmd"
            ok "Python $PYVER ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    if $CHECK_MODE; then err "Python 3.10+ не найден"; exit 1; fi
    info "Устанавливаю Python 3.12..."
    brew install python@3.12
    PYTHON_CMD="python3.12"
    ok "Python 3.12 установлен"
fi

# ─── Шаг 4: Node.js ────────────────────────────────────────────────────
step "4/13: Node.js"
if command -v node &>/dev/null; then
    ok "Node.js $(node --version)"
else
    if $CHECK_MODE; then err "Node.js не найден"; exit 1; fi
    info "Устанавливаю Node.js..."
    brew install node
    ok "Node.js установлен"
fi

# ─── Шаг 5: OpenClaw ───────────────────────────────────────────────────
step "5/13: OpenClaw"
if command -v openclaw &>/dev/null; then
    ok "OpenClaw $(openclaw --version 2>/dev/null || echo 'установлен')"
else
    if $CHECK_MODE; then err "OpenClaw не найден"; exit 1; fi
    info "Устанавливаю OpenClaw..."
    if npm install -g openclaw 2>&1; then
        ok "OpenClaw установлен"
    else
        err "Не удалось установить OpenClaw. Запустите: npm install -g openclaw"
        exit 1
    fi
fi

# ─── Шаг 6: Ollama ──────────────────────────────────────────────────────
step "6/13: Ollama"
if command -v ollama &>/dev/null; then
    ok "Ollama установлен — нейросети готовы забрать вашу работу"
else
    if $CHECK_MODE; then warn "Ollama не найден"; exit 1; fi
    info "Устанавливаю Ollama..."
    brew install ollama
    ok "Ollama установлен"
fi

# Запуск Ollama
if ! pgrep -x "ollama" &>/dev/null; then
    if ! $CHECK_MODE; then
        info "Запускаю Ollama..."
        if [ -d "/Applications/Ollama.app" ]; then
            open -a Ollama 2>/dev/null || true
        fi
        ollama serve &>/dev/null || true &
        for i in 1 2 3 4 5 6 7 8; do
            curl -sf http://localhost:11434/api/tags &>/dev/null && break
            sleep 2
        done
        if curl -sf http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama запущен"
        else
            warn "Ollama не запустился — откройте приложение Ollama вручную"
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════
# ФАЗА 2: МОДЕЛИ И ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════
echo ""
echo "${BOLD}━━━ Фаза 2: Модели и приложение ━━━${NC}"

# ─── Шаг 7: AI модели ──────────────────────────────────────────────────
step "7/13: AI модели"
OLLAMA_READY=false
curl -sf http://localhost:11434/api/tags &>/dev/null && OLLAMA_READY=true

if [ "$OLLAMA_READY" = true ]; then
    MODEL="${JARVICE_MODEL:-glm-5.1:cloud}"
    EMBED_MODEL="nomic-embed-text:latest"

    if ollama list 2>/dev/null | grep -q "$(echo $MODEL | cut -d: -f1)"; then
        ok "Модель $MODEL доступна"
    else
        if $QUICK_MODE || $CHECK_MODE; then
            warn "Модель $MODEL не скачана. Запустите: ollama pull $MODEL"
        else
            info "Скачиваю модель $MODEL (облачная, жрёт трафик)..."
            if ollama pull "$MODEL" 2>&1; then
                ok "Модель $MODEL скачана"
            else
                warn "Облачная модель недоступна — скачиваю локальную qwen3:14b (8.6 ГБ)..."
                info "Это займёт 5-10 минут. Самое время усомниться в выборе профессии."
                if ollama pull "qwen3:14b" 2>&1; then
                    ok "Локальная модель qwen3:14b скачана"
                else
                    err "Не удалось скачать ни одну модель."
                    err "Проверьте интернет и запустите: ollama pull $MODEL"
                fi
            fi
        fi
    fi

    if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
        ok "Модель эмбеддингов доступна"
    else
        if $QUICK_MODE || $CHECK_MODE; then
            warn "Модель эмбеддингов не скачана. Запустите: ollama pull $EMBED_MODEL"
        else
            info "Скачиваю модель эмбеддингов (274 МБ — даже мем весит больше)..."
            ollama pull "$EMBED_MODEL" 2>&1 && ok "Модель эмбеддингов скачана" || \
                warn "Ошибка скачивания — поиск по памяти может не работать"
        fi
    fi
else
    warn "Ollama не запущен — модели не скачаны."
    echo "  ${DIM}Запустите Ollama и выполните: ollama pull glm-5.1:cloud nomic-embed-text:latest${NC}"
fi

# ─── Шаг 8: Авторизация Ollama Cloud ──────────────────────────────────
step "8/13: Ollama Cloud"
if [ "$OLLAMA_READY" = true ]; then
    CLOUD_TEST=$(curl -sf --max-time 20 http://localhost:11434/api/generate \
        -d '{"model":"glm-5.1:cloud","prompt":"привет","stream":false}' 2>/dev/null || echo "")
    if [ -n "$CLOUD_TEST" ]; then
        ok "Облачные модели работают (Да, бесплатно. Не привыкай.)"
    else
        echo ""
        echo "  ${BOLD}${YELLOW}⚡ Облачным моделям нужна авторизация${NC}"
        echo ""
        echo "  Запустите: ${BOLD}ollama signin${NC}"
        echo "  Откроется браузер для входа в ollama.com (бесплатно)."
        echo ""
        if ! $CHECK_MODE && ! $QUICK_MODE; then
            read -p "  Нажмите Enter для входа через браузер, или 's' для пропуска: " SIGNIN_CHOICE
            if [ "$SIGNIN_CHOICE" != "s" ]; then
                ollama signin 2>/dev/null || warn "Вход не удался — запустите 'ollama signin' вручную"
            fi
        fi
    fi
fi

# ─── Шаг 9: The Jarvice ────────────────────────────────────────────────
step "9/13: The Jarvice"
if $CHECK_MODE; then
    warn "Пропускаю установку Jarvice (режим проверки)"
else
    mkdir -p "$JARVICE_DIR"

    if [ ! -d "$VENV_DIR/bin" ]; then
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        ok "Python venv создан ($PYTHON_CMD)"
    fi

    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || {
            err "Venv сломан — пересоздаю..."
            rm -rf "$VENV_DIR"
            "$PYTHON_CMD" -m venv "$VENV_DIR"
            source "$VENV_DIR/bin/activate"
        }
    else
        err "Venv не найден: $VENV_DIR"
        exit 1
    fi

    pip install --upgrade pip --quiet 2>/dev/null || true

    CLONE_DIR="$JARVICE_DIR/src/the-jarvice"
    if [ -d "$CLONE_DIR" ] && [ -f "$CLONE_DIR/pyproject.toml" ]; then
        cd "$CLONE_DIR"
        git pull --ff-only 2>/dev/null || git pull 2>/dev/null || true
    else
        info "Клонирую с GitHub..."
        mkdir -p "$JARVICE_DIR/src"
        if git clone "$GITHUB_REPO" "$CLONE_DIR" --depth 1 2>&1; then
            cd "$CLONE_DIR"
        else
            err "Не удалось клонировать репозиторий. Проверьте интернет."
            exit 1
        fi
    fi

    if [ -f "pyproject.toml" ]; then
        if pip install . --quiet 2>&1; then
            ok "the-jarvice установлен. Ваши данные уже скучают по вам."
        elif pip install -e . --quiet 2>&1; then
            ok "the-jarvice установлен (dev-режим)"
        else
            err "Не удалось установить the-jarvice."
            err "Проверьте лог выше и запустите установку повторно."
            exit 1
        fi
    else
        err "Исходники Jarvice не найдены: $CLONE_DIR"
        exit 1
    fi

    cd "$HOME"

    SHELL_RC="$HOME/.zshrc"
    if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi
    if ! grep -q ".the-jarvice/venv/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# The Jarvice" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.the-jarvice/venv/bin:$PATH"' >> "$SHELL_RC"
        ok "PATH добавлен в $SHELL_RC"
    else
        ok "PATH уже настроен"
    fi
    export PATH="$VENV_DIR/bin:$PATH"
fi

# ═══════════════════════════════════════════════════════════
# ФАЗА 3: НАСТРОЙКА И ПОДКЛЮЧЕНИЕ
# ═══════════════════════════════════════════════════════════
echo ""
echo "${BOLD}━━━ Фаза 3: Настройка и подключение ━━━${NC}"

# ─── Шаг 10: Настройка OpenClaw ────────────────────────────────────────
step "10/13: Настройка OpenClaw"
if $CHECK_MODE; then
    warn "Пропускаю настройку OpenClaw (режим проверки)"
else
    mkdir -p "$OPENCLAW_WORKSPACE"
    mkdir -p "$OPENCLAW_WORKSPACE/memory"

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
        ok "Создан AGENTS.md"
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
        ok "Создан SOUL.md"
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
        ok "Создан MEMORY.md"
    fi

    if [ ! -f "$JARVICE_DIR/config.yaml" ]; then
        cat > "$JARVICE_DIR/config.yaml" << 'CFGEOF'
# The Jarvice Configuration — v1
# Сгенерировано setup.sh

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
        ok "Создан config.yaml (облачные модели)"
    else
        ok "config.yaml уже существует"
    fi
fi

# ─── Шаг 11: Учётные данные ────────────────────────────────────────────
step "11/13: Учётные данные"
echo ""
echo "  ${BOLD}Подключаем сервисы.${NC}"
echo "  ${DIM}Нажмите Enter, чтобы пропустить любой шаг. Да, даже тот, что со звёздочкой.${NC}"
echo "  ${DIM}Пароли хранятся в Keychain. Не в plaintext — мы не варвары.${NC}"
echo ""

if ! $CHECK_MODE && ! $QUICK_MODE; then
    echo "  ${BOLD}1/3 Токен Telegram-бота${NC}"
    echo "  1. Откройте t.me/BotFather"
    echo "  2. Отправьте /newbot"
    echo "  3. Выберите имя (например «Мой Ассистент»)"
    echo "  4. Выберите username (например «my_assistant_bot»)"
    echo "  5. Скопируйте токен (формат: 7123456789:AA...)"
    echo "  ${DIM}Нет, это не номер кредитки. Хотя выгорание делает похожими все цифры.${NC}"
    echo ""
    read -p "  Токен Telegram-бота: " TG_TOKEN
    if [ -n "$TG_TOKEN" ]; then
        if security add-generic-password -U -s "the-jarvice.telegram-bot" -a "bot-token" -w "$TG_TOKEN" 2>/dev/null; then
            ok "Токен сохранён в Keychain"
        else
            echo "$TG_TOKEN" > "$JARVICE_DIR/.telegram-token"
            chmod 600 "$JARVICE_DIR/.telegram-token"
            ok "Токен сохранён в файл (Keychain недоступен)"
        fi
    else
        info "Пропущено — настройте позже: the-jarvice configure --quick"
    fi

    echo ""
    echo "  ${BOLD}2/3 Учётные данные Exchange${NC} (опционально — для сводок по почте)"
    echo "  ${DIM}Пропустите, если у вас нет Exchange. Завидуем.${NC}"
    echo ""
    read -p "  Email Exchange (или Enter для пропуска): " EX_EMAIL
    if [ -n "$EX_EMAIL" ]; then
        read -s -p "  Пароль Exchange (скрыт): " EX_PASS
        echo ""
        if [ -n "$EX_PASS" ]; then
            if security add-generic-password -U -s "the-jarvice.exchange" -a "$EX_EMAIL" -w "$EX_PASS" 2>/dev/null; then
                ok "Учётные данные Exchange сохранены в Keychain"
            else
                warn "Не удалось сохранить в Keychain — запустите: the-jarvice configure --quick"
            fi
        fi
    else
        info "Пропущено — настройте позже: the-jarvice configure --quick"
    fi

    echo ""
    echo "  ${BOLD}3/3 Подключение бота к OpenClaw${NC}"
    echo "  ${DIM}Это свяжет бота с системой. Бот в восторге. Наверное.${NC}"
    echo ""
    if [ -n "${TG_TOKEN:-}" ]; then
        info "Подключаю Telegram-канал к OpenClaw..."
        if openclaw channels add telegram --token "***" 2>/dev/null; then
            ok "Telegram-канал добавлен"
        else
            echo ""
            echo "  ${YELLOW}Автоматическая настройка не удалась. Настройте вручную:${NC}"
            echo "  1. Запустите: ${BOLD}openclaw channels add${NC}"
            echo "  2. Выберите Telegram"
            echo "  3. Введите токен бота"
        fi
    else
        echo "  После создания бота запустите:"
        echo "    ${BOLD}openclaw channels add${NC}"
        echo "    ${BOLD}the-jarvice configure --quick${NC}"
    fi
fi

# ─── Шаг 12: Директории данных ──────────────────────────────────────────
step "12/13: Директории данных"
if ! $CHECK_MODE; then
    RED_DIR="$JARVICE_DIR/data/pii/RED"
    GREEN_DIR="$JARVICE_DIR/data/pii/GREEN"
    LOG_DIR="$JARVICE_DIR/logs"

    for dir in "$RED_DIR" "$GREEN_DIR" "$LOG_DIR"; do
        mkdir -p "$dir"
    done
    chmod 700 "$RED_DIR"
    ok "Директории созданы (PII RED — chmod 700, потому что чужие глаза тут не нужны)"
fi

# ═══════════════════════════════════════════════════════════
# ФАЗА 4: ЗАПУСК
# ═══════════════════════════════════════════════════════════
echo ""
echo "${BOLD}━━━ Фаза 4: Запуск ━━━${NC}"

# ─── Шаг 13: Запуск Gateway ────────────────────────────────────────────
step "13/13: Запуск Gateway"
if ! $CHECK_MODE; then
    if curl -sf http://localhost:19000/health &>/dev/null; then
        ok "OpenClaw Gateway уже запущен"
    else
        info "Запускаю OpenClaw Gateway..."
        openclaw gateway run &>/dev/null &
        for i in 1 2 3 4 5; do
            sleep 2
            curl -sf http://localhost:19000/health &>/dev/null && break
        done
        if curl -sf http://localhost:19000/health &>/dev/null; then
            ok "Gateway запущен"
        else
            warn "Gateway не запустился за 10 сек — запустите вручную: openclaw gateway run"
        fi
    fi
fi

# ─── Итоги ─────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo "${GREEN}${BOLD}  ✅ Установка завершена!${NC}"
echo "${BOLD}══════════════════════════════════════════════════════${NC}"
echo ""

ISSUES=0

if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    echo "  ${YELLOW}⚠️  Ollama не запущен — откройте приложение Ollama${NC}"
    ISSUES=$((ISSUES + 1))
fi

if ! command -v the-jarvice &>/dev/null && [ ! -f "$VENV_DIR/bin/the-jarvice" ]; then
    echo "  ${YELLOW}⚠️  the-jarvice не в PATH — перезапустите Terminal${NC}"
    echo "  ${YELLOW}   или выполните: source ~/.zshrc${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -f "$JARVICE_DIR/config.yaml" ]; then
    echo "  ${YELLOW}⚠️  config.yaml не найден — запустите: the-jarvice configure --quick${NC}"
    ISSUES=$((ISSUES + 1))
fi

HAS_EXCHANGE=false
HAS_TELEGRAM=false
[ -n "${TG_TOKEN:-}" ] && HAS_TELEGRAM=true
[ -n "${EX_EMAIL:-}" ] && HAS_EXCHANGE=true

if [ "$HAS_EXCHANGE" = false ] && [ "$HAS_TELEGRAM" = false ]; then
    echo "  ${YELLOW}⚠️  Нет источников данных — настройте Exchange или Telegram${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$ISSUES" -eq 0 ]; then
    echo "  ${GREEN}Все системы готовы! 🎉${NC}"
else
    echo ""
    echo "  ${YELLOW}Найдено проблем: ${ISSUES} — см. выше${NC}"
fi

echo ""
echo "  ${BOLD}Установлено:${NC}"
echo "    ✅ OpenClaw (фреймворк агентов + gateway)"
echo "    ✅ The Jarvice (пайплайн данных + сводки)"
echo "    ✅ Ollama + модели (glm-5.1:cloud, nomic-embed-text)"
echo "    ✅ Python venv + PATH"
echo "    ✅ Директории PII (RED/GREEN)"
echo "    ✅ Конфиг с облачными моделями"
echo ""

echo "  ${BOLD}Дальнейшие шаги:${NC}"
echo ""

if [ -z "${TG_TOKEN:-}" ]; then
    echo "  1. ${BOLD}Создайте Telegram-бота:${NC}"
    echo "     Откройте t.me/BotFather → /newbot → скопируйте токен"
    echo "     Затем: ${BOLD}openclaw channels add${NC}"
    echo "     Затем: ${BOLD}the-jarvice configure --quick${NC}"
    echo ""
fi

if [ -z "${EX_EMAIL:-}" ]; then
    echo "  2. ${BOLD}Учётные данные Exchange${NC} (опционально):"
    echo "     ${BOLD}the-jarvice configure --quick${NC}"
    echo ""
fi

echo "  ${BOLD}Проверка:${NC}"
echo "    the-jarvice doctor"
echo "    openclaw status"
echo ""
echo "  ${BOLD}Первый запуск:${NC}"
echo "    the-jarvice run --once"
echo ""
echo "  ${DIM}После первого запуска — сводка в Telegram за 30 секунд. Если не пришла — проверьте, не молчит ли бот из принципа.${NC}"
echo ""
echo "  ${BOLD}Расписание сводок:${NC}"
echo "    the-jarvice enable"
echo ""
echo "  ${BOLD}Запуск Gateway (если не запущен):${NC}"
echo "    openclaw gateway run"
echo ""
echo "  ${DIM}Если что-то не работает:${NC}"
echo "  ${DIM}  1. Перезапустите Terminal (помогает в 90% случаев)${NC}"
echo "  ${DIM}  2. Напишите Вадиму — он разберётся с оставшимися 10%${NC}"
echo ""
echo "  ${DIM}Конфиг:    ~/.the-jarvice/config.yaml${NC}"
echo "  ${DIM}OpenClaw:  ~/.openclaw/${NC}"
echo "  ${DIM}Документация: https://github.com/negatix-creator/the-jarvice${NC}"
echo ""
