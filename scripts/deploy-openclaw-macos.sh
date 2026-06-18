#!/bin/bash
# =============================================================================
# deploy-openclaw-macos.sh — Полный деплой OpenClaw на macOS (одним скриптом)
# =============================================================================
# Использование:
#   scp этот_скрипт user@host:/tmp/ && ssh user@host 'bash /tmp/deploy-openclaw-macos.sh'
#   или через бастион: scp -P PORT ... && ssh -p PORT user@bastion 'bash /tmp/deploy-openclaw-macos.sh'
#
# Что делает:
#   1. Проверяет/устанавливает Homebrew, Node.js, OpenClaw, Ollama
#   2. Копирует Ollama SSH-ключ (для cloud-моделей) с машины-источника
#   3. Настраивает LaunchAgents (Ollama + OpenClaw gateway)
#   4. Создаёт конфиг: models, Telegram bot, owner, memory health
#   5. Перезапускает сервисы, проверяет health
#
# Параметры (через env):
#   BOT_TOKEN     — Telegram бот-токен от @BotFather
#   OWNER_TG_ID   — Telegram ID владельца (число)
#   OLLAMA_KEY    — путь к id_ed25519 ключу Ollama (для cloud-моделей)
#   AGENT_MODEL_PRIMARY   — primary модель (по умолчанию ollama/glm-5.2:cloud)
#   AGENT_MODEL_FALLBACK  — fallback модель (по умолчанию ollama/glm-5.1:cloud)
# =============================================================================

set -e

# --- Параметры по умолчанию ---
MODEL_PRIMARY="${AGENT_MODEL_PRIMARY:-ollama/glm-5.2:cloud}"
MODEL_FALLBACK="${AGENT_MODEL_FALLBACK:-ollama/glm-5.1:cloud}"
WORKSPACE_DIR="$HOME/.openclaw/workspace"

echo "=========================================="
echo "  OpenClaw Deploy — macOS"
echo "=========================================="
echo "Model primary:  $MODEL_PRIMARY"
echo "Model fallback: $MODEL_FALLBACK"
echo ""

# --- Проверка параметров ---
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не задан. Получи токен у @BotFather и передай через env:"
    echo "   BOT_TOKEN=xxxx OWNER_TG_ID=12345 OLLAMA_KEY=~/.ollama/id_ed25519 bash $0"
    exit 1
fi
if [ -z "$OWNER_TG_ID" ]; then
    echo "❌ OWNER_TG_ID не задан. Узнай свой Telegram ID у @userinfobot"
    exit 1
fi

# =============================================================================
# Шаг 1: Homebrew
# =============================================================================
if ! command -v brew &>/dev/null; then
    echo "=== Установка Homebrew ==="
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "✅ Homebrew уже установлен"
fi

export PATH="/opt/homebrew/bin:$PATH"

# =============================================================================
# Шаг 2: Node.js
# =============================================================================
if ! command -v node &>/dev/null; then
    echo "=== Установка Node.js ==="
    brew install node
else
    echo "✅ Node.js $(node --version) уже установлен"
fi

# =============================================================================
# Шаг 3: OpenClaw
# =============================================================================
if ! command -v openclaw &>/dev/null; then
    echo "=== Установка OpenClaw ==="
    brew install openclaw
else
    echo "✅ OpenClaw уже установлен: $(openclaw --version 2>&1 | head -1)"
fi

# =============================================================================
# Шаг 4: Ollama
# =============================================================================
if ! command -v ollama &>/dev/null; then
    echo "=== Установка Ollama ==="
    brew install ollama
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
    pkill -f "ollama serve" 2>/dev/null || true
    sleep 2
    ollama serve &
    sleep 3

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
    echo "   Передай: OLLAMA_KEY=~/.ollama/id_ed25519"
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
AUTH_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(24))")

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
      "token": "$AUTH_TOKEN"
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
echo "✅ Конфиг записан (auth token: ${AUTH_TOKEN:0:8}...)"

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
# Шаг 9: LaunchAgent для Ollama
# =============================================================================
echo "=== Создание LaunchAgent для Ollama ==="
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.ollama.ollama.plist << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.ollama</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ollama.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ollama.err.log</string>
</dict>
</plist>
PLISTEOF

launchctl unload ~/Library/LaunchAgents/com.ollama.ollama.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.ollama.ollama.plist 2>&1
echo "✅ Ollama LaunchAgent загружен"

# =============================================================================
# Шаг 10: LaunchAgent для OpenClaw Gateway
# =============================================================================
echo "=== Создание LaunchAgent для OpenClaw ==="

cat > ~/Library/LaunchAgents/com.openclaw.gateway.plist << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/openclaw</string>
        <string>gateway</string>
        <string>--port</string>
        <string>18789</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/openclaw-gateway.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/openclaw-gateway.err.log</string>
</dict>
</plist>
PLISTEOF

# Убиваем старые процессы
pkill -f "openclaw" 2>/dev/null || true
sleep 2

launchctl unload ~/Library/LaunchAgents/com.openclaw.gateway.plist 2>/dev/null || true
sleep 1
launchctl load ~/Library/LaunchAgents/com.openclaw.gateway.plist 2>&1
echo "✅ OpenClaw LaunchAgent загружен"

# =============================================================================
# Шаг 11: PATH в .zshrc
# =============================================================================
if ! grep -q "/opt/homebrew/bin" ~/.zshrc 2>/dev/null; then
    echo "=== Добавление PATH в .zshrc ==="
    echo '' >> ~/.zshrc
    echo '# Homebrew' >> ~/.zshrc
    echo 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"' >> ~/.zshrc
    echo "✅ PATH добавлен в .zshrc"
else
    echo "✅ PATH уже в .zshrc"
fi

# =============================================================================
# Шаг 12: Ожидание и проверка
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
        tail -20 /tmp/openclaw-gateway.log 2>/dev/null
        exit 1
    fi
done

# Проверка стабильности
sleep 5
if curl -s http://127.0.0.1:18789/health 2>/dev/null | grep -q "live"; then
    echo "✅ Gateway стабилен"
else
    echo "❌ Gateway упал после старта"
    tail -20 /tmp/openclaw-gateway.log 2>/dev/null
    exit 1
fi

# =============================================================================
# Шаг 13: Smoke tests
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
PERMS=$(stat -f "%Lp" ~/.openclaw 2>/dev/null)
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

# 8. LaunchAgents loaded
if launchctl list | grep -q "com.openclaw.gateway" && launchctl list | grep -q "com.ollama.ollama"; then
    echo "✅ 8. LaunchAgents: both loaded"; PASS=$((PASS+1))
else
    echo "❌ 8. LaunchAgents: not all loaded"; FAIL=$((FAIL+1))
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
    echo "   /tmp/openclaw-gateway.log"
    echo "   /tmp/ollama.log"
    exit 1
fi