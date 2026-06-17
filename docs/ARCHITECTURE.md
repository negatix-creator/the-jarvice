# Архитектура The Jarvice v0.2.0

Техническое описание компонентов, потоков данных и дизайна системы.

---

## Обзор системы

The Jarvice — local-first AI-ассистент для корпоративных сводок. Система собирает данные из Exchange и Teams, анонимизирует ПДн, генерирует сводку через локальную LLM и доставляет результат в Telegram.

**Ключевое свойство:** персональные данные никогда не покидают устройство пользователя в открытом виде.

```
┌─────────────────────────────────────────────────────────────────┐
│                        The Jarvice v0.2.0                      │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Exchange │  │  Teams   │  │   PII    │  │    Models     │  │
│  │ Scraper  │  │ Scraper  │  │ Pipeline │  │  (Providers)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │             │                │          │
│       ▼              ▼             ▼                ▼          │
│  ┌────────────────────────┐  ┌──────────┐  ┌─────────────┐   │
│  │     State Manager      │  │ Telegram  │  │   Audit Log  │   │
│  │    (state.json)        │  │ Delivery  │  │ (audit.log)  │   │
│  └────────────────────────┘  └──────────┘  └─────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Config (Pydantic v2)                  │  │
│  │                  config.yaml + Keychain                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Диаграмма компонентов

```
the_jarvice/
├── cli/
│   └── main.py               # Typer CLI: configure, run, doctor, enable, disable, version, uninstall
├── core/
│   ├── config.py              # Pydantic v2 модели конфигурации, загрузка/сохранение YAML
│   ├── state.py               # StateManager: курсоры скрейперов, метаданные
│   ├── doctor.py              # 12 диагностических проверок
│   ├── providers.py           # Абстракция LLM-провайдеров (Ollama, OpenAI, Anthropic)
│   ├── context_scrubber.py    # Скраббинг контекста (standard/strict)
│   ├── log_utils.py           # Очистка логов от секретов
│   ├── keyring_utils.py       # Keychain/keyring + env var fallback
│   └── scraper_base.py        # BaseScraper ABC, ScrapeResult
├── scrapers/
│   ├── _base.py               # Реэкспорт BaseScraper
│   ├── exchange/
│   │   └── scraper.py         # ExchangeScraper: EWS, email + calendar
│   ├── teams/
│   │   └── scraper.py         # TeamsScraper: IC3 token, чаты + встречи
│   └── pii/
│       └── anonymizer.py      # PIIClassifier, MappingManager, Anonymizer, Deanonymizer
├── config/
│   ├── config_schema.yaml    # Шаблон конфигурации
│   └── openclaw_template.json # Шаблон OpenClaw конфига
└── VERSION                     # Единственный источник версии
```

---

## Поток данных

### Основной пайплайн (run --once)

```
1. SCRAPE
   ┌─────────────┐     ┌─────────────┐
   │  Exchange    │     │    Teams    │
   │  Scraper     │     │  Scraper   │
   └──────┬──────┘     └──────┬──────┘
          │                    │
          │  ScrapeResult     │  ScrapeResult
          │  (items, errors)  │  (items, errors)
          ▼                    ▼
   
2. PII PIPELINE
   ┌─────────────────────────────────────┐
   │           Anonymizer                │
   │                                     │
   │  RED (исходные ПДн)                │
   │  ├── {hash}.json (chmod 600)       │
   │  └── mapping.json (chmod 600)      │
   │                                     │
   │  PIIClassifier:                     │
   │  ├── email → [EMAIL_N]             │
   │  ├── phone → [PHONE_N]             │
   │  ├── INN   → [INN_N]              │
   │  ├── SNILS → [SNILS_N]            │
   │  └── Force-mask: sender/recipient  │
   │                                     │
   │  GREEN (анонимизированные)          │
   │  └── {hash}.json                   │
   └──────────────┬──────────────────────┘
                  │
                  │  Anonymized ScrapeResult
                  ▼
   
3. SUMMARIZE
   ┌─────────────────────────────────────┐
   │       Model Provider Chain          │
   │                                     │
   │  OllamaProvider (primary)           │
   │      ↓ on failure                   │
   │  Fallback provider (if configured)  │
   │                                     │
   │  Input: GREEN data + system prompt  │
   │  Output: markdown summary           │
   └──────────────┬──────────────────────┘
                  │
                  │  Summary (markdown)
                  ▼
   
4. DELIVER
   ┌─────────────────────────────────────┐
   │       Telegram Delivery             │
   │                                     │
   │  Deanonymizer:                      │
   │  [PERSON_1] → Иванов               │
   │  [EMAIL_2] → ivanov@corp.ru        │
   │                                     │
   │  HTML escape + chunk (≤4096 chars)  │
   │  parse_mode=HTML                    │
   │                                     │
   │  Bot API: sendMessage                │
   └─────────────────────────────────────┘
```

### Обработка ошибок в cron-режиме

При запуске по расписанию (`--cron`) ошибки Ollama отправляются в Telegram уведомлением:

```
⚠️ Ollama not running
Summary generation failed: Ollama is not reachable at http://localhost:11434.
Start it with: ollama serve
```

---

## Система конфигурации (Pydantic v2)

### Иерархия моделей

```
JarviceConfig (root)
├── version: int = 1
├── exchange: ExchangeConfig
│   ├── enabled: bool = True
│   ├── server: str
│   ├── email: str
│   ├── auth_mode: "auto" | "basic" | "ntlm"
│   ├── keychain_service: str
│   └── scrape_interval_hours: int (1-168)
├── teams: TeamsConfig
│   ├── enabled: bool = True
│   ├── auth_mode: "ic3_token" | "graph_api"
│   ├── keychain_service: str
│   ├── scrape_interval_hours: int (1-168)
│   ├── max_messages: int (1-1000)
│   └── include_transcripts: bool = True
├── telegram: TelegramConfig
│   ├── enabled: bool = True
│   ├── bot_token_keychain: str
│   ├── chat_id: str
│   └── keychain_service: str
├── pii: PIIConfig
│   ├── enabled: bool = True
│   ├── red_dir: str (validated path)
│   └── green_dir: str (validated path)
├── models: ModelsConfig
│   ├── primary: str = "qwen3:14b"
│   ├── fallback: str = "qwen2.5:7b"
│   ├── ollama_host: str
│   └── system_prompt: str
├── schedule: ScheduleConfig
│   ├── timezone: str
│   ├── morning_summary: str (HH:MM)
│   ├── evening_summary: str (HH:MM)
│   └── weekly_summary: str (Day HH:MM)
└── logging: LoggingConfig
    ├── level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    ├── dir: str
    ├── max_size_mb: int (1-10000)
    └── rotation: "daily" | "size-based"
```

### Валидация

Pydantic v2 обеспечивает:
- **Типизация** — автоприведение типов, ошибка при невалидных значениях
- **Ограничения** — `Field(ge=1, le=168)` для `scrape_interval_hours`
- **Enum-значения** — `auth_mode` только из допустимых вариантов
- **Кастомные валидаторы** — `@field_validator` и `@model_validator`
- **Path traversal защита** — `PIIConfig.validate_paths_under_jarvice()`

### Разрешение учётных данных

```
┌─────────────────────────────────────────┐
│         get_credential(service, account) │
│                                          │
│  1. keyring (macOS Keychain/libsecret)   │
│     ↓ not found                          │
│  2. env var JARVICE_{SERVICE}_PASSWORD   │
│     ↓ not found                          │
│  3. None (ошибка)                        │
└─────────────────────────────────────────┘
```

### Генерация OpenClaw конфига

`generate_openclaw_config()` берёт шаблон `openclaw_template.json` и подставляет значения из `JarviceConfig` в плейсхолдеры `{{KEY}}`. Результат записывается в `~/.openclaw/openclaw.json`.

---

## Управление состоянием (StateManager)

### Формат state.json

```json
{
  "version": 1,
  "scrapers": {
    "exchange": {
      "last_scrape": "2026-05-21T14:30:00+03:00",
      "error_count": 0,
      "token_set_at": "2026-05-21T08:00:00+03:00"
    },
    "teams": {
      "last_scrape": "2026-05-21T14:30:00+03:00"
    }
  },
  "last_run": "2026-05-21T14:30:00+03:00"
}
```

### Курсорная навигация

Каждый скрейпер сохраняет `last_scrape` — timestamp последнего успешного скрейпинга. При следующем запуске скрейпер получает только новые данные (incremental scraping).

```python
state = StateManager()
since = state.get_cursor("exchange")  # None при первом запуске → 24 часа
result = scraper.scrape(since=since)
state.set_cursor("exchange", result.timestamp)
```

### Отслеживание ошибок

```python
# Инкремент при ошибке
count = state.increment_error_count("exchange")  # → 1, 2, 3...

# Сброс при успехе
state.reset_error_count("exchange")  # → 0
```

### Метаданные скрейперов

```python
# Произвольные метаданные
state.set_scraper_meta("teams", "token_set_at", "2026-05-21T08:00:00+03:00")
age = state.get_scraper_meta("teams", "token_set_at")
```

---

## Абстракция провайдеров (Provider)

### Иерархия

```
ModelProvider (ABC)
├── OllamaProvider    # Локальный, по умолчанию
├── OpenAIProvider    # Cloud, требует API key
└── AnthropicProvider # Cloud, требует API key
```

### Интерфейс

```python
class ModelProvider(ABC):
    name: str
    
    @abstractmethod
    def summarize(self, text: str, system_prompt: str = "") -> SummarizeResult:
        """Сгенерировать сводку текста."""
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Проверить подключение к провайдеру."""
```

### SummarizeResult

```python
@dataclass
class SummarizeResult:
    text: str                    # Текст сводки
    provider: str                # Имя провайдера
    model: str                   # Имя модели
    tokens_in: int = 0           # Входящие токены
    tokens_out: int = 0          # Исходящие токены
    elapsed_ms: float = 0.0      # Время генерации (мс)
    fallback_used: bool = False   # Использован fallback?
    error: Optional[str] = None  # Ошибка (если есть)
```

### Цепочка fallback

```python
providers = create_provider_chain(
    primary=ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b"),
    fallbacks=[
        ProviderConfig(provider=ProviderType.OPENAI, model="gpt-4", api_key_service="openai"),
    ],
)

result = summarize_with_fallback(text, providers, system_prompt)
```

1. Пробует `providers[0]` (Ollama)
2. При ошибке — `providers[1]` (OpenAI)
3. Все провайдеры неудачны → `SummarizeResult(error="All providers failed")`

### Аудит-лог провайдеров

Каждый вызов cloud-провайдера (OpenAI, Anthropic) логируется:

```python
log_to_audit(
    action="summarize",
    provider="openai",
    model="gpt-4",
    tokens_in=3847,
    tokens_out=512,
    green_path="/path/to/GREEN/file.json",
)
```

---

## Планирование (Cron)

### Архитектура

```
the-jarvice enable
       │
       ▼
  Чтение текущего crontab
       │
       ▼
  Удаление старых записей (# the-jarvice-managed)
       │
       ▼
  Добавление новых записей:
  ┌────────────────────────────────────────────────────────────┐
  │ 0 7 * * * /path/to/python -m the_jarvice run --once        │
  │   --cron --label morning >> ~/.the-jarvice/logs/cron.log    │
  │   2>&1 # the-jarvice-managed                                │
  │                                                             │
  │ 0 19 * * * /path/to/python -m the_jarvice run --once       │
  │   --cron --label evening >> ~/.the-jarvice/logs/cron.log   │
  │   2>&1 # the-jarvice-managed                                │
  └────────────────────────────────────────────────────────────┘
       │
       ▼
  crontab installation
```

### Маркер `# the-jarvice-managed`

Все записи The Jarvice в crontab помечены комментарием `# the-jarvice-managed`. Это позволяет:
- Безопасно удалять только записи The Jarvice при `disable`
- Не трогать другие cron-задачи пользователя
- Идемпотентность: повторный `enable` заменяет старые записи

### Флаг `--cron`

- Подавляет Rich-форматирование (для чистых логов)
- Включает уведомления об ошибках Ollama в Telegram
- Используется только в cron-запусках, не интерактивно

### Флаг `--label`

```bash
the-jarvice run --once --cron --label morning
the-jarvice run --once --cron --label evening
the-jarvice run --once --cron --label weekly
```

Метка записывается в лог и может использоваться для фильтрации.

---

## Скрейперы

### BaseScraper (ABC)

```python
class BaseScraper(ABC):
    name: str
    
    @abstractmethod
    def configure(self) -> bool: ...
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, str]: ...
    
    @abstractmethod
    def scrape(self, since: Optional[datetime] = None) -> ScrapeResult: ...
    
    @abstractmethod
    def get_status(self) -> dict: ...
```

### ScrapeResult

```python
@dataclass
class ScrapeResult:
    source: str           # "exchange", "exchange_calendar", "teams"
    timestamp: datetime   # Время скрейпинга
    items: list[dict]     # Список элементов
    count: int            # Количество элементов
    errors: list[str]      # Ошибки
    metadata: dict         # Дополнительные данные
```

### ExchangeScraper

**Подключение:** EWS (on-premise Exchange) через `exchangelib`

**Аутентификация:**
1. Keyring → `the-jarvice.exchange` service
2. macOS Keychain CLI fallback
3. Legacy `exchange-ews` service
4. Env var `JARVICE_EXCHANGE_PASSWORD`

**Stealth:** User-Agent имитирует Outlook 16.0:
```
Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.18129; Pro)
```

**Методы:**
- `scrape(since)` — письма из Inbox с `datetime_received >= since`
- `scrape_calendar(since, days_ahead)` — события календаря
- `_item_to_dict()` — конвертация email в словарь
- `_calendar_item_to_dict()` — конвертация события

**Incremental:** использует `since` из `StateManager.get_cursor("exchange")`

### TeamsScraper

**Подключение:** IC3 token (из DevTools браузера) через `httpx`

**Аутентификация:**
1. Keyring → `the-jarvice.teams` service, account `ic3_token`
2. Env var `JARVICE_TEAMS_PASSWORD`

**Жизненный цикл токена:**
- IC3-токен истекает через ~24 часа
- `_is_token_expired()` проверяет JWT `exp` claim
- `set_token_age_hours()` / `get_token_age_hours()` в StateManager
- `doctor` проверяет возраст токена

**API-эндпоинты:**
- `/conversations` — список чатов
- `/conversations/{id}/messages` — сообщения чата
- `/meetings` — встречи

**Rate limiting:** `request_delay_ms` (200мс по умолчанию) между запросами + exponential backoff при 429

**_SenderIndex:** детерминированная псевдонимизация имён в пределах запуска

---

## PII-пайплайн (подробно)

### PIIClassifier

Regex-детектор без внешних зависимостей:

| Тип | Паттерн | Маска |
|-----|---------|-------|
| Email | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `[EMAIL_N]` |
| Телефон (РФ) | `+7/8 XXX XXX-XX-XX` | `[PHONE_N]` |
| ИНН | 10 или 12 цифр | `[INN_N]` |
| СНИЛС | `XXX-XXX-XXX XX` | `[SNILS_N]` |

### Force-masking

Отправители и получатели **всегда** маскируются, даже если NER не обнаружил ПДн:

```python
# В ExchangeScraper._item_to_dict()
sender = {
    "name": "[PERSON_1]",    # force-mask
    "email": "[EMAIL_1]",    # force-mask
}

# В TeamsScraper._chat_message_to_dict()
sender = {
    "name": "[SENDER_1]",    # _SenderIndex
    "email": sender_email,   # маскируется в PII pipeline
}
```

### MappingManager

Хранит маппинг `маска → реальное_значение` в `RED/mapping.json`:

```json
{
  "version": 1,
  "persons": {
    "[PERSON_1]": {"full": "Иванов И.И.", "variants": ["Иванов", "иванов"]}
  },
  "phones": {
    "[PHONE_1]": "+79001234567"
  },
  "emails": {
    "[EMAIL_1]": "ivanov@corp.ru"
  },
  "_reverse": {
    "иванов": "[PERSON_1]"
  }
}
```

**Свойства:**
- Консистентность: `Иванов` → `[PERSON_1]` везде
- Case-insensitive: `иванов` и `Иванов` → одна маска
- Варианты: поддерживает альтернативные написания
- Обратный индекс: `_reverse` для быстрого поиска

### Deanonymizer

Восстанавливает реальные имена перед отправкой в Telegram:

```python
deanonymizer = Deanonymizer()
real_text = deanonymizer.deanonymize("[PERSON_1] сообщил о [EMAIL_1]")
# → "Иванов сообщил о ivanov@corp.ru"
```

Использует `token_map` — лениво загруженный словарь `маска → значение`.

---

## Диагностика (Doctor)

12 проверок в модуле `core/doctor.py`:

| # | Проверка | Что делает |
|---|----------|------------|
| 1 | Python | Версия ≥ 3.10 |
| 2 | Ollama | Запущен, доступен по `localhost:11434` |
| 3 | Model | Модель загружена в Ollama |
| 4 | Keyring | Чтение/запись работает |
| 5 | Config | `config.yaml` валиден |
| 6 | Exchange | Подключение к EWS-серверу |
| 7 | Teams | IC3-токен валиден, не истёк |
| 8 | Telegram | Bot API отвечает `getMe` |
| 9 | Disk | Свободно ≥ 12 ГБ |
| 10 | OpenClaw | Установлен и запущен |
| 11 | PII Permissions | RED `chmod 700`, `mapping.json` `chmod 600` |
| 12 | Cron | Записи `the-jarvice-managed` в crontab |

### Форматы вывода

```bash
# Таблица (по умолчанию)
the-jarvice doctor

# Подробно
the-jarvice doctor --verbose

# JSON для автоматизации
the-jarvice doctor --json

# Автоисправление
the-jarvice doctor --fix
```

---

## CLI-команды

### Полный список

| Команда | Описание | Ключевые флаги |
|---------|----------|----------------|
| `configure` | Интерактивный мастер настройки | `--quick`, `--reauth SERVICE`, `--skip-*` |
| `run` | Запустить пайплайн | `--once`, `--dry-run`, `--verbose`, `--cron`, `--label` |
| `doctor` | Диагностика системы | `--verbose`, `--json`, `--fix` |
| `enable` | Включить расписание | `--morning HH:MM`, `--evening HH:MM`, `--weekly` |
| `disable` | Отключить расписание | — |
| `version` | Показать версию | — |
| `uninstall` | Удалить The Jarvice | `--keep-config`, `--force` |

### Версионирование

Единственный источник версии — файл `VERSION` в корне проекта:

```
0.2.0
```

Загружается через `importlib.metadata` с fallback на чтение файла:

```python
_VERSION_FILE = Path(__file__).parent.parent.parent / "VERSION"
try:
    _VERSION = _VERSION_FILE.read_text().strip()
except FileNotFoundError:
    _VERSION = "0.1.0"
```

---

## Модель данных

### Config-файл (YAML)

`~/.the-jarvice/config.yaml` — единственный источник истины для конфигурации. OpenClaw-конфиг (`openclaw.json`) генерируется из него.

### State-файл (JSON)

`~/.the-jarvice/state.json` — автогенерируемый, не редактировать вручную. Хранит курсоры скрейперов и счётчики ошибок.

### PII-данные

| Файл | Права | Описание |
|------|-------|----------|
| `data/pii/RED/{hash}.json` | 600 | Исходные данные с ПДн |
| `data/pii/RED/mapping.json` | 600 | Маппинг масок → реальные значения |
| `data/pii/GREEN/{hash}.json` | 644 | Анонимизированные данные (без ПДн) |

### Результаты

| Файл | Описание |
|------|----------|
| `memory/summary_YYYY-MM-DD_HHMMSS.md` | Сгенерированная сводка |
| `data/{source}_YYYY-MM-DD_HHMMSS.json` | Результаты скрейпинга |
| `audit.log` | Аудит-лог операций |
| `logs/cron.log` | Лог cron-запусков |

---

## Зависимости

### Основные

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `typer[all]` | ≥0.9.0 | CLI-фреймворк |
| `pydantic` | ≥2.0 | Валидация конфигурации |
| `keyring` | ≥24.0 | Хранение учётных данных |
| `rich` | ≥13.0 | Терминальный вывод |
| `pyyaml` | ≥6.0 | Парсинг YAML |
| `requests` | ≥2.31 | HTTP-запросы (Telegram, Ollama) |

### Опциональные

| Пакет | Версия | Группа | Назначение |
|-------|--------|--------|------------|
| `exchangelib` | ≥5.0 | `[exchange]` | Exchange EWS скрейпинг |
| `httpx` | — | `[teams]` | Teams IC3 API |
| `pytest` | — | `[dev]` | Тестирование |

### Системные

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| Python | ≥3.10 | Runtime |
| Ollama | latest | Локальная LLM |
| Node.js | ≥20 | OpenClaw (опционально) |
| macOS | ≥13 | Основная платформа |

---

## Метрики (v0.2.0)

| Метрика | Значение |
|---------|----------|
| LOC | ~9200 |
| Тестов | 267 |
| Покрытие кода | Sprint 1-4 |
| Скрейперы | 2 (Exchange, Teams) |
| LLM-провайдеры | 3 (Ollama, OpenAI, Anthropic) |
| Диагностических проверок | 12 |
| CLI-команд | 7 |