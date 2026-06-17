# Architecture Review: The Jarvice v0.2.0 Release Blockers

**Дата:** 2026-05-21  
**Ревьюер:** System Design (Arch Council)  
**Версия:** v0.1.3 → v0.2.0  
**Статус:** ЧЕРНОВИК — awaiting owner approval

---

## 1. ✅ Утверждённые решения

### 1.1 configure() — Три отдельных wizard-функции + параметризованная обёртка

**Решение:** Рефакторинг монолита `configure()` (~200 строк) в **три самостоятельные функции** + одну параметризованную точку входа.

**Архитектура:**

```
cli/
  main.py              — app, run, doctor, uninstall (без configure)
  configure.py          — configure() (точка входа, уровень определяет что запускать)
  wizards/
    __init__.py
    basic.py            — _wizard_basic()       # Сервисы вкл/выкл + Telegram
    models.py           — _wizard_models()      # Ollama + primary/fallback
    advanced.py         — _wizard_advanced()    # Exchange, Teams, PII, schedule, logging
```

**Почему три, а не одна параметризованная:**

| Критерий | 3 функции | 1 параметризованная |
|---|---|---|
| Тестируемость | ✅ Каждая изолированно | ❌ Ветвления сложнее тестить |
| Читаемость | ✅ Файл < 100 строк | ❌ Монолит растёт |
| Progressive disclosure | ✅ Естественная группировка | ⚠️ Нужен флаг-уровень |
| Переиспользование | ✅ `--reauth exchange` → `_wizard_advanced()` | ⚠️ Параметры протекают |

**Уровни Progressive Disclosure:**

| Уровень | Флаг | Что спрашивает | Целевая аудитория |
|---|---|---|---|
| **Basic** | `--level basic` (default) | Telegram + Ollama check + timezone | Новый пользователь, 3 минуты |
| **Models** | `--level models` | Basic + модель, fallback, system_prompt | Продвинутый, 5 минут |
| **Advanced** | `--level advanced` | Models + Exchange, Teams, PII, logging, schedule | Администратор, 10 минут |

**Ключевой принцип:** каждый уровень включает всё предыдущее + добавляет своё. `--reauth <service>` вызывает только нужную функцию.

**Точка входа `configure()` в `cli/configure.py`:**

```python
@app.command()
def configure(
    level: str = typer.Option("basic", "--level", help="Wizard depth: basic|models|advanced"),
    reauth: Optional[str] = typer.Option(None, "--reauth", help="Re-configure one service"),
    skip_exchange: bool = False,  # скрытые флаги для --reauth
    skip_teams: bool = False,
    skip_telegram: bool = False,
    skip_model: bool = False,
):
    config = load_config()
    
    if reauth:
        return _run_reauth(config, reauth)
    
    if level == "basic":
        _wizard_basic(config)
    elif level == "models":
        _wizard_models(config)
    elif level == "advanced":
        _wizard_advanced(config)
    
    save_config(config)
    _print_summary(config)
```

---

### 1.2 setup.sh — Bash-скрипт (curl|bash), macOS first

**Решение:** `setup.sh` — чистый bash, совместимый с macOS (zsh/bash).

**Почему не Python:**

| Критерий | bash | Python (setup.py) |
|---|---|---|
| curl \| bash | ✅ Естественно | ❌ Нужен Python до запуска |
| Зависимости | ✅ Только sh | ❌ venv/pip/bootstrap |
| Скорость | ✅ Секунды | ⚠️ Медленнее (pip install) |
| Идемпотентность | ✅ Проверка каждого шага | ✅ Аналогично |
| Кроссплатформа | ⚠️ macOS-first, Linux потом | ✅ Проще расширить |
| Откат | ✅ trap + cleanup | ⚠️ Сложнее |

**Структура `setup.sh`:**

```bash
#!/usr/bin/env bash
# The Jarvice — Idempotent setup script
# Usage: curl -fsSL https://.../setup.sh | bash
set -euo pipefail

# Marker для identify/ uninstall
JARVICE_MARKER="# the-jarvice-managed"

# 1. Проверка зависимостей (python3.10+, ollama, keyring)
# 2. Создание venv ~/.the-jarvice/venv
# 3. pip install the-jarvice (или editable для dev)
# 4. Первый запуск configure --level basic
# 5. Установка cron (через marker)
# 6. Проверка: the-jarvice doctor

# Идемпотентность: каждый шаг проверяет результат предыдущего
# trap: откат при ошибке
# Логирование: ~/.the-jarvice/logs/setup.log
```

**Ключевые принципы:**
- **Идемпотентность:** повторный запуск безопасен, каждый шаг с `if ! command_exists` проверкой
- **trap + cleanup:** при прерывании (Ctrl+C) или ошибке — откат созданного venv
- **Логирование:** `set -x` в `~/.the-jarvice/logs/setup.log`, stderr → пользователю
- **marker строка:** `# the-jarvice-managed` в crontab для идентификации
- **macOS-first:** `brew` для зависимостей, `security` для Keychain, LaunchAgent для автозапуска

---

### 1.3 Cron — System crontab с marker

**Решение:** **System crontab** (`crontab -l` / `crontab -`) с маркером `# the-jarvice-managed`.

**Почему не launchd и не OpenClaw cron:**

| Критерий | System crontab | launchd plist | OpenClaw cron |
|---|---|---|---|
| Простота | ✅ Одна строка | ⚠️ XML plist | ⚠️ Нужен OpenClaw |
| Портативность | ✅ Linux + macOS | ❌ macOS only | ❌ Зависимость от OpenClaw |
| Управление | ✅ `crontab -l` + grep | ⚠️ launchctl load/unload | ⚠️ openclaw.json |
| Идемпотентность | ✅ Marker + replace | ✅ Но сложнее | ✅ Нативно |
| Логирование | ✅ `>> logfile 2>&1` | ⚠️ LaunchAgent stderr | ✅ Встроенное |
| Откат | ✅ Удалить строки с marker | ⚠️ unload + delete plist | ⚠️ Из openclaw.json |

**Реализация — команды `enable` / `disable`:**

```python
@app.command()
def enable(
    schedule: str = typer.Option("morning", "--schedule", help="morning|evening|both|weekly"),
) -> None:
    """Enable scheduled summaries via system crontab."""
    from the_jarvice.core.cron import install_cron
    config = load_config()
    install_cron(config, schedule)

@app.command()
def disable() -> None:
    """Disable scheduled summaries."""
    from the_jarvice.core.cron import remove_cron
    remove_cron()
```

**Модуль `the_jarvice/core/cron.py`:**

```python
MARKER = "# the-jarvice-managed"

def install_cron(config: JarviceConfig, schedule: str) -> None:
    """Idempotent: adds/replaces crontab entries with MARKER."""
    existing = _read_crontab()
    # Remove old entries with marker
    filtered = [l for l in existing if MARKER not in l]
    # Add new entries
    new_entries = _build_entries(config, schedule)
    _write_crontab(filtered + new_entries)

def remove_cron() -> None:
    """Remove all the-jarvice entries from crontab."""
    existing = _read_crontab()
    filtered = [l for l in existing if MARKER not in l]
    _write_crontab(filtered)
```

**Формат crontab-записей:**

```crontab
0 7 * * * ~/.the-jarvice/venv/bin/the-jarvice run --once >> ~/.the-jarvice/logs/cron.log 2>&1  # the-jarvice-managed morning
0 19 * * * ~/.the-jarvice/venv/bin/the-jarvice run --once >> ~/.the-jarvice/logs/cron.log 2>&1  # the-jarvice-managed evening
0 9 * * 1 ~/.the-jarvice/venv/bin/the-jarvice run --once --weekly >> ~/.the-jarvice/logs/cron.log 2>&1  # the-jarvice-managed weekly
```

**Перспектива v0.3.0:** Добавить `--launcher launchd` для macOS-специфичного plist, но v0.2.0 — только crontab.

---

### 1.4 README + Quick Start — Обязательные секции

**Решение:** Структура README.md для v0.2.0:

```markdown
# The Jarvice

> Local-first AI assistant for corporate data summaries

## Quick Start (30 seconds)
<!-- curl|bash setup -->

## Features
<!-- Exchange, Teams, PII, Telegram, Ollama -->

## Configuration
<!-- Progressive disclosure: basic → models → advanced -->

## Commands
<!-- the-jarvice configure, run, doctor, enable, disable, version -->

## Architecture
<!-- Pipeline: Scrape → Anonymize → Summarize → Deliver -->

## Requirements
<!-- Python 3.10+, Ollama, macOS -->

## Development
<!-- pip install -e ".[dev]", pytest, ruff -->

## License
<!-- MIT -->
```

**Обязательные секции для v0.2.0:**

1. **Quick Start** — curl|bash, 3 команды до первого результата
2. **Features** — что делает, какие источники, как доставляет
3. **Configuration** — `--level basic|models|advanced` с примерами
4. **Commands** — все CLI-команды с примерами
5. **Requirements** — Python, Ollama, macOS (Linux — coming soon)
6. **Development** — для контрибьюторов

**Quick Start (30 секунд):**

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/.../setup.sh | bash

# Configure (3 minutes)
the-jarvice configure --level basic

# First run
the-jarvice run --once

# Enable daily summaries
the-jarvice enable --schedule both
```

---

## 2. ⚡ Проблемы

### CRITICAL

**C1. configure() — 200-строчный монолит в main.py**
- Файл `cli/main.py` уже 919 строк — бог-объект
- `configure()` смешивает UI (prompts), бизнес-логику (тесты соединений), и persistence (save_config)
- `_generate_summary()` и `_deliver_telegram()` тоже в main.py — должны быть в core/
- **Решение:** Вынести `configure` в `cli/configure.py`, wizards в `cli/wizards/`, summary/delivery в `core/`

**C2. setup.sh — нет rollback механизма в текущем коде**
- uninstall() в main.py удаляет данные, но нет `setup.sh` с `trap` для отката
- **Решение:** Добавить `trap cleanup EXIT ERR` в setup.sh, который при ошибке удаляет `~/.the-jarvice/venv`

**C3. cron — нет валидации timezone/time format в install_cron**
- `ScheduleConfig` валидирует `morning_summary` как `HH:MM`, но crontab нужен `MM HH`
- **Решение:** Конвертация `HH:MM` → `MM HH * * *` с валидацией timezone

### WARNING

**W1. Keyring backend — macOS Keychain только**
- `keyring` на macOS использует Keychain, но на Linux — SecretService/dbus
- setup.sh должен проверять `keyring` backend и предупредить если он не security-focused
- **Решение:** В setup.sh — `python3 -c "import keyring; kr=keyring.get_keyring(); print(kr.__class__.__name__)"` и warn если `NotAKeyring`

**W2. Ollama — нет healthcheck в cron**
- Если Ollama не запущена, cron-job молча провалится
- **Решение:** В cron-записи добавить `|| open ~/.the-jarvice/logs/cron.log` или wrapper-скрипт с проверкой `ollama list` перед запуском

**W3. configure() — нет аналога `--non-interactive` для CI**
- `typer.prompt()` блокируется в CI/CD
- **Решение:** Добавить `--non-interactive` флаг, читающий из env vars: `JARVICE_EXCHANGE_SERVER`, `JARVICE_TELEGRAM_CHAT_ID` и т.д.

**W4. doctor — нет проверки cron**
- `doctor` не проверяет наличие crontab-записей
- **Решение:** Добавить проверку: `crontab -l | grep the-jarvice-managed`

### INFO

**I1. VERSION file — не в package, читается через `Path(__file__).parent.parent.parent`**
- Относительный путь хрупок при разных способах установки (pip, brew, editable)
- **Решение:** В v0.2.0 — оставить как есть, в v0.3.0 — перейти на `importlib.metadata.version("the-jarvice")`

**I2. Pydantic v2 `model_dump()` — сериализует всё, включая defaults**
- `save_config()` пишет все поля, даже если пользователь не менял
- **Решение:** Приемлемо для v0.2.0, но в будущем — `model_dump(exclude_defaults=True)` + merge при загрузке

**I3. `_generate_summary` — синхронный `requests.post` с timeout=120s**
- В cron-контексте 120s таймаут ОК, но в interactive — долгое ожидание
- **Решение:** В v0.2.0 оставить, в v0.3.0 — async с httpx

---

## 3. 🔍 Слепые зоны

### S1. setup.sh — обновление (upgrade path)
- Нет сценария `the-jarvice update` / повторного `setup.sh`
- При повторном запуске setup.sh — что происходит с venv, cron, config?
- **Рекомендация:** Добавить `--upgrade` флаг в setup.sh: `pip install --upgrade the-jarvice`, пересоздать venv при смене Python version, сохранить config

### S2. configure() — partial configuration (прерванный wizard)
- Если пользователь прервал wizard на шаге 3 из 5 — конфиг не сохранён
- **Рекомендация:** Сохранять промежуточный конфиг после каждого уровня. Или — флаг `--dry-run` для просмотра без записи

### S3. cron — конфликт с OpenClaw cron
- Если у пользователя уже есть OpenClaw cron для Jarvis, как The Jarvice cron уживается?
- **Рекомендация:** Проверять `crontab -l` на конфликты перед установкой. Marker `the-jarvice-managed` предотвращает дубли, но не конфликты по времени

### S4. Keyring — multi-backend тестирование
- keyring на macOS → Keychain, на Linux → SecretService (dbus), на CI → plaintext
- setup.sh должен корректно обрабатывать все три сценария
- **Рекомендация:** В setup.sh добавить `keyring diagnose` шаг

### S5. PII path traversal — модель валидации
- `PIIConfig.validate_paths_under_jarvice()` проверяет `realpath`, но не проверяет `red_dir`/`green_dir` на вложенность друг в друга
- **Рекомендация:** Добавить проверку `red_dir != green_dir` и что green не внутри red

### S6. Telegram delivery — rate limiting
- `_deliver_telegram` не имеет retry/backoff при 429 Too Many Requests
- **Рекомендация:** Добавить простой exponential backoff (2s, 4s, 8s) при 429

### S7. doctor — нет проверки pip/venv
- doctor проверяет Ollama, Keyring, Config, но не проверяет что `the-jarvice` установлен корректно в venv
- **Рекомендация:** Добавить проверку `which the-jarvice` и версию

---

## 4. Рекомендации по реализации

### Приоритет P0 (блокеры для v0.2.0)

1. **Рефакторинг configure()** — вынести в `cli/configure.py` + `cli/wizards/`
2. **setup.sh** — написать с нуля, с trap, marker, идемпотентностью
3. **enable/disable cron** — модуль `core/cron.py` + команды в CLI
4. **README.md** — Quick Start + все обязательные секции

### Приоритет P1 (v0.2.0, но не блокеры)

5. **doctor: добавить cron check** — `crontab -l | grep marker`
6. **W2: Ollama healthcheck в cron** — wrapper-скрипт
7. **W3: --non-interactive режим** — env vars для CI

### Приоритет P2 (v0.3.0)

8. **setup.sh --upgrade** — путь обновления
9. **launchd plist** — macOS-нативный планировщик как альтернатива
10. **importlib.metadata** — VERSION через package metadata
11. **async summary generation** — httpx вместо requests

### Порядок реализации

```
Week 1: configure() refactor → wizards → cron.py → enable/disable
Week 2: setup.sh → README → doctor cron check → integration testing
Week 3: --non-interactive → edge cases → release v0.2.0
```

### Файловая структура после рефакторинга

```
the_jarvice/
  cli/
    __init__.py
    main.py           — app, version, run, doctor, uninstall
    configure.py       — configure() entry point + level routing
    wizards/
      __init__.py
      basic.py         — _wizard_basic()
      models.py        — _wizard_models()
      advanced.py      — _wizard_advanced()
  core/
    config.py          — Pydantic models, load/save (без изменений)
    cron.py             — install_cron(), remove_cron(), MARKER
    state.py            — StateManager (без изменений)
    keyring_utils.py    — get_credential() (без изменений)
    summary.py          — _generate_summary() (из main.py)
    delivery.py          — _deliver_telegram() (из main.py)
  scrapers/             — (без изменений)
  config/               — (без изменений)
setup.sh                — новый файл
README.md               — переписать
```

---

## Итог

Четыре блокера v0.2.0 имеют ясные архитектурные решения:

1. **configure()** → 3 wizard-функции + параметризованная обёртка с `--level`
2. **setup.sh** → bash с trap, marker, идемпотентность, macOS-first
3. **cron** → system crontab с marker `# the-jarvice-managed`, enable/disable команды
4. **README** → Quick Start, Features, Configuration, Commands, Requirements

Главный риск — **C1 (монолитный main.py)**. Рефакторинг 919 строк требует аккуратности, но архитектура ясна. Рекомендую начать с configure.py + wizards/, потом cron.py, потом setup.sh.

Критических слепых зон нет — S1 (upgrade path) и S3 (OpenClaw cron конфликт) можно отложить в v0.3.0.