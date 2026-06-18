#!/bin/bash
# =============================================================================
# deploy-openclaw-linux.sh — Полный деплой OpenClaw на Linux (одним скриптом)
# =============================================================================
# Использование:
#   scp этот_скрипт user@host:/tmp/ && ssh user@host 'bash /tmp/deploy-openclaw-linux.sh'
#
# Что делает:
#   1. Проверяет/устанавливает Node.js, OpenClaw, Ollama
#   2. Копирует Ollama SSH-ключ (для cloud-моделей) с машины-источника
#   3. Настраивает systemd services (Ollama + OpenClaw gateway)
#   4. Создаёт конфиг: models, Telegram bot, owner, memory health
#   5. Перезапускает сервисы, проверяет health
#
# Параметры (через env):
#   BOT_TOKEN     — Telegram бот-токен от @BotFather
#   OWNER_TG_ID   — Telegram ID владельца (число)
#   OLLAMA_KEY    — путь к id_ed25519 ключу Ollama (для cloud-моделей)
#   AGENT_MODEL_PRIMARY   — primary модель (по умолчанию ollama/glm-5.2:cloud)
#   AGENT_MODEL_FALLBACK  — fallback модель (по умолчанию ollama/glm-5.1:cloud)
#   OPENCLAW_USER — пользователь для сервиса (по умолчанию текущий)
# =============================================================================

set -e

# --- Параметры по умолчанию ---
MODEL_PRIMARY="${AGENT_MODEL_PRIMARY:-ollama/glm-5.2:cloud}"
MODEL_FALLBACK="${AGENT_MODEL_FALLBACK:-ollama/glm-5.1:cloud}"
SERVICE_USER="${OPENCLAW_USER:-$(whoami)}"
WORKSPACE_DIR="$HOME/.openclaw/workspace"

echo "=========================================="
echo "  OpenClaw Deploy — Linux"
echo "=========================================="
echo "Model primary:  $MODEL_PRIMARY"
echo "Model fallback: $MODEL_FALLBACK"
echo "Service user:   $SERVICE_USER"
echo ""

# --- Проверка параметров ---
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не задан. Получи токен у @BotFather и передай через env:"
    echo "   BOT_TOKEN=*** OWNER_TG_ID=12345 OLLAMA_KEY=~/.oll…5519 bash $0"
    exit 1
fi
if [ -z "$OWNER_TG_ID" ]; then
    echo "❌ OWNER_TG_ID не задан. Узнай свой Telegram ID у @userinfobot"
    exit 1
fi

# --- Определение пакетного менеджера ---
PKG=""
INSTALL=""
if command -v apt &>/dev/null; then
    PKG="apt"
    INSTALL="sudo apt update && sudo apt install -y"
elif command -v dnf &>/dev/null; then
    PKG="dnf"
    INSTALL="sudo dnf install -y"
elif command -v yum &>/dev/null; then
    PKG="yum"
    INSTALL="sudo yum install -y"
elif command -v apk &>/dev/null; then
    PKG="apk"
    INSTALL="sudo apk add"
else
    echo "❌ Неизвестный пакетный менеджер. Установи Node.js и Ollama вручную."
    exit 1
fi
echo "Пакетный менеджер: $PKG"

# =============================================================================
# Шаг 1: Базовые пакеты
# =============================================================================
echo "=== Установка базовых пакетов ==="
$INSTALL curl git build-essential 2>/dev/null || $INSTALL curl git gcc make 2>/dev/null || true

# =============================================================================
# Шаг 2: Node.js (v24+)
# =============================================================================
if ! command -v node &>/dev/null || [ "$(node --version | cut -dv -f2 | cut -d. -f1)" -lt 22 ]; then
    echo "=== Установка Node.js ==="
    if [ "$PKG" = "apt" ]; then
        curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
        sudo apt install -y nodejs
    else
        curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
        sudo $INSTALL nodejs
    fi
else
    echo "✅ Node.js $(node --version) уже установлен"
fi

# =============================================================================
# Шаг 3: OpenClaw
# =============================================================================
if ! command -v openclaw &>/dev/null; then
    echo "=== Установка OpenClaw ==="
    sudo npm install -g openclaw
else
    echo "✅ OpenClaw уже установлен: $(openclaw --version 2>&1 | head -1)"
fi

# =============================================================================
# Шаг 4: Ollama
# =============================================================================
if ! command -v ollama &>/dev/null; then
    echo "=== Установка Ollama ==="
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama уже установлен"
fi

# Запускаем Ollama (если не запущен)
if ! pgrep -f "ollama serve" &>/dev/null; then
    echo "=== Запуск Ollama ==="
    ollama serve &
    sleep 3
fi

# Проверяем что Ollama отвечает
if curl -s http://127.0.0.1:11434/api/tags &>/dev/null; then
    echo "✅ Ollama API отвечает"
else
    echo "❌ Ollama API не отвечает. Проверь: ollama serve"
    exit 1
fi

# =============================================================================
# Шаг 5: Ollama SSH-ключ (для cloud-моделей)
# =============================================================================
if [ -n "$OLLAMA_KEY" ] && [ -f "$OLLAMA_KEY" ]; then
    echo "=== Копирование Ollama SSH-ключа (для cloud-моделей) ==="
    mkdir -p ~/.ollama
    cp "$OLLAMA_KEY" ~/.ollama/id_ed25519
    chmod 600 ~/.ollama/id_ed25519
    if [ -f "${OLLAMA_KEY}.pub" ]; then
        cp "${OLLAMA_KEY}.pub" ~/.ollama/id_ed25519.pub
        chmod 600 ~/.ollama/id_ed25519.pub
    fi
    echo "✅ Ollama SSH-ключ скопирован"

    # Перезапуск Ollama чтобы подхватить ключ
    sudo systemctl restart ollama 2>/dev/null || { pkill -f "ollama serve" 2>/dev/null || true; sleep 2; ollama serve & sleep 3; }

    # Проверка cloud-модели
    echo "=== Проверка cloud-модели ==="
    MODEL_NAME="${MODEL_PRIMARY#ollama/}"
    RESPONSE=$(curl -s http://127.0.0.1:11434/api/chat \
        -d "{\"model\":\"$MODEL_NAME\",\"messages\":[{\"role\":\"user\",\"content\":\"привет\"}],\"stream\":false}" 2>&1)

    if echo "$RESPONSE" | grep -q '"error"'; then
        echo "❌ Cloud-модель не работает: $(echo "$RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error","?")[:80])' 2>/dev/null)"
        echo "   Нужна подписка ollama.com или другой Ollama SSH-ключ"
    elif echo "$RESPONSE" | grep -q '"message"'; then
        echo "✅ Cloud-модель $MODEL_NAME работает"
    else
        echo "⚠️ Неожиданный ответ: ${RESPONSE:0:80}"
    fi
else
    echo "⚠️ OLLAMA_KEY не задан или файл не найден. Cloud-модели не будут работать."
    echo "   Передай: OLLAMA_KEY=~/.oll…5519"
fi

# Скачиваем embedding-модель (нужна для memory_search)
echo "=== Скачивание nomic-embed-text ==="
ollama pull nomic-embed-text 2>&1 | tail -1

# Скачиваем модели
echo "=== Скачивание моделей ==="
ollama pull "${MODEL_PRIMARY#ollama/}" 2>&1 | tail -1
ollama pull "${MODEL_FALLBACK#ollama/}" 2>&1 | tail -1

# =============================================================================
# Шаг 6: Структура директорий
# =============================================================================
echo "=== Создание структуры ==="
mkdir -p ~/.openclaw
mkdir -p ~/.openclaw/agents/main
mkdir -p ~/.openclaw/agents/main/sessions
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/memory"
chmod 700 ~/.openclaw

# =============================================================================
# Шаг 7: Конфиг OpenClaw
# =============================================================================
echo "=== Запись openclaw.json ==="

# Генерируем auth token
AUTH_TOKEN=*** -c "import secrets; print(secrets.token_hex(24))")

cat > ~/.openclaw/openclaw.json << JSONEOF
{
  "agents": {
    "defaults": {
      "workspace": "$WORKSPACE_DIR"
    },
    "list": [
      {
        "id": "main",
        "model": {
          "primary": "$MODEL_PRIMARY",
          "fallbacks": ["$MODEL_FALLBACK"]
        }
      }
    ]
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "***"
    }
  },
  "commands": {
    "ownerAllowFrom": ["telegram:$OWNER_TG_ID"]
  },
  "channels": {
    "telegram": {
      "accounts": {
        "default": {
          "botToken": "$BOT_TOKEN",
          "dmPolicy": "allowlist",
          "allowFrom": ["$OWNER_TG_ID"],
          "streaming": {
            "mode": "partial"
          }
        }
      }
    }
  },
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434",
        "api": "ollama",
        "models": [
          {
            "id": "${MODEL_PRIMARY#ollama/}",
            "api": "ollama",
            "reasoning": true,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            "contextWindow": 1000000,
            "maxTokens": 16384,
            "params": {"num_ctx": 1000000}
          },
          {
            "id": "${MODEL_FALLBACK#ollama/}",
            "api": "ollama",
            "reasoning": true,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            "contextWindow": 202752,
            "maxTokens": 16384,
            "params": {"num_ctx": 202752}
          },
          {
            "id": "nomic-embed-text",
            "api": "ollama",
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            "contextWindow": 8192,
            "maxTokens": 8192,
            "params": {"num_ctx": 8192}
          }
        ]
      }
    },
    "mode": "merge"
  },
  "session": {
    "dmScope": "per-channel-peer",
    "maintenance": {
      "mode": "enforce",
      "pruneAfter": "7d",
      "maxEntries": 60
    }
  },
  "cron": {
    "sessionRetention": "24h"
  }
}
JSONEOF
echo "✅ Конфиг записан (auth token: ${AUTH_TOKEN:***"

# =============================================================================
# Шаг 8: Базовые workspace файлы
# =============================================================================
if [ ! -f "$WORKSPACE_DIR/MEMORY.md" ]; then
    echo "=== Создание MEMORY.md ==="
    cat > "$WORKSPACE_DIR/MEMORY.md" << 'MDEOF'
# MEMORY.md

## Config
- Model: glm-5.2:cloud primary, glm-5.1:cloud fallback
- Memory health: pruneAfter 7d, maxEntries 60, cron 24h
MDEOF
fi

# =============================================================================
# Шаг 9: systemd service для Ollama
# =============================================================================
echo "=== Создание systemd service для Ollama ==="

# Ollama installer обычно создаёт свой сервис, но проверим
if [ ! -f /etc/systemd/system/ollama.service ]; then
    sudo tee /etc/systemd/system/ollama.service > /dev/null << 'SVCEOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
Type=simple
User=USER_PLACEHOLDER
ExecStart=/usr/local/bin/ollama serve
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SVCEOF
    sudo sed -i "s|USER_PLACEHOLDER|$SERVICE_USER|" /etc/systemd/system/ollama.service
fi

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama
echo "✅ Ollama systemd service активен"

# =============================================================================
# Шаг 10: systemd service для OpenClaw Gateway
# =============================================================================
echo "=== Создание systemd service для OpenClaw ==="

# Определяем путь к openclaw
OPENCLAW_BIN=$(which openclaw)

sudo tee /etc/systemd/system/openclaw-gateway.service > /dev/null << SVCEOF
[Unit]
Description=OpenClaw Gateway
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User=USER_PLACEHOLDER
ExecStart=OPENCLAW_BIN_PLACEHOLDER gateway --port 18789
Environment=PATH=/usr/local/bin:/usr/bin:/bin:HOME_PLACEHOLDER/.local/bin
Environment=HOME=HOME_PLACEHOLDER
WorkingDirectory=HOME_PLACEHOLDER
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo sed -i \
    -e "s|USER_PLACEHOLDER|$SERVICE_USER|" \
    -e "s|OPENCLAW_BIN_PLACEHOLDER|$OPENCLAW_BIN|" \
    -e "s|HOME_PLACEHOLDER|$HOME|g" \
    /etc/systemd/system/openclaw-gateway.service

# Останавливаем старые процессы
pkill -f "openclaw" 2>/dev/null || true
sleep 2

sudo systemctl daemon-reload
sudo systemctl enable openclaw-gateway
sudo systemctl restart openclaw-gateway
echo "✅ OpenClaw systemd service активен"

# =============================================================================
# Шаг 11: Ожидание и проверка
# =============================================================================
echo "=== Ожидание запуска gateway ==="
for i in $(seq 1 10); do
    sleep 3
    if curl -s http://127.0.0.1:18789/health 2>/dev/null | grep -q "live"; then
        echo "✅ Gateway UP (попытка $i)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Gateway не запустился за 30 сек"
        echo "Лог:"
        sudo journalctl -u openclaw-gateway --no-pager -n 20 2>/dev/null || true
        exit 1
    fi
done

# Проверка стабильности
sleep 5
if curl -s http://127.0.0.1:18789/health 2>/dev/null | grep -q "live"; then
    echo "✅ Gateway стабилен"
else
    echo "❌ Gateway упал после старта"
    sudo journalctl -u openclaw-gateway --no-pager -n 20 2>/dev/null || true
    exit 1
fi

# =============================================================================
# Шаг 12: Smoke tests
# =============================================================================
echo ""
echo "=========================================="
echo "  SMOKE TESTS"
echo "=========================================="

PASS=0
FAIL=0

# 1. Gateway health
if curl -s http://127.0.0.1:18789/health | grep -q "live"; then
    echo "✅ 1. Gateway health: live"; PASS=$((PASS+1))
else
    echo "❌ 1. Gateway health: FAIL"; FAIL=$((FAIL+1))
fi

# 2. Ollama API
if curl -s http://127.0.0.1:11434/api/tags | grep -q "models"; then
    echo "✅ 2. Ollama API: OK"; PASS=$((PASS+1))
else
    echo "❌ 2. Ollama API: FAIL"; FAIL=$((FAIL+1))
fi

# 3. Cloud model
MODEL_NAME="${MODEL_PRIMARY#ollama/}"
if curl -s http://127.0.0.1:11434/api/chat -d "{\"model\":\"$MODEL_NAME\",\"messages\":[{\"role\":\"user\",\"content\":\"тест\"}],\"stream\":false}" 2>&1 | grep -q '"message"'; then
    echo "✅ 3. Cloud model ($MODEL_NAME): OK"; PASS=$((PASS+1))
else
    echo "❌ 3. Cloud model ($MODEL_NAME): FAIL"; FAIL=$((FAIL+1))
fi

# 4. Embedding model
if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "✅ 4. Embedding model: OK"; PASS=$((PASS+1))
else
    echo "❌ 4. Embedding model: FAIL"; FAIL=$((FAIL+1))
fi

# 5. Telegram bot
BOT_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe" 2>&1)
if echo "$BOT_INFO" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$BOT_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null)
    echo "✅ 5. Telegram bot: @$BOT_NAME"; PASS=$((PASS+1))
else
    echo "❌ 5. Telegram bot: FAIL"; FAIL=$((FAIL+1))
fi

# 6. Permissions
PERMS=$(stat -c "%a" ~/.openclaw 2>/dev/null)
if [ "$PERMS" = "700" ]; then
    echo "✅ 6. Permissions ~/.openclaw: 700"; PASS=$((PASS+1))
else
    echo "❌ 6. Permissions ~/.openclaw: $PERMS (нужно 700)"; FAIL=$((FAIL+1))
fi

# 7. Memory health
if python3 -c "import json; d=json.load(open('$HOME/.openclaw/openclaw.json')); assert d['session']['maintenance']['pruneAfter']=='7d'" 2>/dev/null; then
    echo "✅ 7. Memory health config: OK"; PASS=$((PASS+1))
else
    echo "❌ 7. Memory health config: FAIL"; FAIL=$((FAIL+1))
fi

# 8. systemd services
if systemctl is-active --quiet openclaw-gateway && systemctl is-active --quiet ollama; then
    echo "✅ 8. systemd services: both active"; PASS=$((PASS+1))
else
    echo "❌ 8. systemd services: not all active"; FAIL=$((FAIL+1))
fi

# 9. Enabled at boot
if systemctl is-enabled --quiet openclaw-gateway && systemctl is-enabled --quiet ollama; then
    echo "✅ 9. Enabled at boot: both"; PASS=$((PASS+1))
else
    echo "❌ 9. Enabled at boot: not all enabled"; FAIL=$((FAIL+1))
fi

echo ""
echo "=========================================="
echo "  RESULT: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🎉 Деплой завершён успешно!"
    echo "   Bot: @$BOT_NAME"
    echo "   Model: $MODEL_PRIMARY (fallback: $MODEL_FALLBACK)"
    echo "   Gateway: http://127.0.0.1:18789"
    echo ""
    echo "Следующие шаги:"
    echo "   1. Создать SOUL.md, AGENTS.md, USER.md в $WORKSPACE_DIR"
    echo "   2. Написать боту в Telegram — проверить ответ"
    echo "   3. Зарегистрировать машину в INFRASTRUCTURE_REGISTRY.md"
    echo "   4. Настроить daily restart cron (04:05 local)"
else
    echo ""
    echo "⚠️ Есть ошибки. Проверь логи:"
    echo "   sudo journalctl -u openclaw-gateway --no-pager -n 30"
    echo "   sudo journalctl -u ollama --no-pager -n 30"
    exit 1
fi