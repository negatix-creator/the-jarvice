# The Jarvice — Roadmap

> **Последнее обновление: 2026-06-23**

## Текущий статус

**Версия:** v0.5.0
**Дата релиза:** 20 июня 2026
**Последнее обновление:** 22 июня 2026

### Что работает в v0.5.0

- ✅ **PII Pipeline** — полная анонимизация: RED/GREEN, NER (qwen3:14b) + regex, MappingManager, Deanonymizer
  - 22 000+ файлов обработано, 749 persons / 744 emails в mapping, 0 утечек ПДн
  - Meetings transcripts перенесены в pipeline
  - Calendar pipeline: Exchange → RED/calendar/ → anonymizer → GREEN/calendar/
- ✅ **Brain Ingest** — оптимизированный конвейер извлечения знаний
  - Extraction: DeepSeek V4 Pro (106 атомов, 0 галлюцинаций, 160 сек)
  - Validation: GLM 5.1 (cross-model diversity)
  - Pipeline ускорение: 707 сек → 198 сек (−72%)
  - 937 атомов знаний в The Brain (16 типов сущностей, 12 типов связей)
- ✅ **Memory PII-очистка (Этап 4)** — 102 файла memory/*.md обезличены, 1412 замен, 0 утечек
- ✅ **Name Lookup + Deanonymizer (Этап 6)** — lookup ФИО → [PERSON_N], fuzzy matching для склонений
- ✅ **CLI:** configure (interactive/--quick/--non-interactive), run, doctor, status, enable/disable, uninstall
- ✅ **Exchange Scraper:** EWS, stealth User-Agent, keyring+Keychain, email+calendar
- ✅ **Teams Scraper:** IC3 token, chats + meetings
- ✅ **Summary Generator:** GLM 5.2 Cloud (primary), GLM 5.1 Cloud (fallback)
- ✅ **Telegram Delivery:** Bot API, HTML, chunking 4096 chars
- ✅ **Provider abstraction:** Ollama, OpenAI, Anthropic
- ✅ **Security:** Keychain creds, log sanitization, audit log, path traversal protection
- ✅ **Linux support:** apt/dnf/yum, keyrings.alt fallback
- ✅ **CI:** GitHub Actions (macOS + Ubuntu, Python 3.10-3.13)
- ✅ **6 агентов:** Jarvis, Friday, Edith, HERA, Ultron, Jeeves
- ✅ **27 кронов:** сводки, скрейпинг, brain ingest, health checks, backup, security watchdog
- ✅ **Multi-client deployment:** VPS, macOS, Linux — deploy scripts проверены в продакшне (mac Мурада, 19.06)
- ✅ **Deploy scripts:** macOS + Linux одним скриптом (scripts/deploy-openclaw-macos.sh, scripts/deploy-openclaw-linux.sh)
- ✅ **Create-bot skill v2:** Часть 12 — Memory Management & Session Health (pruneAfter, daily restart, weekly cleanup)
- ✅ **INFRASTRUCTURE_REGISTRY.md:** Мак Мурада (#8) зарегистрирован, статус ✅ "Настроен" (mac Мурада, 19.06)
- ✅ **Deploy scripts:** macOS + Linux одним скриптом (scripts/deploy-openclaw-macos.sh, scripts/deploy-openclaw-linux.sh)
- ✅ **Create-bot skill v2:** Часть 12 — Memory Management & Session Health (pruneAfter, daily restart, weekly cleanup)

### 3 тира работы

| Тир | Модель | Данные | Статус |
|-----|--------|--------|--------|
| **Private Mode** | Ollama (локально) | Все данные на устройстве | ✅ Работает |
| **Enhanced Mode** | Cloud LLM | GREEN (обезличенные) данные в облако | ✅ Работает |
| **Knowledge Mode** | Cloud LLM + RAG | GREEN + граф знаний The Brain | 🔧 В разработке |

---

## Версия v0.5.0 (текущая, 20 июня 2026)

### PII Pipeline
- RED/GREEN анонимизация: NER (qwen3:14b) + regex-классификатор
- MappingManager: консистентные токены [PERSON_N], [EMAIL_N], [PHONE_N]
- Deanonymizer: локальная подмена масок на реальные имена перед доставкой
- 22 000+ файлов, 749 persons, 744 emails, 0 утечек ПДн
- Meetings transcripts и Calendar pipeline интегрированы
- Memory PII-очистка: 102 файла, 1412 замен
- Name Lookup: ФИО → [PERSON_N] с fuzzy matching для склонений

### Brain Ingest
- Extraction: DeepSeek V4 Pro (106 атомов, 0 галюцинаций, 160 сек)
- Validation: GLM 5.1 (cross-model верификация)
- Pipeline: 707 сек → 198 сек (−72%)
- 937 атомов, 16 типов сущностей, 12 типов связей
- **Новое (19.06):** Бенчмарк 7 моделей, принята оптимальная конфигурация (DeepSeek V4 Pro extract + GLM 5.1 validate + qwen3:14b NER)
- **Обновление (22.06):** 1042 атома (+105 за 2 дня), brain ingest nightly работает стабильно

### Коммерческая лицензия + Deploy
- MIT → Proprietary Commercial License
- Production / Hosting / Integration / Evaluation лицензии
- Продукт позиционируется для B2B и корпоративных клиентов
- **Обновление (22.06):** Deploy scripts macOS+Linux — проверены в продакшне (мак Мурада). INFRASTRUCTURE_REGISTRY.md #8 — статус "Настроен".
  - Backup script `scripts/backup.sh` — добавлен обработчик exit 23 (race condition sqlite-wal)

---

## Версия v0.6.0 (следующая)

**Цель:** Knowledge Mode RAG + персональный граф знаний + прямой чат с lookup.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | **Knowledge Mode RAG** — embed → retrieve → augment summary prompt с контекстом из The Brain | P0 | 3 дня |
| 2 | **Knowledge Base индексация** — индексация PII-free данных для семантического поиска | P0 | 2 дня |
| 3 | **Friday-Brain-Personal** — персональный граф знаний для некорпоративного контекста | P1 | 2 дня |
| 4 | **Прямой чат lookup** — в чате с агентом: пользователь пишет ФИО → agent lookup → [PERSON_N] → обработка без утечки ПДн | P0 | 2 дня |
| 5 | `the-jarvice knowledge` CLI (index, search, stats) | P1 | 1 день |
| 6 | Context window management: приоритизация релевантного контекста | P1 | 1.5 дня |
| 7 | Knowledge Mode toggle в configure wizard | P1 | 0.5 дня |

**KPIs:**
- RAS retrieval latency: < 200 мс
- Context augmentation: +40% к точности сводок с фактами из The Brain
- Прямой чат lookup: < 100 мс на запрос ФИО

---

## Версия v0.7.0

**Цель:** Multi-tenant архитектура и командные workflow.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | **Multi-tenant архитектура** — изоляция данных и конфигов для нескольких пользователей на одной инстанции | P0 | 3 дня |
| 2 | **Team workflows** — маршрутизация сводок и действий между членами команды | P0 | 2 дня |
| 3 | **Ролевая модель доступа** — admin / manager / employee с разными правами на данные и действия | P0 | 2 дня |
| 4 | **Shared knowledge graph** — общий корпоративный граф + персональные подсубграфы | P1 | 2 дня |
| 5 | **Delegation workflow** — делегирование задач и писем между пользователями через EWS actions | P1 | 1.5 дня |
| 6 | **Team dashboard** — обзор статусов и метрик по команде | P1 | 2 дня |
| 7 | **Audit trail** — расширенный аудит действий всех пользователей | P1 | 1 день |

---

## Версия v1.0.0 — Enterprise

**Цель:** Enterprise-grade готовность: SSO, compliance, audit, масштабирование.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | **SSO / SAML 2.0** — интеграция с корпоративными IdP (Active Directory, Okta, Keycloak) | P0 | 3 дня |
| 2 | **Audit log** — полный аудит всех действий: кто, что, когда, результат. Соответствие корпоративным требованиям безопасности | P0 | 2 дня |
| 3 | **Compliance** — соответствие 152-ФЗ (Россия), GDPR (ЕС): журналы доступа к ПДн, политика хранения, право на удаление | P0 | 3 дня |
| 4 | **RBAC** — ролевая модель доступа с гранулярными правами на функции и данные | P0 | 2 дня |
| 5 | **DLP integration** — интеграция с корпоративными DLP-системами (InfoWatch, Solar Dozor) | P1 | 2 дня |
| 6 | **Multi-region deployment** — развёртывание в нескольких регионах для соответствия требованиям локализации данных | P1 | 2 дня |
| 7 | **SLA monitoring** — метрики доступности, latency, error rate с алертингом | P1 | 1.5 дня |
| 8 | **High availability** — резервирование компонентов, failover, graceful degradation | P1 | 3 дня |
| 9 | **API gateway** — REST API для интеграции с внешними системами (CRM, ERP, ITSM) | P2 | 2 дня |
| 10 | **Admin console** — веб-интерфейс для управления инстанциями, пользователями, лицензиями | P2 | 3 дня |

**KPIs:**
- Uptime: 99.9% (≤ 8.76 ч downtime/год)
- Audit log: 100% действий зафиксированы
- SSO login: < 3 сек
- Compliance audit: pass с первого раза

---

## Архитектурные решения

| Решение | Дата | Обоснование |
|---------|------|-------------|
| Local-first | 2026-05-21 | ПДн не покидают устройство. Cloud = опция. |
| RED/GREEN pipeline | 2026-05-21 | Исходники (RED, chmod 700) → обезличенные (GREEN) для обработки |
| 3 тира | 2026-05-21 | Private → Enhanced → Knowledge, progressive disclosure |
| Brain Ingest v2.1: LLM Cross-Validation | 2026-06-05 | verify.py + llm_verify.py с 3 correction cycles |
| DeepSeek V4 Pro для extraction | 2026-06-20 | 106 атомов, 0 галлюцинаций, лучший результат в бенчмарке |
| GLM 5.1 для validation | 2026-06-20 | Cross-model diversity — разная архитектура от extraction |
| qwen3:14b для NER | 2026-06-20 | Локальная модель, не передаёт ПДн наружу, достаточное качество распознавания |
| Memory PII-очистка | 2026-06-20 | 102 файла memory/*.md обезличены, консистентные токены с GREEN/ |
| Deploy scripts (macOS/Linux) | 2026-06-20 | Полный деплой одним скриптом, проверено на маке Мурада |
| Create-bot v2: Session Health | 2026-06-20 | pruneAfter 7d, maxEntries 60, daily restart cron |
| Commercial License | 2026-06-20 | Переход с MIT на proprietary для B2B-продаж |
| Backup script exit 23 | 2026-06-22 | Race condition sqlite-wal → допустимый код, 2>/dev/null убран |
| memory_search timeout | 2026-06-23 | QMD embedding provider timeout 15s при загрузке Ollama. BM25 fallback работает. Требует graceful degradation. |

---

## Версионирование

| Версия | Дата | Ключевое |
|--------|------|----------|
| v0.1.0 | 2026-05 | CLI, config, doctor, setup |
| v0.1.1 | 2026-05 | Exchange, PII, pipeline |
| v0.1.2 | 2026-05 | Teams, security fixes |
| v0.2.0 | 2026-05 | Providers, configure --quick, cron |
| v0.2.1 | 2026-05 | Linux, CI, non-interactive, status |
| v0.3.0 | 2026-06 | Friday-Ops Agent, heartbeat, self-heal |
| v0.3.1 | 2026-06 | Multi-Client Deployment |
| v0.4.0 | 2026-06 | Enhanced Mode (cloud models) |
| **v0.5.0** | **2026-06-20** | **PII Pipeline, Brain Ingest v2.1, Memory anonymization, Name Lookup, Deploy scripts, Commercial License** |
| v0.5.1 | 2026-06-23 | memory_search timeout fix (QMD graceful degradation), Brain notes 1042, backup exit 23 |
| v0.6.0 | Q3 2026 | Knowledge Mode RAG, Friday-Brain-Personal, прямой чат lookup |
| v0.7.0 | Q4 2026 | Multi-tenant, team workflows |
| v1.0.0 | 2027 | Enterprise: SSO, audit log, compliance |