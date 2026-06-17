# Architecture Council — Release Pragmatism Review

**Проект:** The Jarvice v0.1.3 → v0.2.0  
**Рецензент:** Pragmatism Lens (🛠️)  
**Дата:** 2026-05-21  
**Принцип:** «Что НЕ делать? Где YAGNI? Какова стоимость поддержки?»  
**Контекст:** 4 блокера релиза: Configure Wizard, Setup Script, README + Quick Start, enable/disable cron

---

## 1. ✅ Утверждённые решения — Простые, поддерживаемые

### Setup Script — bash, а не Python

Текущий `setup/setup.sh` (267 строк) — правильный выбор для v0.2.0. Bash-скрипт установки — индустриальный стандарт (Homebrew install, rustup, nvm). Преимущества:

- **Не требует Python для запуска** — это важно: venv создаётся *внутри* скрипта
- **Идемпотентность** реализована через проверки `if [ -d ... ]` / `if command_exists ...` — просто и читаемо
- **Zero runtime dependency**: bash есть на каждой macOS из коробки
- **Поддержка**: любой DevOps-инженер прочитает bash setup.sh без документации

Python-альтернатива (`setup.py` на Typer) потребовала бы: отдельный entry_point или `python3 setup.py`, что создаёт курино-яичную проблему — Python ещё не установлен или venv ещё не создан. А `pip install` уже использует Python — но он вызывается *из bash-скрипта*, не заменяет его.

**Вердикт:** ✅ Bash для setup — правильно. Не переписывать на Python.

### README — текущая структура достаточна

Существующий README (290 строк) уже содержит:
- Quick Start (6 команд)
- CLI Reference с таблицами флагов
- Architecture diagram
- Key Directories, Credentials, Data Flow
- Development section

Для «5 минут до первой сводки» нужно 6 команд в Quick Start — они уже есть. Добавлять Quick Start Guide отдельным файлом не нужно — секция в README достаточно.

**Вердикт:** ✅ Не создавать отдельный QUICK_START.md. Улучшить Quick Start секцию в README — добавить ожидаемое время каждого шага и troubleshooting для 2-3 частых ошибок.

### Keyring-first credential storage

Пароли и токены в macOS Keychain через `keyring`, не в config.yaml — это правильный, безопасный, macOS-native подход. Не менять.

**Вердикт:** ✅ Утверждено без изменений.

---

## 2. ⚡ Проблемы — Over-engineering и YAGNI

### 🚨 Configure Wizard — 3 уровня Progressive Disclosure — это over-engineering для v0.2.0

**Спецификация Sprint 004** предлагает три уровня:
- Level 0 (default): 3 поля (email, password, bot token)
- Level 1 (`--models`): выбор провайдера + API key
- Level 2 (`--advanced`): temperature, max_tokens, custom endpoints

**Проблема:** Текущий `configure()` уже работает. Он последовательно проводит через 5 шагов: Exchange → Teams → Telegram → Model → Schedule. Каждый шаг можно пропустить через `--skip-*`. Есть `--reauth` для повторной настройки одного сервиса. Это **уже Progressive Disclosure** — просто не разложено на три отдельных функции.

**YAGNI-анализ:**
- Level 1 (`--models`) нужен только когда появится cloud provider support. Сейчас единственный провайдер — Ollama. Выбор из одного варианта — не wizard, а confirmation.
- Level 2 (`--advanced`) — это temperature, max_tokens, custom endpoints. Пользователь v0.2.0 не будет менять эти параметры. Это power-user настройки для v0.3.0+.
- Refactor на `_configure_basic()`, `_configure_models()`, `_configure_advanced()` — это 3 новые функции + 3 новых флага CLI + 3 уровня UX. Стоимость: ~200 строк нового кода для фичи, которую никто не попросит в v0.2.0.

**Рекомендация:** 
1. Оставить текущий `configure()` как есть — он уже работает
2. Добавить `--quick` флаг, который пропускает всё кроме Exchange + Telegram (2 шага вместо 5) — это 10 строк кода
3. Cloud provider support (Level 1) — отложить до v0.3.0, когда реально появится OpenAI/Anthropic
4. Advanced настройки (Level 2) — отложить до v0.4.0

**Стоимость текущего подхода:** 0 строк нового кода.  
**Стоимость Progressive Disclosure:** ~200 строк + 3 новых CLI флага + 3 функции + тесты.

### 🚨 Provider Abstraction — YAGNI для v0.2.0

Sprint 004 специфицирует `ModelProvider` ABC с `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`. На момент v0.2.0 единственный провайдер — Ollama. Создавать ABC для одного наследника — классический YAGNI.

**Что нужно сейчас:**
- `_generate_summary()` в `main.py` вызывает Ollama через `requests.post()` — это 60 строк
- Вынести в `core/summarizer.py` как `def summarize(text, config) -> str` — 30 минут рефакторинга

**Что НЕ нужно сейчас:**
- ABC с 3 абстрактными методами
- Retry с exponential backoff для cloud API (Ollama локальный — нет rate limits)
- Auto-degradation цепочка провайдеров
- Audit log для cloud-вызовов

**Рекомендация:**
1. Вынести `_generate_summary()` в `core/summarizer.py` как простую функцию — это правильный рефакторинг, не over-engineering
2. Не создавать `ModelProvider` ABC пока не будет второго провайдера
3. Cloud provider support — весь Sprint 004 item 2 — отложить до v0.3.0

### ⚠️ `the-jarvice model switch` / `model list` — преждевременные команды

Две новые CLI-команды для единственного провайдера (Ollama) с 1-2 моделями. `model list` — это `ollama list` в обёртке. `model switch` — это редактирование `config.yaml` для смены `models.primary`.

**Рекомендация:** Отложить до появления cloud провайдеров. Сейчас `the-jarvice configure --reauth model` закрывает кейс смены модели.

### ⚠️ Context Scrubbing Pass (GREEN → CLOUD) — преждевременный

`scrub_for_cloud()` — это ещё один уровень PII-обработки, который нужен **только** при отправке в cloud. Если v0.2.0 работает только с локальным Ollama — этот код мёртвый.

**Рекомендация:** Отложить до v0.3.0 (cloud providers). Текущий RED → GREEN pipeline достаточен для локального использования.

### ⚠️ Audit Log — преждевременный

JSON-аудит-лог (`~/.the-jarvice/audit.log`) для единственного локального провайдера — это запись «я позвал localhost:11434 и получил ответ». Ценность audit log появляется при cloud провайдерах, где есть реальный риск утечки и нужно доказательство что данные не ушли.

**Рекомендация:** Отложить до cloud provider support. Сейчас logging в `~/.the-jarvice/logs/` достаточен.

---

## 3. 🔍 Что НЕ делать — Явные антипаттерны

### ❌ НЕ создавать 3-уровневый wizard для configure

Текущий wizard работает. Разбиение на 3 уровня добавит сложность без пользы. Пользователь v0.2.0 хочет:
```bash
the-jarvice configure  # 5 минут, всё настроено
```
Не хочет:
```bash
the-jarvice configure          # Level 0
the-jarvice configure --models # Level 1
the-jarvice configure --advanced # Level 2
```
Три команды для одной задачи — это не Progressive Disclosure, это Progressive Confusion.

### ❌ НЕ создавать ModelProvider ABC для одного наследника

ABC для одного наследника — это 3 файла, 50+ строк boilerplate, и 0 пользы. Когда появится OpenAI provider — вот тогда и создать ABC, имея 2 реальных наследника. На этом этапе достаточно:

```python
# core/summarizer.py
def summarize(text: str, config: JarviceConfig) -> str | None:
    """Generate summary using configured model provider."""
    # Сейчас — только Ollama
    # v0.3.0 — добавить if/elif для cloud providers
    ...
```

Простой `if/elif` на 2 провайдера читаемее, чем ABC + Registry + Strategy Pattern.

### ❌ НЕ добавлять cron в v0.2.0 через system crontab

Sprint 004 упоминает enable/disable cron как блокер. Но для macOS-only продукта:

- **system crontab** (`crontab -e`) — работает, но хрупкий (не переживает обновления macOS, не видно в System Settings, не логируется в unified log)
- **launchd** — macOS-native, переживает перезагрузки, логируется в system log, виден в System Settings
- **OpenClaw cron** — уже есть в системе, не нужен отдельный cron для The Jarvice

**Рекомендация для v0.2.0:** НЕ добавлять cron/launchd вообще. The Jarvice вызывается через `the-jarvice run --once` из OpenClaw cron, который уже настроен. Enable/disable = включить/выключить OpenClaw cron через `openclaw gateway` — это уже работает.

Если нужен отдельный запуск без OpenClaw — добавить `the-jarvice schedule` в v0.3.0, который создаёт LaunchAgent plist. Но не в релизе.

### ❌ НЕ писать отдельный QUICK_START.md

README уже содержит Quick Start. Дублирование — это двойное поддержание. Лучше улучшить секцию в README:
- Добавить ⏱️ ожидаемое время рядом с каждым шагом
- Добавить troubleshooting для 3 частых проблем (Ollama не стартует, keyring не доступен, Exchange не подключается)

### ❌ НЕ добавлять privacy audit / dry-run / `the-jarvice privacy` в v0.2.0

`--dry-run` уже есть в `the-jarvice run`. Отдельная `privacy audit` команда и `summarize --dry-run` — это дублирование. Для v0.2.0 достаточно `run --dry-run`.

---

## 4. 📊 Оценка стоимости поддержки

### Что вошло в v0.2.0 (блокеры релиза)

| Блокер | Текущий статус | Реальная стоимость | Рекомендация |
|--------|---------------|-------------------|--------------|
| Configure Wizard | Работает (`configure` + 5 шагов + `--skip-*` + `--reauth`) | 0 строк — уже готово | ✅ Не трогать. Добавить `--quick` (10 строк) |
| Setup Script | Работает (`setup.sh` — 267 строк, идемпотентный) | 0 строк — уже готово | ✅ Не трогать |
| README + Quick Start | Работает (290 строк, полная документация) | 0 строк — уже готово | ✅ Добавить ⏱️ и troubleshooting (30 мин правки) |
| enable/disable cron | Не нужно — OpenClaw cron уже работает | 0 строк — не делать | ✅ Использовать OpenClaw cron |

### Что предложено в Sprint 004, но НЕ нужно для релиза

| Фича | Оценка LOC | Стоимость поддержки | Когда делать |
|------|-----------|-------------------|--------------|
| Progressive Disclosure (3 уровня) | ~200 | Высокая — 3 функции, 3 флага, тесты, документация | v0.3.0 (с cloud providers) |
| ModelProvider ABC | ~150 | Высокая — 3 файла, boilerplate, registry | v0.3.0 (с OpenAI provider) |
| Context Scrubbing (GREEN → CLOUD) | ~200 | Средняя — новый pipeline stage | v0.3.0 (с cloud providers) |
| Audit Log | ~100 | Низкая, но бесполезная без cloud | v0.3.0 |
| `model switch/list` команды | ~80 | Низкая | v0.3.0 |
| launchd/cron management | ~150 | Средняя — plist генерация, enable/disable | v0.3.0 |
| Privacy audit / dry-run | ~60 | Низкая — дублирует `run --dry-run` | Не делать — уже есть |

### Итого: v0.2.0 release checklist

**Что делать (2-3 часа работы):**

1. ✅ Вынести `_generate_summary()` из `main.py` в `core/summarizer.py` (30 мин)
2. ✅ Вынести `_deliver_telegram()` из `main.py` в `core/delivery.py` (30 мин)
3. ✅ Добавить `--quick` флаг к `configure` (10 мин)
4. ✅ Добавить ⏱️ время и troubleshooting в Quick Start секцию README (30 мин)
5. ✅ Убрать `graph_api` stub из Teams scraper (из предыдущего ревью) (20 мин)
6. ✅ Убрать дублирующиеся функции в `keyring_utils.py` (из предыдущего ревью) (15 мин)

**Что НЕ делать:**

1. ❌ 3-уровневый Progressive Disclosure wizard
2. ❌ ModelProvider ABC
3. ❌ Context Scrubbing pass
4. ❌ Audit Log
5. ❌ `model switch` / `model list` команды
6. ❌ cron/launchd management
7. ❌ Отдельный QUICK_START.md

---

## 5. Итоговый вердикт

**v0.2.0 готов к релизу СЕЙЧАС.** Четыре блокера — configure wizard, setup script, README, cron — уже реализованы и работают. Sprint 004 пытается запрыгнуть в v0.2.0 с фичами для v0.3.0 (cloud providers, multi-model, advanced config).

**Релизный план:**

```
v0.2.0 (сейчас):
  - Setup script ✅ (уже работает)
  - Configure wizard ✅ (уже работает, добавить --quick)
  - README ✅ (уже работает, добавить ⏱️)
  - Cron ✅ (через OpenClaw, не нужен отдельный)
  - Рефакторинг: summarizer.py, delivery.py, убрать graph_api stubs

v0.3.0 (следующий спринт):
  - Cloud provider support (OpenAI / Anthropic)
  - ModelProvider abstraction (теперь есть 2+ наследника)
  - Progressive Disclosure Level 1 (--models)
  - Context Scrubbing (GREEN → CLOUD)
  - Audit Log
  - the-jarvice model switch/list

v0.4.0:
  - Progressive Disclosure Level 2 (--advanced)
  - launchd schedule management
  - Streaming responses
```

**Принцип:** Ship what works. Don't build frameworks for one user. Don't abstract before you have two implementations. v0.2.0 — это working product, не platform.

---

*«The best code is the code you didn't write. The second best is the code you can delete without anyone noticing.»*