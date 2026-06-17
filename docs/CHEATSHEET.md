# The Jarvice — Памятка

## Что это
Локальный AI-ассистент для корпоративных сводок. Скрейпит Exchange/Teams, обезличивает ПДн, генерирует сводку через Ollama, доставляет в Telegram. Всё на вашей машине — данные не уходят в облако.

## Ключевые числа
- 9 230 строк кода, 267 тестов
- 4 спринта, 12 диагностик
- От установки до первой сводки — 5 минут

## Три режима приватности
| Режим | Где данные | Качество сводки | Цена |
|-------|-----------|----------------|------|
| Private | Только на машине | Базовое (Ollama) | Бесплатно |
| Enhanced | Обезличенные в облаке | Высокое (GPT-4) | По API |
| Knowledge | Обезличенные + граф знаний | Экспертное | Подписка |

## Как работает
```
Exchange/Teams → PII Anonymizer → LLM → Telegram
                 (RED → GREEN)              (HTML)
```
- RED (chmod 700) — оригиналы с ПДн, никогда не покидают машину
- GREEN — обезличенные данные ([PERSON_1] вместо имён)
- mapping.json (chmod 600) — обратная подстановка для Telegram

## Безопасность
- Пароли и токены — в Keychain/keyring, не в конфигах
- Path traversal protection на PII директории
- Ollama prompt hardening (system prompt против injection)
- Log sanitization (SENSITIVE_FIELDS маскируются)
- Audit log (JSON lines) всех операций с ПДн

## Установка
```bash
# Быстрая
bash setup.sh
the-jarvice configure --quick    # 3 поля
the-jarvice run --once

# Headless / CI
the-jarvice configure --non-interactive  # из env vars

# Расписание
the-jarvice enable                  # cron
the-jarvice disable                 # убрать cron
```

## CLI команды
| Команда | Что делает |
|---------|-----------|
| `configure --quick` | 3 поля: email, пароль, bot token |
| `configure --non-interactive` | Из env vars (JARVICE_*) |
| `run --once` | Один прогон |
| `run --dry-run` | Без отправки в Telegram |
| `run --cron` | Для расписания (тихий режим) |
| `doctor` | 12 проверок |
| `status` | Конфиг, последний запуск, cron |
| `enable` | Включить расписание |
| `disable` | Выключить расписание |
| `uninstall` | Удалить (с очисткой PII) |

## Env vars для --non-interactive
- `JARVICE_EXCHANGE_EMAIL`
- `JARVICE_EXCHANGE_PASSWORD`
- `JARVICE_EXCHANGE_SERVER` (автодетект если не указан)
- `JARVICE_TEAMS_IC3_TOKEN`
- `JARVICE_TELEGRAM_BOT_TOKEN`
- `JARVICE_TELEGRAM_CHAT_ID` (автодетект если не указан)
- `JARVICE_SCHEDULE_TIMEZONE`
- `JARVICE_SCHEDULE_MORNING`
- `JARVICE_SCHEDULE_EVENING`
- `JARVICE_MODEL_PRIMARY`

## Для кого
- Руководители — утренняя сводка по почте вместо 1-2 часов чтения
- Безопасники — ПДн не уходят за пределы машины
- DevOps — headless установка, cron, 12 диагностик
- Продакт-менеджеры — конкурентное преимущество: privacy-first

## v0.2.0 → v0.2.1
- v0.2.0: первый публичный релиз (configure, setup, cron, doctor, README)
- v0.2.1: headless configure, status, uninstall PII wipe, Linux, CI

## Что дальше (v0.3.0)
- Cloud providers (OpenAI, Anthropic)
- Exchange OAuth (Office 365)
- Knowledge Mode (The Brain RAG)