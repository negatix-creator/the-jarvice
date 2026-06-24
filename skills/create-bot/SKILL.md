---
name: create-bot
description: Full setup — SSH to remote machine, install OpenClaw, configure Ollama + embeddings + memory, create first Telegram bot. End-to-end from zero to working bot.
---

# Create Bot Skill — Full Setup

Полный скилл: от SSH-подключения к пустой машине до работающего Telegram-бота с памятью и эмбеддингами.

> **Связанный скилл:** При каждом подключении к чужой машине используй `remote-connect` для регистрации в INFRASTRUCTURE_REGISTRY.md и логирования действий. Инсайты из деплоя обновляют этот скилл.

---

## Часть 0: Регистрация машины (remote-connect)

**Перед началом деплоя** — зарегистрировать машину в инфраструктурном реестре:

1. Запустить `scripts/remote-discover.sh` на целевой машине
2. Добавить/обновить запись в `INFRASTRUCTURE_REGISTRY.md`
3. Указать владельца в `## Люди и привязка к машинам`
4. Записать креды как ссылку на Keychain (НЕ как значения)
5. После деплоя — обновить реестр с установленными сервисами

> См. `skills/remote-connect/SKILL.md` для полного протокола.

---

## Часть 1: Подключение к удалённой машине

### Шаг 1: SSH-подключение

```bash
ssh user@host
# или по IP
ssh user@192.168.x.x
# или с ключом
ssh -i ~/.ssh/my_key user@host
```

Если ключ не настроен — создай и скопируй:

```bash
ssh-keygen -t ed25519 -C "openclaw-setup"
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host
```

### Шаг 2: Базовая настройка системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl build-essential
sudo timedatectl set-timezone Europe/Moscow  # заменить на нужную
date
```

---

## Часть 2: Установка OpenClaw

### Шаг 3: Установка Node.js

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
node --version   # v24.x.x
```

macOS: `brew install node@24`

### Шаг 4: Установка OpenClaw

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
# или
npm i -g openclaw@latest
```

### Шаг 5: Онбординг

```bash
openclaw onboard --install-daemon
```

### Шаг 6: Проверка

```bash
openclaw gateway status  # running, port 18789
```

---

## Часть 3: Настройка Ollama

### Шаг 7: Установка Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama && sudo systemctl start ollama

# macOS
brew install ollama
```

### Шаг 8: Скачивание моделей

```bash
ollama pull qwen2.5:7b   # 8 GB RAM
ollama pull qwen2.5:14b  # 16+ GB RAM
ollama pull nomic-embed-text  # обязательно для эмбеддингов
ollama list
```

### Шаг 9: Настройка провайдера Ollama в OpenClaw

В `~/.openclaw/openclaw.json` → `models.providers`:

```json
"ollama": {
  "baseUrl": "http://127.0.0.1:11434",
  "api": "ollama",
  "models": [
    {
      "id": "qwen2.5:14b",
      "name": "Qwen 2.5 14B (Local)",
      "api": "ollama",
      "input": ["text"],
      "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 131072,
      "maxTokens": 8192
    }
  ]
}
```

---

## Часть 4: Настройка памяти и эмбеддингов

### Шаг 10: Настройка memorySearch

В `~/.openclaw/openclaw.json` → `agents.defaults`:

```json
"memorySearch": {
  "provider": "ollama",
  "remote": { "baseUrl": "http://localhost:11434" },
  "model": "nomic-embed-text",
  "queryInputType": "query",
  "documentInputType": "passage"
}
```

### Шаг 11: Создание структуры памяти

```bash
mkdir -p ~/.openclaw/workspace/memory
cat > ~/.openclaw/workspace/MEMORY.md << 'EOF'
# MEMORY.md — {DISPLAY_NAME}
EOF
```

### Шаг 12: Настройка политики памяти

Создать `~/.openclaw/workspace/MEMORY-POLICY.md` — стандартная политика (daily dump, Keychain для паролей, APPEND only, memory_search перед "не знаю").

### Шаг 13: Настройка QMD (опционально)

```json
"memory": {
  "backend": "qmd",
  "citations": "auto",
  "qmd": {
    "includeDefaultMemory": true,
    "sessions": { "enabled": true, "retentionDays": 90 },
    "update": { "interval": "5m", "debounceMs": 15000 },
    "limits": { "maxResults": 6, "timeoutMs": 4000 }
  }
}
```

---

## Часть 5: Создание первого бота

### Шаг 14: Получить Telegram-токен

@BotFather → `/newbot` → копировать токен.

### Шаг 15: Создать workspace бота

```bash
mkdir -p ~/.openclaw/workspace-{agent_id}
```

**SOUL.md** — личность бота (со встроенным онбордингом):

```markdown
# SOUL.md — {DISPLAY_NAME}

## Кто я

{DISPLAY_NAME} — корпоративный AI-помощник. Работаю так: вы ставите задачу — я выполняю. Если чего-то не умею — научусь прямо в диалоге.

## Стиль

- Профессиональный, но дружелюбный
- Краткий и по делу
- Русский язык по умолчанию
- Технические термины как есть

## Принципы

- Точность > скорость
- Приватные данные не покидают машину
- Всегда уточнять если не уверен
- Если не умею — честно говорю и предлагаю научиться

## Онбординг (первое сообщение)

При первом сообщении от пользователя — представиться по шаблону в AGENTS.md → Онбординг.
Онбординг состоит из 3 шагов:
1. Представление + лестница возможностей (работает сейчас / можно подключить / разработаем с нуля)
2. Вопрос о контексте клиента (роль, задачи, приоритеты)
3. Первая польза — сразу сделать что-то полезное в первом диалоге

## Лестница возможностей

**Работает прямо сейчас:**
- Ответить на любой вопрос — с поиском в интернете или по истории переписки
- Сделать сводку из длинного текста, переписки или документа
- Найти нужное в истории — когда, кто, что обсуждали
- Напомнить о важном — в нужное время, в нужный день
- Помочь с текстом — письмо, отчёт, протокол, таблица

**Можно подключить:**
- Корпоративная почта — я сам читаю входящие и делаю сводки
- Календарь — слежу за встречами, готовлю повестки
- CRM/таблицы — ищу данные, обновляю статусы
- Teams/Slack — мониторю каналы, не даю пропустить важное

**Разработаем с нуля:**
- Любой сценарий автоматизации — опишите, что повторяется каждый день
- Парсинг данных с любых источников
- Регулярные отчёты по графику
- Интеграции с любыми сервисами по API

**Логика:** если задача повторяется больше двух раз — её можно автоматизировать.
```

**AGENTS.md** — роли и правила (со встроенным онбордингом):

```markdown
# AGENTS.md — {DISPLAY_NAME}

## Роль

{Одно предложение — роль бота}

## Session Startup

1. Read SOUL.md — это кто ты
2. Read USER.md — это кто тебе пишет
3. Check HEARTBEAT.md if exists

## Онбординг

### Первое сообщение от пользователя

При первом контакте (новая сессия, пользователь пишет впервые) — представиться:

    Привет, {USER_NAME}! 👋 Я — {DISPLAY_NAME}, ваш AI-помощник.

    Я работаю так: вы ставите задачу — я выполняю. Если чего-то не умею — научусь прямо в диалоге.

    🟢 Что работает прямо сейчас:
    • Ответить на любой вопрос — с поиском в интернете или по нашей переписке
    • Сделать сводку из длинного текста, переписки или документа
    • Найти нужное в истории — когда, кто, что обсуждали
    • Напомнить о важном — в нужное время, в нужный день
    • Помочь с текстом — письмо, отчёт, протокол, таблица

    🔵 Что можно подключить:
    • Корпоративная почта — я сам читаю входящие и делаю сводки
    • Календарь — слежу за встречами, готовлю повестки
    • CRM/таблицы — ищу данные, обновляю статусы
    • Teams/Slack — мониторю каналы, не даю пропустить важное

    🟣 Что разработаем с нуля:
    • Любой сценарий автоматизации — опишите, что повторяется каждый день
    • Парсинг данных с любых источников
    • Регулярные отчёты по графику
    • Интеграции с любыми сервисами по API

    Логика простая: если задача повторяется больше двух раз — её можно автоматизировать.

    ---

    Чтобы я был максимально полезен — расскажите немного о себе:

    1. Чем занимаетесь? (роль, компания)
    2. Какие задачи отнимают больше всего времени каждый день?
    3. Что из перечисленного хотелось бы попробовать прямо сейчас?

### Второе сообщение (после ответа клиента)

Клиент ответил на вопросы → адаптироваться:
- Запомнить контекст (роль, задачи, приоритеты) в memory
- Предложить конкретный первый сценарий based on ответов
- Если клиент назвал почту → предложить подключить почту
- Если клиент назвал документы → предложить скинуть документ для сводки прямо сейчас
- Если клиент назвал рутину → предложить автоматизацию
- Цель: дать первую пользу в онбординге, не просто разговор

### Последующие сообщения
Отвечать нормально, без повторного онбординга.

## Зона ответственности

- Обработка запросов пользователя
- Работа с текстами, документами, письмами
- Аналитика и сводки
- Напоминания и задачи
- Разработка новых навыков в диалоге

## Что НЕ делать

- Не отправлять данные наружу
- Не менять конфиги без подтверждения
- Не придумывать — если не знаю, честно говорю

## Алерты

- 🔴 CRITICAL → сразу писать владельцу
- 🟡 WARNING → логировать + писать если повторяется
- 🟢 INFO → только в лог
```

**IDENTITY.md**:

```markdown
# IDENTITY.md

- **Name:** {DISPLAY_NAME}
- **Creature:** Corporate AI assistant
- **Vibe:** Professional, friendly, capable
- **Emoji:** 🤖
```

**USER.md**:

```markdown
# USER.md

- **Name:** {имя владельца}
- **Telegram:** {username}
- **Timezone:** {таймзона}
- **Role:** Owner
```

**MEMORY.md**: `# MEMORY.md — {DISPLAY_NAME}`

### Шаг 16: Настроить openclaw.json

**agents.list:**

```json
{
  "id": "{agent_id}",
  "name": "{DISPLAY_NAME}",
  "workspace": "~/.openclaw/workspace-{agent_id}",
  "model": { "primary": "ollama/glm-5.2:cloud", "fallbacks": ["ollama/glm-5.1:cloud"] }
}
```

**channels.telegram.accounts:**

```json
"{agent_id}": {
  "name": "{DISPLAY_NAME}",
  "dmPolicy": "allowlist",
  "botToken": "{ТОКЕН}",
  "allowFrom": [{TELEGRAM_USER_ID}],
  "groupPolicy": "allowlist",
  "streaming": { "mode": "partial" }
}
```

**bindings:**

```json
{
  "type": "route",
  "agentId": "{agent_id}",
  "match": { "channel": "telegram", "accountId": "{agent_id}" }
}
```

⚠️ Все три секции обязательны! Без binding сообщения уйдут в main-бот.

### Шаг 17: Перезапустить gateway

```bash
openclaw gateway restart
```

### Шаг 18: Проверить

```bash
openclaw agents list
ls ~/.openclaw/agents/{agent_id}/sessions/
# Должно быть: agent:{agent_id}:telegram:direct:{user_id}
```

---

## Часть 6: Настройка fallback-моделей

**ТОЛЬКО cloud-модели. ❌ НЕ использовать локальные модели как fallback.**

```json
"model": {
  "primary": "ollama/glm-5.2:cloud",
  "fallbacks": ["ollama/glm-5.1:cloud"]
}
```

### ⚠️ Ollama cloud — авторизация через SSH-ключ

#### macOS (просто):

Ollama работает под текущим пользователем, ключи в `~/.ollama/`:

```bash
scp ~/.ollama/id_ed25519 user@host:~/.ollama/id_ed25519
scp ~/.ollama/id_ed25519.pub user@host:~/.ollama/id_ed25519.pub
# Перезапустить Ollama
```

#### Linux (КРИТИЧНО — другой пользователь!):

Ollama на Linux работает под пользователем **`ollama`** (home: `/usr/share/ollama/`), НЕ под `root`.

**❌ НЕ класть ключи в `/root/.ollama/` — Ollama их не увидит!**
**✅ Кладём в `/usr/share/ollama/.ollama/`**

```bash
scp ~/.ollama/id_ed25519 root@host:/tmp/
scp ~/.ollama/id_ed25519.pub root@host:/tmp/
ssh root@host 'mkdir -p /usr/share/ollama/.ollama && \
  cp /tmp/id_ed25519 /usr/share/ollama/.ollama/ && \
  cp /tmp/id_ed25519.pub /usr/share/ollama/.ollama/ && \
  cp /root/.ollama/.env /usr/share/ollama/.ollama/ 2>/dev/null || true && \
  chown -R ollama:ollama /usr/share/ollama/.ollama/ && \
  chmod 600 /usr/share/ollama/.ollama/id_ed25519 && \
  chmod 644 /usr/share/ollama/.ollama/id_ed25519.pub && \
  systemctl restart ollama'
```

**Проверка:**

```bash
curl -s http://127.0.0.1:11434/api/chat -d \
  '{"model":"glm-5.2:cloud","messages":[{"role":"user","content":"hi"}],"stream":false}' | head -3
# Должна вернуть JSON с "content", НЕ "Unauthorized"
```

Без этого cloud-модели отдают **401 Unauthorized**. Проверить пользователя: `grep User /etc/systemd/system/ollama.service`, `getent passwd ollama`.

---

## 🚀 Быстрый деплой (готовые скрипты)

### macOS:
```bash
scp scripts/deploy-openclaw-macos.sh user@host:/tmp/
scp ~/.ollama/id_ed25519 user@host:~/.ollama/id_ed25519
scp ~/.ollama/id_ed25519.pub user@host:~/.ollama/id_ed25519.pub
ssh user@host 'BOT_TOKEN=*** OWNER_TG_ID=12345 bash /tmp/deploy-openclaw-macos.sh'
```

### Linux:
```bash
scp scripts/deploy-openclaw-linux.sh user@host:/tmp/
scp ~/.ollama/id_ed25519 user@host:/tmp/id_ed25519
scp ~/.ollama/id_ed25519.pub user@host:/tmp/id_ed25519.pub
ssh user@host 'BOT_TOKEN=*** OWNER_TG_ID=12345 bash /tmp/deploy-openclaw-linux.sh'
```

⚠️ **На Linux скрипт должен сам скопировать ключи из /tmp/ в /usr/share/ollama/.ollama/ с chown ollama:ollama.**

---

## ⚠️ КРИТИЧНО: Управление контекстом сессии

При SSH-работе на удалённом сервере контекст сессии быстро раздувается → timeout модели → reset.

### Правила:

1. **НЕ выполнять SSH-команды по одной** — писать скрипт, scp, запускать одним bash
2. **Использовать `sessions_spawn`** для тяжёлых SSH-задач
3. **Лимит: ~30 SSH-команд на сессию** — после контекст ~150K, модель таймаутит
4. **OpenClaw reset после 3 ошибок подряд** — нормальное поведение
5. **glm-5.2:cloud** стабильнее при большом контексте, **glm-5.1:cloud** таймаутит при 150K+
6. При работе через бастион — минимизировать round-trip команд

### Скрипт-шаблон:

```bash
cat > /tmp/setup.sh << 'SCRIPT'
#!/bin/bash
set -e
# ... все команды ...
SCRIPT
scp /tmp/setup.sh user@host:/tmp/
ssh user@host 'bash /tmp/setup.sh'
```

### Reverse tunnel (нестандартная топология):
- Туннель: `ssh -p 22 -N -R 2722:localhost:22 root@bastion_host`
- Доступ: `ssh -p 2722 user@bastion_host`
- Для автоподдержки: autossh или LaunchAgent

---

## Частые ошибки

1. **Нет binding** — сообщения идут в main. Всегда добавляйте binding.
2. **Нет streaming config** — добавьте `"streaming": {"mode": "partial"}`.
3. **dmPolicy "pairing"** — используйте "allowlist" с explicit allowFrom.
4. **Ollama не запущена** — `ollama list`, при ошибке `ollama serve`.
5. **Эмбеддинги не работают** — проверьте `nomic-embed-text`.
6. **LaunchAgents не созданы** — установщик НЕ создаёт LaunchAgent (macOS). Вручную.
7. **PATH не включает /opt/homebrew/bin** (macOS) — openclaw/node не работают после перезагрузки.
8. **models.json отсутствует** — бот не отвечает без него.
9. **Permissions ~/.openclaw/ = 755** — должно быть 700.
10. **Нет ownerAllowFrom** — команды не работают.
11. **Gateway auth.mode=token ломает Telegram polling** — использовать mode=none для local.
12. **519 SSH-команд** — контекст 152K, timeout, reset. Лимит ~30, потом spawn.
13. **glm-5.1:cloud при 150K+** — `This operation was aborted`. Используйте glm-5.2:cloud.
14. **plugins.entries.ollama.config.apiKey** — НЕ поддерживается, ломает конфиг → crash loop.
15. **Cloud-модели 403** — `this model requires a subscription`. Ставить local primary.
16. **Ollama на Linux под пользователем `ollama`** — ключи в `/usr/share/ollama/.ollama/`, НЕ `/root/.ollama/`. Иначе 401 Unauthorized. Проверить: `grep User /etc/systemd/system/ollama.service`.
17. **channels.telegram: "bindings" не валиден** — использовать `accounts.default.botToken` + `allowFrom`.
18. **agents.list: "authProfiles" не валиден** — не добавлять, Telegram auth через channel config.
19. **extensions как файл** — должен быть директорией.
20. **Ollama baseUrl localhost vs 127.0.0.1** — использовать 127.0.0.1! localhost может резолвиться в IPv6.

## Улучшение скилла через инсайты

После каждого деплоя — записать уроки в `memory/YYYY-MM-DD.md`. Если инсайт подтверждён на 2+ машинах → добавить в «Частые ошибки». Не раздувать, не дублировать.

---

## Часть 7: Защита сессии

### Save-Game МГНОВЕННО
Получил credentials → в том же ходе: 1) Keychain → 2) MEMORY.md → 3) продолжать.

### Верификация токенов
```bash
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('ok') else 'FAIL')"
python3 -c "import json; json.load(open('openclaw.json'))" && echo '✅' || echo '❌'
```

### Не слать сырые ошибки
Технические ошибки — только в лог. В чат: что случилось + что делаю + через сколько вернусь.

---

## Часть 8: Smoke Tests

1. **Сервисы:** `systemctl is-active openclaw && systemctl is-active ollama`
2. **Модели:** `curl -s http://127.0.0.1:11434/api/chat -d '{"model":"glm-5.2:cloud","messages":[{"role":"user","content":"hi"}],"stream":false}'` — не "Unauthorized"
3. **Порт:** `ss -tlnp | grep 18789`
4. **Бот:** `curl -s "https://api.telegram.org/bot${TOKEN}/getMe"`
5. **Логи:** `journalctl -u openclaw -n 50 | grep -iE 'error|fatal'`
6. **Онбординг:** написать боту первое сообщение — должен представиться и рассказать о возможностях

---

## Часть 9: 7-Day Monitoring (чужой сервер)

Healthcheck скрипт на 7 дней: OpenClaw alive, Ollama alive, port listening. Автоудаление через 7 дней.

---

## Часть 10: Credentials на Linux

Keychain только на macOS. На Linux: `pass` (GPG), `openssl enc`, или `chmod 600`. Никогда не писать пароли в .md.

---

## Часть 11: Skill Installation (3-level validation)

1. Файл: SKILL.md существует, > 100 байт
2. Symlink: агент видит через `~/.openclaw/agents/*/agent/skills/`
3. После рестарта: сервис жив, скиллы загружены

---

## Часть 12: Memory Management & Session Health

В `openclaw.json`:

```json
{
  "session": { "maintenance": { "mode": "enforce", "pruneAfter": "7d", "maxEntries": 60 } },
  "cron": { "sessionRetention": "24h" }
}
```

Daily restart cron на 04:05. Embedding timeout 600s для больших стораджей. Мониторить `openclaw status` (< 60 sessions).

Quick fix: `openclaw sessions cleanup --all-agents --enforce && openclaw gateway restart`

---

## Часть 13: Стандартный онбординг (MIT / Jarvis боты)

### Принцип

Каждый бот при **первом сообщении** не просто представляется — он вовлекает клиента в диалог, узнаёт контекст и даёт первую пользу прямо в онбординге.

### 3 шага онбординга

**Шаг 1 — Представление + лестница возможностей:**
- Бот представляется по имени
- Показывает 3 уровня: 🟢 работает сейчас / 🔵 можно подключить / 🟣 разработаем с нуля
- Ключевая логика: «если задача повторяется больше двух раз — её можно автоматизировать»
- Задаёт 3 вопроса: роль, времязатратные задачи, что попробовать прямо сейчас

**Шаг 2 — Адаптация:**
- Клиент отвечает → бот запоминает контекст в memory
- Предлагает конкретный первый сценарий based on ответов
- Если клиент назвал почту → предлагает подключить
- Если документы → предлагает скинуть документ для сводки прямо сейчас
- Если рутину → предлагает автоматизацию

**Шаг 3 — Первая польза:**
- Бот делает что-то полезное прямо в первом диалоге
- Сводка, поиск, напоминание — что-то конкретное
- Клиент уходит с ощущением «это работает»

### Лестница возможностей

| Уровень | Что | Примеры |
|---------|-----|--------|
| 🟢 Работает сейчас | Из коробки | Вопросы, сводки, поиск по истории, напоминания, тексты |
| 🔵 Можно подключить | Настройка интеграции | Почта, календарь, CRM, Teams/Slack |
| 🟣 Разработаем с нуля | Кастомная разработка | Автоматизация рутины, парсинг, отчёты по графику, API |

### Реализация

Онбординг **встроен в шаблоны** SOUL.md и AGENTS.md в Шаге 15:
- **SOUL.md** — секции «Онбординг» (3 шага) и «Лестница возможностей» (3 уровня)
- **AGENTS.md** — секция «Онбординг» с точным шаблоном первого сообщения, вторым сообщением (адаптация) и последующими

### Переменные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `{DISPLAY_NAME}` | Имя бота (IDENTITY.md) | MIT Assistant, Jarvis |
| `{USER_NAME}` | Имя пользователя (USER.md) | Diana, Vadim |

### Для каких ботов

Онбординг встроен по умолчанию для **всех** ботов: MIT Assistant, Jarvis, кастомные. Шаблоны в Шаге 15 уже содержат онбординг — не нужно добавлять отдельно.

---

## Чеклист установки (полный)

- [ ] SSH доступ работает
- [ ] Система обновлена, таймзона правильная
- [ ] Node.js установлен (v24+)
- [ ] OpenClaw установлен и gateway запущен
- [ ] Ollama установлена и работает
- [ ] Модель скачана + nomic-embed-text
- [ ] ⚠️ Ollama cloud SSH-ключи в правильном месте (macOS: ~/.ollama/, Linux: /usr/share/ollama/.ollama/)
- [ ] ⚠️ Cloud-модель проверена: `curl api/chat` отвечает, не 401
- [ ] memorySearch настроен
- [ ] Структура памяти создана (memory/, MEMORY.md, MEMORY-POLICY.md)
- [ ] Telegram-токен получен и верифицирован (getMe OK)
- [ ] Workspace создан (SOUL с онбордингом, AGENTS с онбордингом, IDENTITY, USER, MEMORY)
- [ ] Агент + Telegram account + binding добавлены
- [ ] ⚠️ LaunchAgent (macOS) / systemd (Linux) создан
- [ ] ⚠️ PATH включает /opt/homebrew/bin (macOS)
- [ ] ⚠️ ~/.openclaw permissions = 700
- [ ] ⚠️ ownerAllowFrom настроен
- [ ] JSON проверен перед рестартом
- [ ] Gateway перезапущен
- [ ] ⚠️ Memory health: pruneAfter 7d, maxEntries 60, sessionRetention 24h
- [ ] ⚠️ Daily restart cron на 04:05
- [ ] Smoke tests пройдены (6 тестов)
- [ ] ⚠️ Онбординг проверен: бот представился при первом сообщении
- [ ] 7-day monitoring (если чужой сервер)
- [ ] Машина в INFRASTRUCTURE_REGISTRY.md
- [ ] Креды в Keychain/pass (НЕ в .md)
- [ ] Запись в memory/YYYY-MM-DD.md
- [ ] Сообщения идут в правильного бота