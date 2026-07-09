# The Jarvice — Roadmap

> **Последнее обновление: 2026-07-09**
> **Версия продукта: v0.5.4**

---

## Текущий статус

**Версия:** v0.5.4
**Дата релиза:** 3 июля 2026
**Статус:** 🟡 Knowledge Mode в разработке (Brain v3.1 pipeline running)

### Что работает в v0.5.4

- ✅ **PII Pipeline** — полная анонимизация: RED/GREEN, NER (qwen3:14b) + regex, MappingManager, Deanonymizer
  - 22 000+ файлов обработано, 749 persons / 744 emails в mapping, 0 утечек ПДн
  - Meetings transcripts перенесены в pipeline
  - Calendar pipeline: Exchange → RED/calendar/ → anonymizer → GREEN/calendar/
- ✅ **Brain Ingest v3.1** — полностью переработанный конвейер на облачных моделях
  - DeepSeek V4 Pro (extraction) → GLM 5.2 (validation) → Kimi K2.6 (resolution)
  - Pipeline ускорение: многопоточность (15 workers), ~942/2505 events (~14K atoms, ~9.5K edges)
  - Vault generator с персонализацией (в плане — шаг 8.9)
  - **В работе:** полный прогон memory/ 8 агентов → canon.sqlite
- ✅ **Memory PII-очистка** — 102+ файла memory/*.md обезличены, 1412+ замен, 0 утечек
- ✅ **Name Lookup + Deanonymizer** — lookup ФИО → [PERSON_N], fuzzy matching для склонений
- ✅ **CLI:** configure (interactive/--quick/--non-interactive), run, doctor, status, enable/disable, uninstall
- ✅ **Exchange Scraper:** EWS, stealth User-Agent, keyring+Keychain, email+calendar
- ✅ **Teams Scraper:** IC3 token, chats + meetings (🟡 transcripts зависают — headless Playwright issue)
- ✅ **Summary Generator:** GLM 5.2 Cloud (primary), Kimi K2.6 Cloud (fallback)
- ✅ **Telegram Delivery:** Bot API, HTML, chunking 4096 chars (🟡 баг доставки — сообщения пропадают/перезаписываются)
- ✅ **Provider abstraction:** Ollama, OpenAI, Anthropic
- ✅ **Security:** Keychain creds, log sanitization, audit log, path traversal protection
- ✅ **Linux support:** apt/dnf/yum, keyrings.alt fallback
- ✅ **CI:** GitHub Actions (macOS + Ubuntu, Python 3.10-3.13)
- ✅ **8 агентов + 1 неактивный:** Friday, Jarvis, Sophie, Ultron, Dev, ArGO, Hera, (+ Edith ⏸️)
- ✅ **23 крона (активных):** сводки, скрейпинг, brain ingest, health checks, backup, security watchdog
- ✅ **Multi-client deployment:** VPS, macOS, Linux — deploy scripts проверены в продакшне
- ✅ **Deploy scripts:** macOS + Linux одним скриптом
- ✅ **Create-bot skill v2.1:** onboarding + SYSTEM.md self-awareness (877 строк)
- ✅ **INFRASTRUCTURE_REGISTRY.md:** 10 машин, все активны/настроены
- ✅ **Sophie — Baserow Product Operator:** GLM-5.2 primary, MCP Baserow глобальный, 12 таблиц в Database 13
- ✅ **Dev-агент v1.0:** TDD, code review, spike (DeepSeek V4 Pro)
- ✅ **Ultron safety gates:** 4 уровня риска, backup обязателен, drift detection

### 3 тира работы

| Тир | Модель | Данные | Статус |
|-----|--------|--------|--------|
| **Private Mode** | Ollama (локально) | Все данные на устройстве | ✅ Работает |
| **Enhanced Mode** | Cloud LLM | GREEN (обезличенные) данные в облако | ✅ Работает |
| **Knowledge Mode** | Cloud LLM + граф знаний | GREEN + граф знаний The Brain | 🔄 В разработке (Brain v3.1 pipeline RUNNING) |

---

## Версия v0.5.4 (текущая, 3 июля 2026)

### Brain v3.1 Pipeline (в разработке)
- **Цель:** Полное пересоздание The Brain на облачных моделях с графовой архитектурой
- **Фазы 8.1–8.7:** ✅ Завершены
  - 8.1 NER Worker: 73 tests, 0 false positives
  - 8.2 Sanitizer: 65 tests, 0 leaks
  - 8.3 Consolidator: 660 atoms, 43 edges (тест)
  - 8.4 Validator: 18 passed, 12 flagged, 13 errors
  - 8.5 Resolver: 7 resolved, 13 rejected, 5 human
  - 8.6 Pipeline orchestration
  - 8.7 Парсинг memory/ 8 агентов → 2505 событий + NER + Sanitize
- **Фаза 8.8:** 🔄 Полный прогон ~942/2505 events, ~14K atoms, ~9.5K edges, 15 workers
  - deepseek-v4-flash/pro (extraction) + glm-5.2 (validation)
  - Идемпотентность: SSLError retry (3 attempts), 500 retry
  - Оценка завершения: ~18ч (к 12:00 пятницы 10.07)
- **Фаза 8.8.1:** ⏳ Проверка потерянных events (0 atoms) — вытащить, сверить с логом, прогнать потерянные
- **Фаза 8.9:** ⏳ Vault generator с персонализацией
- **Фаза 8.10:** ⏳ Тесты §11
- **Фаза 8.11:** ⏳ Расширение источников (docs/, dreaming/, inbound .docx/.pdf/.csv/.xlsx/.pptx/.ogg/.jpg)

### PII Pipeline
- RED/GREEN анонимизация: NER (qwen3:14b) + regex-классификатор
- MappingManager: консистентные токены [PERSON_N], [EMAIL_N], [PHONE_N]
- Deanonymizer: локальная подмена масок на реальные имена перед доставкой
- 22 000+ файлов, 749 persons, 744 emails, 0 утечек ПДн
- **В работе:** Teams transcripts (зависают на Playwright headless — headless=False todo)

### Коммерческая лицензия + Deploy
- MIT → Proprietary Commercial License
- Production / Hosting / Integration / Evaluation лицензии
- Продукт позиционируется для B2B и корпоративных клиентов
- **В работе:** Sophie — Head of Product & Experience, Baserow Product Operator

---

## Известные проблемы (Known Issues)

| # | Проблема | Влияние | Статус | Путь решения |
|---|----------|---------|--------|--------------|
| 1 | **Teams transcripts зависают** — Playwright headless=True timeout | Нет новых транскрипций с 04.07 | 🔴 Блокер | headless=False или увеличить таймауты |
| 2 | **Teams sync scraper FAILED** — token refresh timeout/SIGKILL | Потеря данных чатов | 🔴 Блокер | Fix teams_login.py — обработка «остаться в системе?» |
| 3 | **Telegram delivery баг** — сообщения пропадают/перезаписываются | Часть сводок не доходит | 🟡 Деградация | Не рестартить gateway при работе агентов; ждёт фикса OpenClaw |
| 4 | **Memory Search (QMD)** — vector unknown, embedModel NOT SET | Поиск не работает | 🟡 Заморожено | Решение Вадима: НЕ чинить, переход на Brain v3.1 |
| 5 | **ArGO кроны error** — 4/5 джобов error 6 дней | Напоминания о добавках не работают | 🟡 Деградация | Требует investigation |
| 6 | **Ultron Brain Stats error** — 9 consecutive | Нет статистики Brain | 🟡 Деградация | Brain v3.0 заморожен, скорее всего несовместимость |
| 7 | **Weekly Docs Update error** — 5 consecutive | Документация не обновляется автоматически | 🟡 Деградация | Требует investigation |
| 8 | **dev-ssh-key** — НЕ найден в Keychain | Dev-агент может не иметь доступа к репо | 🟡 Риск | Проверить и добавить в Keychain |
| 9 | **Brain Ingest nightly error** — 9 consecutive (v3.0 заморожен) | Ночной прогон не работает | 🟡 Ожидается | Заменён на Brain v3.1 pipeline |
| 10 | **Exchange скрейпинг** — mail.fsk.ru TLS timeout, O365 mailbox not exist | Почта не синхронизируется | 🟡 Заморожено | Ждёт новых кредов от Вадима |

---

## Версия v0.6.0 (следующая)

**Цель:** Knowledge Mode RAG + персональный граф знаний + прямой чат с lookup.

| # | Задача | Приоритет | Оценка | Статус |
|---|--------|-----------|--------|--------|
| 1 | **Brain v3.1 завершить** — 8.8 (полный прогон), 8.9 (vault), 8.10 (тесты §11), 8.11 (источники) | P0 | 5 дней | 🔄 В процессе |
| 2 | **Knowledge Mode RAG** — embed → retrieve → augment summary prompt с контекстом из The Brain | P0 | 3 дня | ⏳ Зависит от Brain v3.1 |
| 3 | **Knowledge Base индексация** — индексация PII-free данных для семантического поиска | P0 | 2 дня | ⏳ Зависит от Brain v3.1 |
| 4 | **Friday-Brain-Personal** — персональный граф знаний для некорпоративного контекста | P1 | 2 дня | ⏳ Зависит от Brain v3.1 |
| 5 | **Прямой чат lookup** — в чате с агентом: пользователь пишет ФИО → agent lookup → [PERSON_N] → обработка без утечки ПДн | P0 | 2 дня | ⏳ Зависит от Brain v3.1 |
| 6 | **Teams transcripts fix** — headless=False или увеличение таймаутов | P0 | 0.5 дня | 🔴 Блокер |
| 7 | **Teams sync scraper fix** — обработка «остаться в системе?» в teams_login.py | P0 | 0.5 дня | 🔴 Блокер |
| 8 | `the-jarvice knowledge` CLI (index, search, stats) | P1 | 1 день | ⏳ |
| 9 | Context window management: приоритизация релевантного контекста | P1 | 1.5 дня | ⏳ |
| 10 | Knowledge Mode toggle в configure wizard | P1 | 0.5 дня | ⏳ |

**KPIs:**
- Brain v3.1: 100% events processed, 0 потерянных
- RAS retrieval latency: < 200 мс
- Context augmentation: +40% к точности сводок с фактами из The Brain
- Прямой чат lookup: < 100 мс на запрос ФИО
- Teams transcripts: успешный прогон ≥ 90%

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
| **Brain v3.1: cloud models pipeline** | **2026-07-03** | Полный редизайн на DeepSeek V4 Pro + GLM 5.2 + Kimi K2.6, многопоточность, идемпотентность, SSLError retry |
| **Teams token recovery: пароль в Keychain** | **2026-07-07** | НЕТ MFA, ChevroletCruze2009!!!. Скрипт не нажимает «остаться в системе?» |
| **Sophie → Baserow Product Operator** | **2026-07-08** | GLM-5.2 primary, MCP Baserow глобальный, 12 таблиц в Database 13 |

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
| v0.5.0 | 2026-06-20 | PII Pipeline, Brain Ingest v2.1, Memory anonymization, Name Lookup, Deploy scripts, Commercial License |
| v0.5.1 | 2026-06-23 | memory_search timeout fix, Brain notes 1042, backup exit 23, landing SEO |
| **v0.5.4** | **2026-07-03** | **Brain v3.1 pipeline (DeepSeek + GLM + Kimi, многопоточность, 15 workers), Sophie Baserow Product Operator, Dev-агент v1.0, Ultron safety gates** |
| v0.6.0 | Q3 2026 | Knowledge Mode RAG, Brain v3.1 полный, прямой чат lookup, Teams fixes |
| v0.7.0 | Q4 2026 | Multi-tenant, team workflows |
| v1.0.0 | 2027 | Enterprise: SSO, audit log, compliance |
