# Architecture Council — Completeness Review (Release v0.2.0)

**Project:** The Jarvice v0.1.3 → v0.2.0  
**Reviewer:** Friday (Completeness Lens)  
**Date:** 2026-05-21  
**Principle:** "Что может сломаться? Где слепые зоны? Какие векторы атак?"

---

## 1. ✅ Утверждённые решения

- **System crontab** с маркером `# the-jarvice-managed` — проще чем launchd, работает на Linux тоже
- **Bash setup script** — курино-яичная проблема с Python setup.py, bash правильный выбор
- **Progressive Disclosure wizard** — 3 уровня снижают когнитивную нагрузку
- **Идемпотентность setup** — проверять перед установкой, не перезаписывать config

---

## 2. 🔴 CRITICAL — Что сломается

### C-01: Ollama не запущен в момент cron job

Cron job запускается в 7:00. Если Ollama не запущен — сводка не генерируется, пользователь не получает уведомление.

**Фикс:** `run --once` должен:
1. Проверить Ollama доступность перед началом
2. Если Ollama недоступен — логировать ошибку + отправить Telegram уведомление "⚠️ Ollama не запущен, сводка не сгенерирована"
3. Не молчать — пользователь должен знать что пошло не так

### C-02: Setup script — нет rollback

Если setup.sh падает на середине (например, Ollama не скачивается из-за сети), нет способа откатить частичную установку. Пользователь остаётся с поломанным состоянием.

**Фикс:**
1. `trap cleanup EXIT` в setup.sh — удалить venv если pip install не завершился
2. `--check` режим — проверить что всё установлено без модификаций
3. Явные сообщения об ошибках с инструкциями по ручному фиксу

### C-03: Keyring backend может быть недоступен

На Linux без `libsecret` или на macOS без KeychainUnlock — keyring.get_password() зависает или возвращает None. Конфигуратор спросит пароль, сохранит в keyring, но при следующем запуске keyring не сможет его прочитать.

**Фикс:**
1. `doctor` должен проверять keyring backend (уже есть `check_keyring()`)
2. setup.sh должен устанавливать `libsecret-1-0` на Linux
3. При keyring failure — автоматический fallback на env vars с предупреждением

---

## 3. 🟡 WARNING — Что может сломаться

### W-01: Timezone→crontab конвертация

Пользователь в Калининграде (UTC+2) указывает "07:00 утренняя сводка". Но crontab работает в системном timezone. Если системный timezone = UTC, cron запустится в 07:00 UTC = 09:00 MSK = 07:00 KGD. Но если системный timezone = MSK, то 07:00 MSK = 05:00 KGD.

**Фикс:** Явно конвертировать пользовательский timezone в crontab entries, или всегда использовать системный timezone с предупреждением.

### W-02: Partial config — wizard прерван на середине

Если пользователь нажимает Ctrl+C на шаге 2/3, config.yaml может быть создан с неполными данными. Последующий `run --once` упадёт с ошибкой.

**Фикс:** 
1. Сохранять config в temp файл, перемещать только после успешного завершения
2. При обнаружении partial config — предлагать `configure --reauth`

### W-03: Telegram rate limit при cron ошибке

Если Ollama падает 3 раза подряд, и каждый раз отправляется Telegram уведомление об ошибке — можно упереться в rate limit Telegram API (30 msg/sec, но 20 msg/min в группу).

**Фикс:** Rate limit для ошибочных уведомлений — не более 1 в 5 минут.

### W-04: --non-interactive режим для CI/CD

setup.sh и configure wizard — интерактивные. Нет способа запустить их неинтерактивно (для Docker, CI/CD, Ansible).

**Фикс:** Добавить `--non-interactive` флаг: `configure --non-interactive --email=user@corp.ru --password=xxx --bot-token=xxx`

### W-05: Doctor не проверяет cron

`doctor` проверяет Ollama, Keyring, Config — но не проверяет активен ли cron job.

**Фикс:** Добавить 12-ю проверку: `check_cron()` — проверяет что crontab содержит `# the-jarvice-managed` entries.

---

## 4. 🔵 INFO — Хорошо бы иметь

### I-01: VERSION файл — path resolution при pip install

`_VERSION_FILE = Path(__file__).parent.parent / "VERSION"` — работает при `pip install -e .`, но может не работать при `pip install the-jarvice` (package data не включён).

**Фикс:** Использовать `importlib.metadata.version("the-jarvice")` как fallback.

### I-02: Sync requests в providers.py

`OllamaProvider.summarize()` использует `requests.post()` — синхронный вызов. При cron запуске это ОК, но при未来发展 (web UI) понадобится async.

**Фикс:** Не сейчас, но добавить TODO комментарий.

### I-03: Model download confirmation

`ollama pull qwen3:14b` скачивает 8.6 GB без подтверждения. На медленном соединении это может занять 30+ минут.

**Фикс:** Показать размер и спросить подтверждение перед скачиванием.

---

## 5. 🔍 Слепые зоны

### BS-01: Upgrade path

Нет команды `the-jarvice upgrade`. Если пользователь установил v0.1.0 и хочет v0.2.0 — нужно ли запускать setup.sh заново? Миграция config.yaml?

**Рекомендация:** `pip install -e . --upgrade` + `the-jarvice doctor` для проверки. В setup.sh — проверка версии.

### BS-02: OpenClaw cron conflict

Если Jarvis использует OpenClaw cron для сводок, а The Jarvice создаёт system crontab — возможен дублирующий запуск.

**Рекомендация:** Проверять наличие OpenClaw cron перед созданием crontab entry. Если OpenClaw cron активен — не создавать дублирующий.

### BS-03: PII path nesting

`PIIConfig` проверяет что пути внутри `~/.the-jarvice/`. Но если `~/.the-jarvice/` — симлинк на другой раздел, `realpath()` резолвит его, и путь может оказаться вне `~/.the-jarvice/`.

**Рекомендация:** Проверять и base path через `realpath()`.

### BS-04: Telegram rate limit при массовой отправке

Если `chunk_html()` разбивает сводку на 5 сообщений, а cron запускается 2 раза в день — 10 сообщений/день. Это безопасно. Но если пользователь запускает `run` вручную 10 раз — 50 сообщений, что может быть rate limited.

**Рекомендация:** Добавить минимальный интервал между Telegram отправками (1 сек).

---

## 6. 🛡️ Векторы атак при установке

| Вектор | Угроза | Защита |
|--------|--------|--------|
| `curl \| bash` setup.sh | MITM, подмена скрипта | HTTPS + checksum verification |
| pip install из PyPI | Зависимости с уязвимостями | pin versions в requirements.txt |
| Ollama model pull | Подмена модели | SHA256 verification (ollama делает это) |
| Keyring access | Другие приложения читают креды | macOS Keychain ACL, Linux keyring permissions |
| config.yaml в ~/.the-jarvice/ | Чтение конфига другими пользователями | chmod 600 на config.yaml |
| setup.sh запускает brew install | Установка нежелательных пакетов | Показать что будет установлено перед запуском |
| Telegram bot token в Keychain | Токен утечка | keyring backend encryption, не в config.yaml |

---

## Verdict

**✅ APPROVE with conditions**

v0.2.0 можно релизить если закрыть 3 CRITICAL:
1. Ollama healthcheck в cron job + уведомление об ошибке
2. Setup script rollback на частичной установке
3. Keyring backend проверка в doctor и setup

**Track для v0.2.1:** W-01 (timezone), W-02 (partial config), W-04 (--non-interactive)

*Friday — Completeness Lens — Architecture Council — 2026-05-21*