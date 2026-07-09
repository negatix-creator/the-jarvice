# Knowledge Graph + PII Masking Platform

> Версия: 3.1 (implementation-ready)
> Дата: 2026-07-09
> Назначение: полная спецификация для корпоративного внедрения

---

## 0. Бизнес-контекст

### 0.1. Проблема

Корпоративные руководители тонут в потоке данных: почта, календари, мессенджеры, встречи. Информация разбросана по системам, знания не сохраняются, контекст теряется при смене сотрудников. AI-ассистенты могли бы помочь — но передача персональных данных (ПДн) в облачные модели нарушает 152-ФЗ, корпоративные политики безопасности и здравый смысл.

### 0.2. Решение

Платформа, которая:
1. **Собирает** разрозненные корпоративные данные в единый граф знаний
2. **Обезличивает** все ПДн перед отправкой в облако — гарантированно, на уровне архитектуры
3. **Строит** канонический граф: люди, организации, решения, проблемы, инсайты, связи
4. **Отдаёт** контекст агентам через API с политиками доступа
5. **Демаскирует** ответы перед доставкой пользователю — локально

### 0.3. Цели

| Цель | Метрика |
|---|---|
| **Безопасность** | 0 утечек ПДн в облачные модели. Все данные проходят через маскирование. |
| **Полнота знаний** | Все корпоративные источники (почта, календарь, Teams, документы) автоматически попадают в граф. |
| **Качество извлечения** | ≥90% корректных атомов (фактов) из источников. ≥85% Recall@10 при поиске. |
| **Скорость** | Свежие данные доступны в графе за <60 сек. Поиск <400 мс (p95). |
| **Масштабируемость** | От персонального инстанса (1 пользователь) до командного (50+ пользователей). |
| **Право на забвение** | Полное удаление данных субъекта по запросу — из всех хранилищ, включая бэкапы. |

### 0.4. Возможности

**Для руководителя:**
- Управленческие сводки на основе всего корпоративного контекста (почта + календарь + Teams + документы)
- Поиск по графу знаний: «какие решения принимались по проекту X», «с кем обсуждали тему Y»
- Проактивные инсайты: риски, зависимости, непринятые решения
- Персональный vault (Obsidian) с реальными именами и полным графом

**Для команды:**
- Контекстные капсулы по проектам (роль-ориентированный доступ)
- Автоматическое извлечение решений, задач, проблем из рабочих коммуникаций
- Накопление корпоративной памяти — знания не теряются при уходе сотрудников

**Для безопасности:**
- Облачные модели работают только с масками — соответствие 152-ФЗ
- Политики доступа по realm (work / tech / personal / health / finance)
- Локальные модели для чувствительных данных (здоровье, финансы) — не уходят в облако даже в масках
- Crypto-shredding + deletion saga — право на забвение

**Для IT:**
- OS-изоляция: RED zone (ПДн) и GREEN zone (маски) — разные пользователи ОС
- API-first: все доступы через сокет с policy enforcement на каждом этапе
- Воспроизводимость: replay (точное воспроизведение) и reprocess (пересборка новой моделью)
- Идемпотентность: безопасные повторные запуски, crash recovery

### 0.5. Архитектурные принципы

1. **RED/GREEN invariant** — облачные модели НИКОГДА не видят RED. Это не политика, это архитектура — разные OS-пользователи, разные директории, нет файлового пути.
2. **Policy everywhere** — проверка доступа не только на входе, а на каждом этапе pipeline: retrieval, graph expansion, capsules, egress.
3. **Lineage** — каждый атом знает, из какого события он извлечён. Векторы знают, от какого текста посчитаны. Hash-сверка.
4. **Idempotency** — безопасные повторные запуски. content_hash, upsert по atom_id+version.
5. **Reproducibility** — канон можно точно воспроизвести (replay) или пересобрать новой моделью (reprocess).
6. **Crypto-shredding** — каждое событие шифруется отдельным ключом. Удаление = отзыв ключа. Производные удаляются через deletion saga.

---

## 1. Обзор системы

Система состоит из двух контуров, работающих совместно:

1. **PII Pipeline (маскирование/демаскирование)** — обеспечивает защиту персональных данных при передаче в облачные модели
2. **Knowledge Graph (Brain v3.1)** — граф знаний, который строится на обезличенных данных и обеспечивает поиск, навигацию и контекстную выдачу для агентов

Оба контура работают по принципу: **облачные модели никогда не видят реальные ПДн** — только маскированные данные (GREEN).

---

## 2. Полный поток данных (end-to-end)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ИСТОЧНИКИ ДАННЫХ                                    │
│  Почта (Exchange EWS) · Календарь · Teams · Memory-файлы · Ручной ввод     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ Mutation API (сокет) или file loader
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RED ZONE (chmod 700)                                │
│                                                                             │
│   raw_events.sqlite — сырые данные с ПДн                                   │
│        │                                                                    │
│        ├── NER Worker (локальная модель qwen3:14b, Ollama localhost:11434)  │
│        │     Извлекает: Person, Organization, Product, System               │
│        │     Строит: identity_map.sqlite                                    │
│        │     НЕ строит канон, атомы, рёбра — только сущности и маски        │
│        │     ~2 сек/событие                                                 │
│        │                                                                    │
│        ├── Sanitizer                                                         │
│        │     Natasha NER → regex → Yargy → verify-LLM                      │
│        │     Использует identity_map для маскирования                        │
│        │     + Re-identification Risk Gate (6-шаговая проверка)             │
│        │     Выход: GREEN-события (обезличенные тексты с масками)            │
│        │                                                                    │
│        └── identity_map.sqlite                                               │
│              Шифрованные значения, ключ в OS Keychain                        │
│              SUBJECT_01HZ... → реальное имя (зашифровано)                   │
│              Алиасы: полные ФИО, фамилии, инициалы, склонения               │
│                                                                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ Только маскированные данные
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GREEN ZONE                                          │
│                                                                             │
│   green_events (обезличенные тексты с масками [PERSON_N], [ORG_N])         │
│        │                                                                    │
│        ├── Cloud Consolidator (GLM-5.2 / DeepSeek V4 Pro, ollama-cloud)    │
│        │     Читает GREEN-события                                           │
│        │     Извлекает: атомы (15 типов) + рёбра (17 типов)                 │
│        │     Пишет: canon.sqlite (атомы + рёбра + evidence)                 │
│        │     Видит маски, НЕ видит реальные имена — структура сохранена     │
│        │     ~1 сек/событие, 15 workers параллельно                         │
│        │                                                                    │
│        ├── GREEN Projector                                                   │
│        │     canon.sqlite → green.sqlite (masked atoms + edges + FTS5 + vec) │
│        │     Проверка: канарейки, словарный скан, lineage-инвариант         │
│        │                                                                    │
│        ├── Embed Worker                                                     │
│        │     sqlite-vec: маскированные тексты → векторы                     │
│        │     Lineage: hash(masked_text) для контроля актуальности            │
│        │                                                                    │
│        └── Vault Generator + Personalizer                                   │
│              canon.sqlite + identity_map → vault с реальными именами        │
│              (только для владельца, ~/Documents/Brain-v3-Personal/)         │
│                                                                             │
│   canon.sqlite — канонический граф знаний                                   │
│   green.sqlite — проекция для поиска и выдачи агентам                       │
│                                                                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ Агенты запрашивают контекст
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BRAIN CORE API (UDS-сокет)                          │
│                                                                             │
│   1. Auth + policy (realm × sensitivity × principal)                       │
│   2. Нормализация (регистр, ё/е, лемматизация для FTS)                     │
│   3. Кандидаты: FTS5 top-50 ∪ vec top-50 ∪ exact match                     │
│   4. RRF fusion                                                             │
│   5. Graph expansion: 1 hop, degree cap ≤30, hub suppression               │
│   6. Dedup (supersedes/same_as → только актуальные)                        │
│   7. Token-budget packing (L0 nav / L1 summaries / L2 content / L3 provenance) │
│   8. Provenance rendering                                                   │
│                                                                             │
│   Policy — на КАЖДОМ этапе:                                                 │
│   - candidate retrieval (SQL)                                               │
│   - graph expansion (сосед из чужого realm не раскрывается)                  │
│   - capsule generation                                                      │
│   - MOC generation                                                          │
│   - context packing                                                        │
│   - cloud egress                                                           │
│                                                                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ Выдача агентам (маскированные данные)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         АГЕНТЫ                                              │
│                                                                             │
│   Friday, Jarvis, Dev, Ultron, Sophie, ArGO, Edith, Hera                   │
│   Видят только GREEN (маски) через Brain Core API                          │
│                                                                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ LLM генерирует ответ с масками
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEMASKING (Deanonymizer)                             │
│                                                                             │
│   LLM ответ: "Встреча с [PERSON_653] и [PERSON_1400] назначена на 15:00"  │
│        │                                                                    │
│        ▼                                                                    │
│   Deanonymizer (локально, НЕ в облаке):                                     │
│   [PERSON_653] → реальная фамилия (из identity_map)                        │
│   [PERSON_1400] → реальная фамилия (из identity_map)                       │
│        │                                                                    │
│        ▼                                                                    │
│   Пользователь: "Встреча с Ивановым и Петровым назначена на 15:00"         │
│                                                                             │
│   Скрипты:                                                                  │
│   - deanonymize_response.py — inline для прямого чата                      │
│   - deanonymize.py --file — для кронов (сводки)                             │
│   - Мержат все mapping-файлы + identity_map.sqlite                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

ОТДЕЛЬНО:
  canon.sqlite + identity_map → Vault Generator → Obsidian vault
  (реальные имена, полный граф, только владелец, ~/Documents/Brain-v3-Personal/)
```

---

## 3. Классы доверия

| Класс | Что видит | Кто | Граница |
|---|---|---|---|
| **RED** | Полные ПДн (оригиналы) | NER Worker, Sanitizer verify-LLM | Локальный runtime: без интернета, без телеметрии, отдельная OS identity, только pipeline-задачи |
| **Agent runtime** | Только GREEN (маски) | Все агенты через Brain Core API | UDS-сокет, группа brain-clients |
| **External/cloud** | Egress-filtered GREEN | Облачные модели (GLM, Kimi, DeepSeek) | Минимизация + session-scoped aliasing |

**Инвариант:** агентский runtime и внешние модели не имеют пути к RED — ни через файлы, ни через API, ни через логи.

---

## 4. Маскирование (Sanitizer)

### 4.1. Компоненты

```
sanitizer.py
├── Natasha NER       ← ФИО, адреса, организации (библиотека natasha, локально)
├── Regex engine      ← Телефоны, email, ИНН, СНИЛС, паспорт, карты, адреса
├── Yargy            ← Доменные паттерны (должности, отделения)
└── verify-LLM       ← qwen3:14b (локально) для верификации сложных случаев
```

### 4.2. Порядок обработки

1. **Natasha NER** — извлекает PER, ORG, LOC из текста
2. **Regex** — ловит структурированные ПДн (телефоны, email, ИНН, СНИЛС, паспорта, карты)
3. **Yargy** — доменные паттерны (должности «директор департамента X», отделения)
4. **verify-LLM** (опционально, `--no-ner` для regex-only режима) — проверяет граничные случаи
5. **Re-identification Risk Gate** — 6-шаговая проверка перед выдачей в GREEN

### 4.3. Типы масок

| Маска | Тип | Что заменяет |
|---|---|---|
| `SUBJECT_<ULID>` | person | ФИО (основной формат v3.1) |
| `[PERSON_N]` | person | ФИО (legacy совместимость) |
| `[ORG_N]` | organization | Названия компаний, подразделений |
| `[PHONE_N]` | phone | Телефоны |
| `[EMAIL_N]` | email | Email адреса |
| `[INN_N]` | inn | ИНН (10 или 12 цифр) |
| `[SNILS_N]` | snils | СНИЛС |
| `[PASSPORT_N]` | passport | Паспорт (серия+номер) |
| `[CARD_N]` | card | Номер карты (16 цифр) |
| `[ADDRESS_N]` | address | Адреса |
| `[TGID_N]` | tgid | Telegram ID/username |

### 4.4. Variants matching (умный поиск)

Один человек = один токен, независимо от формы написания:

- Полное ФИО → `[PERSON_1]` (точное совпадение)
- Фамилия → `[PERSON_1]` (4-символьный префикс)
- Фамилия + инициалы → `[PERSON_1]` (initials matching)
- Склонение (дательный, творительный падеж) → `[PERSON_1]` (strip окончаний)
- Одиночные имена → **НЕ маскируются** (слишком много ложных срабатываний)

### 4.5. Re-identification Risk Gate

6-шаговая проверка перед попаданием в GREEN:

1. Прямые идентификаторы найдены и заменены?
2. Сколько квазиидентификаторов осталось (роль, подразделение, город, возраст)?
3. Уникальна ли их комбинация в пределах GREEN?
4. Есть ли sensitive-атрибут рядом с person-подобным узлом?
5. Разрешает ли политика публикацию комбинации?
6. **Действие:** `copy` (пропустить) / `generalize` (обобщить) / `merge` (объединить) / `suppress` (удалить)

Действие фиксируется в `green_projection_map`.

### 4.6. Пример маскирования

```
Вход (RED):
"Позвоните Иванову Алексею Петровичу по +7 916 123-45-67"

Шаг 1 — NER: "Иванов Алексей Петрович" → PER, "+7 916 123-45-67" → phone
Шаг 2 — Anonymizer:
  get_or_create_token('person', 'Иванов Алексей Петрович') → проверяет mapping → [PERSON_1]
  get_or_create_token('phone', '+7 916 123-45-67') → проверяет mapping → [PHONE_1]
Шаг 3 — Замена (с конца, чтобы не сбить индексы):
  "Позвоните [PERSON_1] по [PHONE_1]"
Шаг 4 — Сохранение:
  Оригинал → RED/mail/ (chmod 600)
  Маскированный → GREEN/mail/
  identity_map обновляется
```

---

## 5. Демаскирование (Deanonymizer)

### 5.1. Обратный поток

```
LLM генерирует ответ с масками:
  "Встреча с [PERSON_653] и [PERSON_1400] назначена на 15:00"
         ↓
Deanonymizer (локально, НЕ в облаке):
  [PERSON_653] → реальная фамилия (из identity_map)
  [PERSON_1400] → реальная фамилия (из identity_map)
         ↓
Пользователь видит:
  "Встреча с Ивановым и Петровым назначена на 15:00"
```

### 5.2. Приоритет источников

| Приоритет | Источник | Масок | Назначение |
|---|---|---|---|
| 1 (высший) | Основной mapping (legacy) | ~1747 | memory/*.md, чат |
| 2 | PII pipeline mapping | ~423 | Новые данные (Teams, календарь) |
| 3 | identity_map.sqlite (v3.1) | Сколько угодно | Brain v3.1 |

При конфликте одинаковых токенов — первый выигрывает (старший mapping).

### 5.3. Реализация

- `deanonymize_response.py` — inline для прямого чата (агент вызывает после LLM)
- `deanonymize.py --file` — для кронов (сводки, отчёты)
- Оба мержат все mapping-файлы + identity_map.sqlite
- PII Daemon (backup, не активен) — мониторит gateway.log, находит исходящие с масками, редактирует через Telegram API

---

## 6. Knowledge Graph (Brain v3.1)

### 6.1. Онтология

**15 типов узлов:**

| Категория | Типы |
|---|---|
| Core | Person, Organization, Product |
| Context | Decision, Problem, Insight |
| Assets | Document, Meeting, Task |
| Operations | System, Input, Constraint, Competency, Project, Solution, Measurement |

**17 типов рёбер:**

| Тип | Описание |
|---|---|
| relates_to | Общая связь |
| mentions | Упоминание |
| informs | Информирует о |
| belongs_to | Принадлежит |
| part_of | Часть |
| requires | Требует |
| causes | Причина |
| solves | Решает |
| derived_from | Выведено из |
| constrains | Ограничивает |
| documents | Документирует |
| implements | Реализует |
| precedes | Предшествует |
| depends_on | Зависит от |
| measures | Измеряет |
| authored_by | Авторство |
| located_in | Расположение |

### 6.2. Схема canon.sqlite

```sql
-- Атомы (канонические факты)
atoms (
  atom_id TEXT PRIMARY KEY,           -- ULID, непрозрачный, неизменяемый
  slug TEXT,                           -- human-readable alias (только RED и vault)
  node_type TEXT NOT NULL,             -- 15 типов
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  content TEXT,
  realm TEXT NOT NULL,                 -- work/tech/personal/health/finance/meta
  sensitivity INTEGER NOT NULL,        -- 10 public / 20 internal / 30 private / 40 secret
  status TEXT NOT NULL DEFAULT 'active', -- active/superseded/retracted/draft
  confidence REAL,
  valid_from TEXT, valid_to TEXT,
  observed_at TEXT NOT NULL,
  created_at TEXT, updated_at TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  search_text_hash TEXT NOT NULL,       -- hash(title+summary+content) для lineage
  created_by_run_id TEXT NOT NULL REFERENCES projection_runs
)

-- Рёбра (связи между атомами)
edges (
  edge_id TEXT PRIMARY KEY,
  source_atom_id TEXT NOT NULL REFERENCES atoms(atom_id),
  target_atom_id TEXT NOT NULL REFERENCES atoms(atom_id),
  edge_type TEXT NOT NULL,             -- 17 типов
  strength REAL DEFAULT 1.0,
  evidence TEXT,
  created_at TEXT
)

-- Provenance: многие-ко-многим (один факт ← несколько источников)
atom_evidence (
  atom_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  source_span_start INTEGER,
  source_span_end INTEGER,
  evidence_type TEXT,                  -- stated/inferred/confirmed
  confidence REAL,
  PRIMARY KEY (atom_id, event_id, source_span_start)
)

-- Воспроизводимость
projection_runs (
  run_id TEXT PRIMARY KEY,
  projector_name TEXT,
  code_version TEXT,
  model_id TEXT,
  prompt_version TEXT,
  ontology_version TEXT,
  started_at TEXT,
  completed_at TEXT,
  status TEXT,
  total_events INTEGER,
  total_atoms INTEGER,
  total_edges INTEGER
)

-- Векторы (маскированные!)
embeddings (
  atom_id TEXT NOT NULL,
  atom_version INTEGER NOT NULL,
  search_text_hash TEXT NOT NULL,       -- hash ЗАМАСКИРОВАННОГО текста
  model_id TEXT NOT NULL,
  dimensions INTEGER NOT NULL,
  vector BLOB NOT NULL,
  PRIMARY KEY (atom_id, model_id)
)
```

### 6.3. Зоны данных (realms)

| Realm | Sensitivity | Описание | Доступ |
|---|---|---|---|
| work | 20 internal | Рабочие проекты, решения, встречи | Friday, Jarvis, Dev, Sophie, Hera |
| tech | 20 internal | Технические системы, инфраструктура | Friday, Jarvis, Dev, Ultron |
| personal | 30 private | Личные данные, финансы, здоровье | Friday, Jarvis, Hera |
| health | 30 private | Медицинские данные | **ArGO only (local)** |
| finance | 30 private | Финансовые данные | **Edith only (local)** |
| meta | 10 public | Мета-информация о системе | Все |

### 6.4. Поиск и выдача (Retrieval)

```
1. Auth + policy (SQL-предикат: realm IN(...) AND sensitivity <= rank)
2. Нормализация (регистр, ё/е, лемматизация)
3. Кандидаты: FTS5 top-50 ∪ vec top-50 ∪ exact match (title/alias)
4. RRF fusion
5. Graph expansion: 1 hop, degree cap ≤30, hub suppression
6. Dedup (supersedes/same_as → только актуальные)
7. Token-budget packing:
   L0 — навигация (MOC, заголовки)
   L1 — summaries
   L2 — top content
   L3 — provenance
8. Provenance rendering
```

**Policy enforcement на каждом этапе** — не только на шаге 1:
- candidate retrieval (SQL)
- graph expansion (сосед из чужого realm не раскрывается)
- capsule generation
- MOC generation
- context packing
- cloud egress

---

## 7. Cloud Egress Layer

Перед каждым облачным вызовом:

1. **Минимизация** — в облако уходит только пакет контекста под запрос (token budget), без лишних рёбер и provenance
2. **Session-scoped aliasing** — `SUBJECT_01HZ... → PERSON_A`, таблица соответствия живёт в рамках сессии
3. Между сессиями алиасы **не переиспользуются** → linkage между беседами разорван
4. Обратный проход: `PERSON_A` → SUBJECT-id → (локально) реальное имя
5. **Policy-check**: realm / sensitivity / destination на пакете

---

## 8. OS-изоляция

```
Пользователь: brain (сервисный, без login, launchd-демоны)
  владеет: ~/Brain/red/ (700) и ~/Brain/green/ (700)
  запускает: RED workers, GREEN projector, Brain Core API
  предоставляет: UDS-сокет /var/run/brain/api.sock
                 (группа brain-clients, srw-rw----)

Пользователь: owner (владелец)
  агенты, Obsidian, vault ~/Documents/Brain-v3-Personal/
  входят в группу brain-clients → доступ только к сокету
  файлового доступа к ~/Brain/* НЕТ (иной владелец, chmod 700)
```

---

## 9. Профили доступа агентов

| Principal | Realms | Max sensitivity | Egress |
|---|---|---|---|
| Friday, Jarvis | ALL | 30 private | local + cloud |
| Dev | tech, work, meta | 20 internal | local + cloud |
| Ultron | tech, meta | 20 internal | local |
| Sophie | work, meta | 20 internal | local + cloud |
| ArGO | personal(health) | 30 private | **local only** |
| Edith | personal(finance) | 30 private | **local only** |
| Hera | work, meta, personal | 30 private | local + cloud |

`cloud_deny_realms: [health, finance]` — не уходят в облако даже в масках, независимо от профиля.

---

## 10. Capsules (контекстные капсулы)

Одна капсула проекта может смешивать work + finance + personal → генерируются варианты под фактически используемые policy-классы:

```
capsule:project-x:work-internal      (Dev, Sophie, Ultron)
capsule:project-x:all-private        (Friday, Jarvis, Hera)
capsule:project-x:cloud-safe         (egress)
```

Классы выводятся из таблицы профилей; новых классов без нового профиля не создаётся.

---

## 11. Deletion Saga (право на забвение)

Идемпотентная сага с журналом:

```
forget(subject|atom)
  1. revoke per-event keys (raw_events — crypto-shredding)
  2. retract canonical atoms (status=retracted) + tombstone-события
  3. GREEN: remove/supersede проекций (по green_projection_map)
  4. delete FTS entries + shadow tables
  5. delete vectors
  6. outbox: capsule_refresh, moc_refresh затронутых
  7. regenerate vault (затронутые файлы)
  8. запись deletion tombstone (что удалено, когда, по чьей команде)
  9. backup retention: бэкапы старше N дней с удалёнными данными
     ротируются по расписанию; факт фиксируется в журнале саги
```

---

## 12. Тесты (гейт перед production)

1. **Canary-тест** — в тестовые события подсаживаются канарейки во все поля. После полного пайплайна — поиск по GREEN, FTS, capsules, MOC, API, логам, temp-файлам. **Ноль вхождений.**
2. **Словарный скан** — GREEN по identity store (значения + aliases + морфоформы pymorphy)
3. **Lineage-инвариант** — `embedding.search_text_hash == hash(masked_text)` для 100% векторов
4. **Vault isolation** — grep конфигов на путь vault = 0; чтение `~/Brain/*` из-под owner = permission denied
5. **Scoped access** — агент с ограниченным профилем не получает данные из чужого realm (прямой запрос, graph expansion, капсула, summary)
6. **Gold set** — dev (50 запросов) + holdout (50) + adversarial (PII-выуживание, конфликтные факты)
7. **Deletion saga e2e** — forget тестового субъекта → канарейки исчезают отовсюду
8. **Дистрибутив** — чистая установка не содержит ни байта данных владельца

---

## 13. Источники данных

| Источник | Loader | Что маскирует |
|---|---|---|
| Exchange Mail | `exchange_loader.py` | subject, body, sender, recipients |
| Exchange Calendar | `calendar_loader.py` | subject, organizer, attendees, body |
| Teams messages | `teams_to_pii.py` | sender, message text |
| Teams transcripts | `teams_to_pii.py` | speaker, text |
| Memory files | `anonymize_memory.py` | ФИО, email, телефоны |
| Ручной ввод | Mutation API | Произвольный текст |

---

## 14. Модели и их роли

| Роль | Модель | Где | Задача | Видит |
|---|---|---|---|---|
| NER Worker | qwen3:14b (локально) | Ollama localhost | Извлечение сущностей + identity_map | RED (PII) |
| Sanitizer verify-LLM | qwen3:14b (локально) | Ollama localhost | Верификация сложных случаев маскирования | RED (PII) |
| Cloud Consolidator | GLM-5.2 / DeepSeek V4 Pro | ollama-cloud | Построение канона (атомы + рёбра) | GREEN (маски) |
| Embed Worker | bge-m3 / nomic-e5 (локально) | Ollama localhost | Векторизация маскированных текстов | GREEN (маски) |
| Vault Personalizer | Прямая подстановка | локально | Замена масок на реальные имена | identity_map |

---

## 15. Стоп-правила для внедрения

- **S1.** Источники неприкосновенны: работа только на копиях, hash-сверка до/после
- **S2.** identity_map и ключи не покидают RED zone. Не логировать, не коммитить, не печатать
- **S3.** В GREEN ничего не пишется мимо санитайзера и Risk Gate
- **S4.** Каждый скрипт имеет `--dry-run`; боевой запуск — после dry-run
- **S5.** Один шаг = один критерий приёмки; шаги не объединять
- **S6.** Идемпотентность каждого шага (idempotency_key, content_hash, upsert)
- **S7.** Удаление — только через deletion saga с журналом. Ручные DELETE запрещены

---

## 16. SLO (целевые показатели)

| Метрика | Цель |
|---|---|
| Retrieval DB latency (SQLite/FTS/vector) | p50 < 50 мс |
| Retrieval end-to-end (включая embedding + fusion) | p95 < 400 мс |
| Freshness (от события до доступности в GREEN) | p95 < 60 сек |
| Context packing | p95 < 2000 токенов |
| Recall@10 (holdout) | > 85% |
| Unauthorized results | 0 |
| PII leak | 0 |
| 20 concurrent reads деградация | < 2× |