# PII Pipeline — Полная архитектура

## Обзор

PII Pipeline обеспечивает анонимизацию персональных данных (ПДн) перед отправкой во внешние LLM и демаскировку (deanonymization) перед доставкой ответов в Telegram.

**Принцип:** Внешние модели (GLM, Kimi, DeepSeek — все через Ollama cloud) НИКОГДА не видят реальные ПДн. Они работают только с масками `[PERSON_N]`, `[EMAIL_N]` и т.д. Реальные данные хранятся локально в `mapping.json` (RED/, chmod 600) и подставляются обратно только перед отправкой в Telegram.

---

## 1. Структура директорий

```
~/AI/knowledge_red/                     ← RED (оригиналы, chmod 700)
├── mapping.json                        ← Главный mapping (1747 персон, chmod 600)
├── mail/                               ← Оригиналы писем (JSON, chmod 600)
└── ...

~/.the-jarvice/data/pii/
├── RED/                                ← Новый RED (PII pipeline, chmod 700)
│   ├── mapping.json                    ← Mapping для новых данных (423 персоны)
│   ├── mail/                           ← Оригиналы писем
│   ├── calendar/                       ← Оригиналы встреч
│   ├── teams/                          ← Оригиналы Teams сообщений
│   └── transcripts/                    ← Оригиналы транскриптов
│
└── GREEN/                              ← GREEN (анонимизированные данные)
    ├── mail/                           ← Письма с масками
    ├── calendar/                       ← Встречи с масками
    ├── teams/                          ← Teams с масками
    └── transcripts/                    ← Транскрипты с масками

~/.openclaw/memory/red                  ← Симлинк → ~/AI/knowledge_red/
```

### Уровни доступа
| Зона | Данные | Права | Кто читает |
|------|--------|-------|------------|
| RED | Оригиналы (ПДн) | chmod 700/600 | Только локальные скрипты (loader, anonymizer) |
| GREEN | Маскированные | обычные | LLM (Jarvis, кроны, subagents) |
| mapping.json | Связь маска↔реальное значение | chmod 600 | Только deanonymizer (локально) |

---

## 2. Классификация данных (POLICY.md)

| Уровень | Что входит | Запреты |
|---------|-----------|---------|
| **RED** | ПДн сотрудников/клиентов, пароли, токены, ключи | ❌ Во внешние сервисы |
| **YELLOW** | Внутренние документы, стратегия, оргструктура, протоколы | Только в рабочих задачах |
| **GREEN** | Публичная информация, методологии, общие знания | ✅ Свободно |

---

## 3. Маскиратор (Anonymizer)

### 3.1. Компоненты

```
classifier.py          ← Определяет наличие ПДн в тексте
├── Natasha NER        ← ФИО и адреса (библиотека natasha, локально)
├── Regex              ← Телефоны, email, ИНН, СНИЛС, паспорт, карты
└── NER qwen3:14b      ← Локальная LLM для ФИО в произвольном тексте (опционально)
│
anonymizer.py          ← Заменяет ПДн на маски с консистентным маппингом
├── get_or_create_token() ← Проверяет mapping, возвращает существующий или создаёт новый токен
├── Variants matching  ← Частичные совпадения (Иванов → Иванов А.П. → Иванов Алексей Петрович)
└── _reverse index     ← Обратный поиск: value → token
```

### 3.2. Типы масок

| Маска | Тип | Что заменяет |
|-------|-----|-------------|
| `[PERSON_N]` | person | ФИО сотрудников |
| `[PHONE_N]` | phone | Телефоны (+7 XXX XXX-XX-XX) |
| `[EMAIL_N]` | email | Email адреса |
| `[INN_N]` | inn | ИНН (10 или 12 цифр) |
| `[SNILS_N]` | snils | СНИЛС |
| `[PASSPORT_N]` | passport | Паспорт (серия+номер) |
| `[CARD_N]` | card | Номер карты (16 цифр) |
| `[ADDRESS_N]` | address | Адреса |
| `[TGID_N]` | tgid | Telegram ID/username |

### 3.3. Как работает маскирование

```
Входной текст: "Позвоните Иванову Алексею Петровичу по +7 916 123-45-67"
                ↓
1. Classifier:
   - Natasha NER: "Иванов Алексей Петрович" → PER
   - Regex: "+7 916 123-45-67" → phone
   
2. Anonymizer:
   - get_or_create_token('person', 'Иванов Алексей Петрович')
     → проверяет mapping.json → нет → создаёт [PERSON_1]
   - get_or_create_token('phone', '+7 916 123-45-67')
     → проверяет mapping.json → нет → создаёт [PHONE_1]
   
3. Замена в тексте (с конца, чтобы не сбить индексы):
   "Позвоните [PERSON_1] по [PHONE_1]"
                ↓
4. Сохранение:
   - Оригинал → RED/mail/ (chmod 600)
   - Маскированный → GREEN/mail/
   - mapping.json обновляется (chmod 600)
```

### 3.4. Variants matching (умный поиск)

Для persons хранятся варианты написания:
- `Иванов Алексей Петрович` → `[PERSON_1]` (full)
- `Иванов` → `[PERSON_1]` (root matching — 4-char prefix)
- `Иванов А.П.` → `[PERSON_1]` (initials matching)
- `Иванову` → `[PERSON_1]` (declined name matching — strip endings)

Это обеспечивает консистентность: один и тот же человек всегда получает один и тот же токен, независимо от формы написания.

### 3.5. NER через qwen3:14b (локально)

Для извлечения ФИО из произвольного текста (тело письма, Teams сообщения), где regex и natasha могут пропустить имена:

- **Модель:** `qwen3:14b` через Ollama (локально, НЕ cloud)
- **Время:** ~84 сек на вызов
- **Использование:** опционально (`--no-ner` флаг для regex-only режима)
- **Безопасность:** ПДн не уходят в облако — NER работает локально

---

## 4. Источники данных и loaders

### 4.1. Exchange Mail (`exchange_loader.py`)
```
Exchange EWS → item_to_dict() → RED/mail/ (оригинал)
                                → anonymize_mail() → GREEN/mail/ (маски)
```
- Анонимизирует: subject, body, sender (name+email), recipients (name+email)
- Force-mask: sender и recipients всегда маскируются (даже если NER пропустил)
- Фильтры: CID (не email), Message-ID (не email)
- Mapping: `~/AI/knowledge_red/mapping.json` (старший, 1747 персон)

### 4.2. Exchange Calendar (`calendar_loader.py`)
```
Exchange EWS → event_to_dict() → RED/calendar/ (оригинал)
                                → anonymize() → GREEN/calendar/ (маски)
```
- Анонимизирует: subject, organizer, attendees, body
- Фильтры: is_cancelled, "Нет на месте", "План дня", "Пуш время", Free
- Mapping: `~/.the-jarvice/data/pii/RED/mapping.json` (новый, 423 персоны)

### 4.3. Teams (`teams_to_pii.py`)
```
Teams scraper → RED/teams/ (оригиналы)
              → anonymize() → GREEN/teams/ (маски)
Teams transcripts → RED/transcripts/ (оригиналы)
                   → anonymize() → GREEN/transcripts/ (маски)
```
- Анонимизирует: sender, message text, transcript text
- Mapping: `~/.the-jarvice/data/pii/RED/mapping.json`

### 4.4. teams_by_date.py
```
GREEN/teams/*.json → фильтр по дате → /tmp/teams-morning.txt (compact формат)
```
Не интерпретирует — только фильтрует и агрегирует сырые маскированные данные.

---

## 5. Memory (память Джарвиса)

### 5.1. Файлы памяти
```
workspace-jarvis/
├── MEMORY.md          ← Долгосрочная память (curated)
├── MEMORY-p1.md       ← Страница 1 (split по размеру)
├── MEMORY-p2.md       ← Страница 2
└── memory/
    ├── 2026-06-26.md  ← Daily notes (APPEND)
    ├── 2026-06-25.md
    └── ...
```

### 5.2. Обезличивание memory
- `anonymize_memory.py` — маскирует ПДн в memory-файлах
- Использует mapping.json (3107 записей на момент анонимизации)
- Заменяет: полные ФИО (2+ слов), фамилии, email, телефоны
- НЕ заменяет: одиночные имена (Александр, Дмитрий) — чтобы избежать ложных срабатываний
- Backup: `memory/.pre-anonymize-backup/`

### 5.3. Embeddings
- `jarvis.sqlite` (293MB, 3675 чанков) — индекс по memory и GREEN-данным
- memory_search ищет по memory/*.md и session transcripts
- Внешние модели видят только маски при поиске

---

## 6. Deanonymizer (демаскировка перед отправкой)

### 6.1. Принцип

```
LLM генерирует ответ с масками:
  "Встреча с [PERSON_653] и [PERSON_1400] назначена на 15:00"
                ↓
Deanonymizer (локально):
  [PERSON_653] → "Дрыгин" (из mapping.json)
  [PERSON_1400] → "Гараев" (из mapping.json)
                ↓
В Telegram:
  "Встреча с Дрыгиным и Гараевым назначена на 15:00"
```

### 6.2. Mapping-файлы (приоритет)

| Приоритет | Путь | Масок | Использование |
|-----------|------|-------|---------------|
| 1 (высший) | `~/AI/knowledge_red/mapping.json` | 1747 | memory/*.md, ответы в чате |
| 2 (fallback) | `~/.the-jarvice/data/pii/RED/mapping.json` | 423 | Новые данные PII pipeline |
| 3 (симлинк) | `~/.openclaw/memory/red/mapping.json` | → 1 | Дефолтный путь в коде |

При конфликте одинаковых токенов с разными значениями — **первый выигрывает** (старший mapping).

### 6.3. Скрипты deanonymization

**Для прямого чата (AGENTS.md правило):**
```bash
echo 'Текст с [PERSON_653]' | python3 \
  /Users/mizhenskii/.openclaw/workspace-jarvis/scripts/pii_pipeline/deanonymize_response.py
```

**Для кронов (сводки):**
```bash
python3 /Users/mizhenskii/.openclaw/workspace/scripts/pii_pipeline/deanonymize.py \
  --file /Users/mizhenskii/.openclaw/workspace-jarvis/spike/evening-final.md
```

**PII Daemon (backup, не активен):**
- `pii_daemon.py` — мониторит gateway.log, находит исходящие с масками, редактирует через Telegram API
- LaunchAgent: `ai.jarvis.pii-daemon.plist`
- НЕ запущен (gateway.log не пишется) — полагаемся на инлайн deanonymization

### 6.4. Проверка (smoke_test.py)
- Сканирует GREEN/ на наличие regex-обнаружимых ПДн
- Проверяет: телефоны, email, ИНН, СНИЛС, имена, Telegram IDs
- Должен показывать 0 утечек

---

## 7. Поток данных (end-to-end)

### 7.1. Входящие данные (scraper → LLM)

```
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌─────┐
│  Источник   │────▶│  RED/    │────▶│ Anonymizer│───▶│  GREEN/  │────▶│ LLM │
│  (Exchange, │     │ (ориг.)  │     │ (masking) │    │ (маски)  │     │     │
│  Teams)     │     │ chmod 600│     │           │    │          │     │ GLM │
└─────────────┘     └──────────┘     └──────────┘     └──────────┘     │Kimi│
                                                        ↑              │DS  │
                                                        │              └─────┘
                                                   mapping.json
                                                   (RED/, chmod 600)
                                                   НЕ уходит в облако
```

### 7.2. Исходящие ответы (LLM → Telegram)

```
┌─────┐     ┌────────────────┐     ┌──────────────┐     ┌──────────┐
│ LLM │────▶│ Ответ с масками │────▶│ Deanonymizer │────▶│ Telegram │
│     │     │ [PERSON_653]    │     │ (локально)   │     │          │
└─────┘     └────────────────┘     └──────────────┘     └──────────┘
                                     ↑
                                mapping.json
                                (RED/, chmod 600)
                                НЕ уходит в облако
```

### 7.3. Кроны (сводки)

```
1. teams_by_date.py → /tmp/teams-morning.txt (маски)
2. Subagent (DeepSeek/Kimi) читает GREEN/ + /tmp/ → draft (маски)
3. Validator (GLM) проверяет draft vs GREEN/ → validation
4. Editor (Kimi) финальная версия → evening-final.md (маски)
5. deanonymize.py --file evening-final.md → заменяет маски
6. Announce delivery → Telegram (реальные имена)
```

### 7.4. Прямой чат

```
1. Пользователь пишет в Telegram
2. Jarvis читает memory/*.md (маски) + GREEN/ (маски)
3. LLM генерирует ответ с масками
4. Jarvis прогоняет ответ через deanonymize_response.py
5. Демаскированный текст отправляется в Telegram
```

---

## 8. Кроны Джарвиса (сводки)

| Крон | Расписание | Модель | Источники | Deanonymize |
|------|-----------|--------|-----------|-------------|
| Утренняя сводка | 09:30 KGD, пн-пт | Kimi K2.6 | GREEN/calendar + mail + Teams | ✅ |
| Вечерняя сводка (итоги) | 23:00 KGD, пн-пт | Kimi K2.6 | GREEN/calendar + mail + Teams + transcripts | ✅ |
| Расписание на завтра | 23:01 KGD, вс-чт | Kimi K2.6 | GREEN/calendar + mail | ✅ |
| Недельный ревью | 20:00 KGD, воскр | Kimi K2.6 | GREEN/ (неделя) | ✅ |
| Квартальный дамп | 18:00 1 янв/апр/июл/окт | Kimi K2.6 | GREEN/ (квартал) | ✅ |
| Teams sync | каждые 30 мин | GLM 5.2 | Teams scraper | — |
| Index knowledge | каждые 30 мин | GLM 5.2 | Проверка новых файлов | — |
| Обновление почты | 22:30 KGD, пн-пт | — | exchange_loader.py | — |

Multi-pass pipeline: DeepSeek V4 Pro (сбор) → GLM 5.2 (валидация) → Kimi K2.6 (редактор), до 3 итераций, цель ≥95% точности.

---

## 9. Безопасность

### 9.1. Что НЕ видят внешние модели
- mapping.json (реальные ПДн)
- RED/ директории (оригиналы)
- Неанонимизированный текст писем, встреч, Teams
- memory/.pre-anonymize-backup/

### 9.2. Что видят внешние модели
- GREEN/ (маскированные данные)
- memory/*.md (обезличенные, маски вместо ФИО)
- /tmp/teams-*.txt (маски)

### 9.3. Что остаётся локально
- mapping.json — только deanonymizer читает
- NER qwen3:14b — локальная модель, ПДн не уходят в облако
- RED/ — только loader записывает, deanonymizer не пишет

### 9.4. Известные риски
- **Два mapping с разной нумерацией** — старый (1747) и новый (423). Решение: deanonymizer мержит оба, приоритет у старшего
- **NER отключён по умолчанию** (`--no-ner`) для скорости. Regex + natasha ловят ~95% ПДн. NER ловит оставшиеся 5%, но ~84 сек на файл
- **Остаточные утечки в GREEN** — ~0.02% файлов (email в URL-параметрах, подписях). Smoke test проверяет, но не 100%

---

## 10. Файлы скриптов

### workspace-jarvis/scripts/pii_pipeline/
| Файл | Назначение |
|------|-----------|
| `classifier.py` | Определение ПДн (natasha NER + regex) |
| `anonymizer.py` | Замена ПДн на маски, mapping management |
| `exclusions.py` | Список исключений (названия продуктов, отделов — не ПДн) |
| `deanonymizer.py` | Замена масок на реальные значения (оба mapping) |
| `deanonymize_response.py` | CLI-обёртка для прямого чата |
| `exchange_loader.py` | Exchange почта → RED → GREEN |
| `pii_daemon.py` | Daemon для post-factum редактирования (не активен) |
| `telegram_edit.py` | Telegram API editMessageText |

### workspace/scripts/pii_pipeline/
| Файл | Назначение |
|------|-----------|
| `deanonymize.py` | Deanonymize для кронов (primary + fallback mapping) |
| `calendar_loader.py` | Exchange календарь → RED → GREEN |
| `teams_to_pii.py` | Teams → RED → GREEN |
| `teams_by_date.py` | Фильтр GREEN/teams по дате → compact файл |
| `smoke_test.py` | Проверка GREEN/ на утечки ПДн |
| `anonymize_memory.py` | Обезличивание memory/*.md |

### workspace/the-jarvice/the_jarvice/scrapers/pii/
| Файл | Назначение |
|------|-----------|
| `anonymizer.py` | Новый Anonymizer (NER qwen3:14b + variants matching) |
| | Содержит: Anonymizer, MappingManager, Deanonymizer классы |