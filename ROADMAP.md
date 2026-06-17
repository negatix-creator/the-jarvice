# The Jarvice — Roadmap

> Последнее обновление: 2026-06-17

## Текущий статус

**Версия:** v0.3.0
**LOC:** 9500+ | **Тестов:** 267 (265 pass на VPS)
**Спринтов завершено:** 5 (Sprint 001–005)
**Первый клиентский деплой:** ✅ 2026-06-04 (VPS 2.58.65.124, Дмитрий)
**Последнее обновление инфраструктуры:** 2026-06-17

### Что работает (v0.3.0)
- ✅ CLI: configure (interactive/--quick/--non-interactive), run, doctor, status, enable/disable, uninstall
- ✅ Exchange Scraper: EWS, stealth User-Agent, keyring+Keychain fallback, email+calendar
- ✅ PII Pipeline: RED/GREEN, regex-классификатор (телефоны/email/ИНН/СНИЛС), MappingManager, Deanonymizer
- ✅ Summary Generator: Ollama glm-5.1:cloud (default), русский промпт, temperature 0.3
- ✅ Telegram Delivery: Bot API, HTML, chunking 4096 chars
- ✅ Provider abstraction: OllamaProvider, OpenAIProvider, AnthropicProvider
- ✅ Context scrubber: standard/strict
- ✅ Audit log, log sanitization, token age tracking, rate limiting, sender pseudonymization
- ✅ Linux support: apt/dnf/yum, keyrings.alt fallback на headless
- ✅ CI: GitHub Actions (macOS + Ubuntu, Python 3.10-3.13)
- ✅ VPS deployment: протестировано на 78.17.56.204
- ✅ **Full System Setup:** 13-step installer (OpenClaw + Jarvice + Ollama + agent config)
- ✅ **Cloud Models:** glm-5.1:cloud default, nomic-embed-text embeddings
- ✅ **OpenClaw Integration:** workspace files, gateway start, channels add
- ✅ **Interactive Credentials:** Telegram token, Exchange, Ollama signin
- ✅ **Config Generation:** config.yaml with cloud models preconfigured
- ✅ **Nightly Backup:** BACKUP_OK (7.0G, ротация 10/10)
- ✅ **Gateway stability:** PID 88930, RSS ~825MB, uptime 12д 9ч (стабильно)
- ✅ **Teams Sync v2:** 2 транскрипта (CPO StandUp, Согласование приказа)
- ⚠️ **Teams Token Refresh:** протух ~13:34 04.06, авторефреш нестабилен (workaround: 48h window + 30s timeout)
- ✅ **VPS health:** load 0.23, swap 67MB (RAM 299MB used), uptime 54+ дней
- ✅ **First Client Deployment:** VPS 2.58.65.124 (Ubuntu 24.04, 4GB RAM)
- ✅ **Brain Ingest v2.1:** LLM Cross-Validation (7 фаз: Collect → Extract → verify.py → llm_verify.py → Merge → Update → Report)
- ✅ **OpenClaw 2026.6.1:** обновлён на клиентской машине, gateway стабильно работает
- ✅ **Gemma 3:27b:** добавлена в Ollama (gemma3:27b-cloud), используется для задач medium-сложности
- ⚠️ **Jarvis MEMORY.md:** 22-23KB (превышает порог 20KB) — требуется компактизация (5 срабатываний watchdog 16.06)
- ✅ **Jarvis MEMORY.md compacted:** 19.8 KB ✅ (в норме, компактизирован с 23.4 KB 11.06)
- ⚠️ **Jarvis model change:** deepseek-v4-pro:cloud → glm-5.1:cloud (fallbacks: kimi-k2.6:cloud, deepseek-v4-flash:cloud) — 2026-06-05, по причине timeout deepseek
- ⚠️ **Teams Token Refresh**: стабильное обновление — workaround с 48h window + 30s HTTP timeout, но token протух 04.06
- ⚠️ **Brain Ingest cron:** дневной (15:00) отсутствует в cron list — известная проблема
- ✅ **Brain Stats (Ultron):** 2 крон-джоба (утро 15:00, вечер 03:10) — работают, документированы
- ✅ **Config hash baseline:** sha256 b0f29774b752e129 ✅ (актуален, совпадает с текущим)
- ✅ **OpenClaw alerts log:** 1 запись 14.06 (config modified alert — ожидается при обновлении)
- ⚠️ **Friday Daily Digest:** consecutiveErrors=3 (Telegram delivery failed, 17h ago) — не восстановлено
- ⚠️ **Friday Weekly Docs Update:** Telegram delivery failed (7d ago) — не восстановлено
- ⚠️ **GLM-5.2:** доступна от Zhipu (13.06), 1M контекст, MIT лицензия — ждём в Ollama cloud
- ⚠️ **Ollama brew outdated:** ollama в списке outdated brew (17.06) — требует `brew upgrade`
- ✅ **Config integrity:** sha256 b0f29774b752e129 ✅ (совпадает с baseline)

### 3 тира (Product Council)
| Тир | Модель | Данные | Статус |
|-----|--------|--------|--------|
| **Private Mode** | Ollama (локально) | Все данные на устройстве | ✅ Работает |
| **Enhanced Mode** | OpenAI/Anthropic | GREEN (обезличенные) данные в облако | 🔧 Провайдеры есть, scrubber есть, wizard нет |
| **Knowledge Mode** | The Brain RAG | Контекст из графа знаний | ❌ Не начат |

---

## Завершённые спринты

### Sprint 001 — Foundation (v0.1.0)
CLI skeleton, config, state, doctor, setup.sh, BaseScraper, uninstall

### Sprint 002 — Exchange + PII (v0.1.1)
ExchangeScraper (EWS), PII Anonymizer (RED/GREEN), pipeline run --once, Telegram delivery

### Sprint 003 — Teams + Security (v0.1.2)
TeamsScraper (IC3), configure wizard, PII path validation (CRIT-01), prompt hardening, HTML delivery

### Sprint 004 — Providers + UX (v0.2.0)
Provider abstraction, context scrubber, audit log, configure --quick, enable/disable cron, setup.sh idempotent

### Sprint 005 — Linux + CI (v0.2.1)
configure --non-interactive, uninstall PII wipe, status, Linux support, Makefile, GitHub Actions CI

---

## Предстоящие спринты

### Sprint 006 — Friday-Ops Agent (v0.3.0)

**Цель:** Friday-Ops — лёгкий агент-наблюдатель на клиентской машине для мониторинга, self-heal и инфраструктурной валидации.

> **Обновлено 2026-06-01:** учтена самовалидация Jarvis (prompt-level) — Friday-Ops добавляет infra-level валидацию поверх неё.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | Friday-Ops OpenClaw agent: конфиг, SOUL.md, AGENTS.md | P0 | 0.5 дня |
| 2 | Heartbeat: doctor, disk, cron, Ollama, PII integrity | P0 | 1 день |
| 3 | **Pre-flight validation**: перед запуском крона проверить доступность модели (Ollama/cloud), Exchange, диска | P0 | 1 день |
| 4 | Self-heal: restart Ollama, restart cron, rollback version | P0 | 1.5 дня |
| 5 | **Model fallback orchestrator**: при 502/timeout автоматический switch на fallback модель, алерт при consecutive failures | P0 | 0.5 дня |
| 6 | Alerting → основной Friday (метрики, ошибки, алерты) + Jarvis failure alerting (≥2 errors → Telegram) | P0 | 1 день |
| 7 | **Post-run validation**: проверить что сводка доставлена, файлы записаны, нет silent failures | P1 | 1 день |
| 8 | Secure tunnel: WireGuard/SSH для remote debug | P1 | 1.5 дня |
| 9 | `the-jarvice ops` CLI subcommand (status, heal, tunnel) | P1 | 1 день |
| 10 | Автоматические обновления: pull + restart + smoke test | P1 | 1 день |

**Два уровня валидации:**

| Уровень | Где | Что проверяет | Действие при ошибке |
|---------|------|---------------|--------------------|
| **Prompt-level** (Jarvis) | Внутри cron payload | Факты vs источники, точность %, консистентность | Исправление + повтор валидации до ≥95% |
| **Infra-level** (Friday-Ops) | До/после запуска крона | Ollama жив? Exchange доступен? Диск есть? Сводка доставлена? | Fallback модель, restart, алерт |

**KPIs:**
- Heartbeat ≤ 30 сек
- Pre-flight check ≤ 10 сек
- Self-heal: Ollama restart < 60 сек, cron fix < 30 сек
- Alert latency: < 2 мин до основного Friday
- Post-run validation: < 15 сек после завершения крона
- Rollback: < 5 мин на откат версии

---

### Sprint 007 — Multi-Client Deployment (v0.3.1)

**Цель:** Деплой Jarvice + Friday-Ops на клиентскую машину "под ключ".

**Реальный опыт (2026-06-04):** Первый клиентский деплой на VPS 2.58.65.124. 29 известных проблем выявлено. Деплой был ручной (SSH + scp), не через Docker/Ansible. Playbook: `docs/deploy-jarvis-playbook.md` (1180 строк, 29 known issues). Опыт Алексея (problemgoout-ops/deploy-agent): Часть -1 (Защита сессии, 8 правил).

**Статус инфраструктуры (2026-06-16):**
- VPS 78.17.56.204 (prod): MTProto proxy ✅ Up 5+ дней, load 0.23, swap 1.0Gi, uptime 53+ дней
- VPS 2.58.65.124 (client): OpenClaw gateway inactive, swap настроен, cron не добавлены
- Teams sync: токен протухает ~20ч, авторефреш нестабилен (протух 04.06 ~13:34)
- Gateway: PID 65060, RSS ~832MB, uptime 11д 9ч (стабильно)
- Brain Ingest ночной: ✅ ok (24h ago)
- Brain Stats (Ultron): 2 крон-джоба (утро 15:00, вечер 03:10) — работают
- Config hash: sha256 b0f29774b752e129 ✅ (совпадает с baseline)
- Friday Daily Digest: ❌ error (17h ago, Telegram delivery failed, consecutiveErrors=3) — не восстановлено
- Friday Weekly Docs Update: ❌ error (7d ago, Telegram delivery failed) — не восстановлено
- HERA перепрофилирована в бизнес-консультанта МИТ-оф (14.06)
- Jarvis MEMORY.md: 23KB (превышает порог 20KB) — требуется компактизация

| # | Задача | Приоритет | Оценка | Статус |
|---|--------|-----------|-------|--------|
| 1 | Docker Compose: Jarvice + Friday-Ops + Ollama | P0 | 2 дня | 🔧 Проектирование |
| 2 | Ansible playbook: полная установка с нуля | P0 | 1.5 дня | 🔧 Playbook v1.2 (manual) |
| 3 | `setup.sh --ops-mode`: ставит оба агента, изолирует от клиента | P0 | 1 день | 🔵 Не начат |
| 4 | Клиентская изоляция: отдельный системный пользователь, нет доступа к конфигам | P0 | 1 день | 🔵 Не начат |
| 5 | Credential bootstrap: JARVICE_* env vars → keyring | P1 | 0.5 дня | ⚠️ keyring на Linux = keyrings.alt |
| 6 | Smoke test: E2E на чистой машине (VPS) | P0 | 1 день | ✅ VPS 2.58.65.124 |
| 7 | Документация: Deployment Guide для ops | P1 | 0.5 дня | ✅ deploy-jarvis-playbook.md |
| 8 | Swap для <8GB RAM (2GB + swappiness=10) | P0 | 0.1 дня | ✅ VPS 2.58.65.124 (swap настроен) |
| 9 | Workspace изоляция (дефолтный workspace — удалять) | P0 | 0.1 дня | ⚠️ Выявлено при деплое |
| 10 | Device pairing flow (approve → cron add) | P1 | 0.5 дня | ⚠️ Chicken-egg проблема |
| 11 | ONBOARDING.md в AGENTS.md (не отдельный файл) | P1 | 0.1 дня | ✅ Проверено |
| 12 | USER.md мульти-пользовательский (все allowFrom) | P1 | 0.1 дня | ✅ Проверено |
| 13 | Ollama cloud keypair copy (Linux) | P1 | 0.2 дня | ✅ Проверено |
| 14 | Python heredoc через SSH → scp вместо | P2 | 0.1 дня | ✅ Проверено |
| 15 | **Cron jobs на клиенте**: добавить через CLI после pairing | P0 | 0.5 дня | ⚠️ Не добавлены на 2.58.65.124 |
| 16 | **Gateway auto-start**: systemd service для OpenClaw | P0 | 0.2 дня | ⚠️ inactive на 2.58.65.124 |

**29 известных проблем** (полный список: `docs/deploy-jarvis-playbook.md`):
- #21: 4GB RAM → OOM при рестарте (нужен swap) — SWAP настроен на VPS 2.58.65.124 ✅
- #22: Дефолтный workspace подхватывается глобально — Документировано в deploy playbook ✅
- #23: FIRST_MESSAGE.md не работает — онбординг в AGENTS.md — Проверено, работает ✅
- #24: USER.md с 1 юзером → отказ работать с другими — Все пользователи в USER.md ✅
- #25: `openclaw cron add` требует pairing (chicken-egg) — Device approval workflow документирован ✅
- #26: Python heredoc через SSH бьёт кавычки → scp — Используется scp ✅
- #27: Ollama keypair на Linux в 2 местах — keypair скопирован на оба VPS ✅
- #28: `--non-interactive` не существует — `openclaw onboard --install-daemon` без флага ✅
- #29: Скрипты в дефолтном workspace удаляются при чистке — Скрипты в agent-specific workspace ✅
- **#30: Friday Daily Digest — Telegram delivery failed** — consecutiveErrors=3, 14.06. Не восстановлено. Возможно: delivery channel/to неправильно настроены, или Telegram API rate limit.
- **#31: EDITH Месячный отчёт — error** — 14d ago, не восстановлено.
- **#32: Brain Ingest дневной (15:00) — отсутствует в cron list** — известная проблема, не добавлен.
- **#33: Ollama brew outdated** — ollama в списке outdated brew пакетов (17.06). Требует `brew upgrade ollama`.

**KPIs (обновлены по реальному опыту):**
- git clone → работающий Jarvice: ≤ 30 мин на чистой VPS (реально: ~40 мин manual, target: 15 мин с Ansible)
- configure --quick → первая сводка: ≤ 5 мин
- Клиент НЕ имеет доступа к конфигам и логам
- **4GB RAM VPS**: swap обязателен (2GB), OOM без него
- **Cron jobs**: must be added manually after device pairing (chicken-egg)
- **Gateway auto-start**: systemd service required for persistence

---

### Sprint 008 — Enhanced Mode (v0.4.0)

**Цель:** Cloud модели с PII scrubbing, configure wizard progressive disclosure.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | Configure Wizard: 3 уровня (basic/models/advanced) | P0 | 2 дня |
| 2 | Cloud providers: OpenAI, Anthropic (API keys → Keychain) | P0 | 2 дня |
| 3 | Context scrubbing: GREEN → cloud, local-only fields removed | P0 | 1.5 дня |
| 4 | Privacy UX: dry-run с показом что уходит куда | P0 | 1 день |
| 5 | `the-jarvice model switch` команда | P1 | 0.5 дня |
| 6 | Fallback: cloud → Ollama при недоступности | P1 | 1 день |
| 7 | Zero-data-retention провайдеры: документация | P2 | 0.5 дня |

**Решения Product Council:**
- Enhanced Mode = cloud с обезличенными данными
- dry-run обязателен перед отправкой в облако
- Fallback автоматический (cloud → local)

---

### Sprint 009 — Zero Inbox: умная сортировка почты (v0.5.0)

**Цель:** Jarvice не только сводит — он действует. Классификация писем, перемещение в папки Outlook, черновики ответов, делегирование.

> **Inspired by:** CIO Zero Inbox (А101, Алексей Сложеникин) — n8n + LLM + EWS. Мы берём лучшее (действия, sticky routing, экономия LLM) и добавляем своё (PII pipeline, self-validation, multi-source).

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | **Action classifier**: LLM-классификация писем (reply_now, reply_later, delegate, ack_and_schedule, fyi, archive) | P0 | 2 дня |
| 2 | **Two-level routing**: правила без LLM (VIP-список, рассылки, CC>10) + LLM для остального | P0 | 1.5 дня |
| 3 | **EWS actions**: MoveItem (папки), CreateItem (черновики), пересылка (delegate) | P0 | 2 дня |
| 4 | **Draft reply generation**: LLM генерирует черновик ответа с контекстом из почты/Teams/memory | P0 | 2 дня |
| 5 | **Sticky thread routing**: ConversationId → та же папка/действие без повторного LLM-вызова | P0 | 1 день |
| 6 | **ChangeKey handling**: перечитывание ChangeKey после UpdateItem перед MoveItem | P0 | 0.5 дня |
| 7 | **PII-safe drafts**: черновики ответов проходят через GREEN pipeline перед отправкой в cloud LLM | P0 | 1 день |
| 8 | `the-jarvice inbox` CLI subcommand (classify, act, status) | P1 | 1 день |
| 9 | **Confirmation UX**: Telegram кнопки подтверждения перед действиями (reply_now, delegate) | P1 | 1.5 дня |
| 10 | **Fallback**: при ошибке LLM → action=fyi (безопасный режим) | P0 | 0.5 дня |

**Классификатор действий (по мотивам Zero Inbox):**

| Действие | Когда | Папка Outlook | Черновик | Telegram |
|---------|-------|-------------|----------|----------|
| `reply_now` | VIP/эскалация | ✉️ Ответить срочно | ✅ Да | 🔴 Приоритет |
| `reply_later` | Требует ответа, не срочно | ✉️ Ответить | ✅ Да | 🟡 Дайджест |
| `delegate` | Тема → отдел | 📤 Делегировано | ✅ + пересылка | 🟡 Дайджест |
| `ack_and_schedule` | Подтвердить + проработать | 📋 Запланировано | ✅ Да | 🟡 Дайджест |
| `fyi` | К сведению | ✅ Обработано | ❌ Нет | Дайджест |
| `archive` | Рассылка, спам | 🗄️ Архив | ❌ Нет | ❌ Нет |

**Наша инновация поверх Zero Inbox:**
- PII pipeline: черновики проходят через GREEN pipeline (у А101 — данные как есть)
- Self-validation: Jarvis проверяет черновик перед отправкой (у А101 — нет)
- Multi-source контекст: Teams + memory + транскрипции обогащают черновик
- Confirmation UX: человек подтверждает действия через Telegram кнопки

**KPIs:**
- Классификация: < 5 сек на письмо (правила), < 30 сек (LLM)
- Черновик ответа: < 60 сек
- LLM-экономия: ≥40% писем без LLM-вызова
- Точность маршрутизации: ≥90% (self-validation ≥95%)

---

### Sprint 010 — Knowledge Mode (v0.6.0)

**Цель:** The Brain RAG — контекст из графа знаний для сводок и черновиков.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | RAG pipeline: embed → retrieve → augment summary prompt | P0 | 3 дня |
| 2 | Knowledge Base: индексация PII-free данных | P0 | 2 дня |
| 3 | Context window management: prioritize relevant context | P1 | 1.5 дня |
| 4 | `the-jarvice knowledge` CLI (index, search, stats) | P1 | 1 день |
| 5 | Knowledge Mode toggle в configure | P1 | 0.5 дня |

---

### Sprint 011 — Ops Dashboard + Remote Management (v0.7.0)

**Цель:** Централизованная оркестрация множества клиентских инстансов.

| # | Задача | Приоритет | Оценка |
|---|--------|-----------|--------|
| 1 | Friday Dashboard: список инстансов, статусы, метрики | P0 | 2 дня |
| 2 | Remote config push: обновление конфигов через туннель | P0 | 1.5 дня |
| 3 | Remote debug: SSH через WireGuard tunnel | P0 | 1 день |
| 4 | Batch updates: катить обновления на N инстансов | P1 | 2 дня |
| 5 | Alert routing: Friday-Ops → основной Friday → Вадим | P1 | 1 день |
| 6 | Audit log aggregation: логи со всех инстансов → центральный | P2 | 1.5 дня |

---

## Бэклог (без спринта)

- OAuth2 для Exchange 365 (Microsoft Graph API)
- Web dashboard (самообслуживание для клиентов)
- Оплата/монетизация (SaaS billing)
- Per-domain trust levels (разные уровни доверия для разных доменов)
- brew formula для macOS
- Docker Hub образ
- ~~Model fallback цепочки~~ → реализовано 2026-06-01 (deepseek-v4-pro:cloud → glm-5.1:cloud → qwen2.5:14b)
- **Brain Ingest v2.1** → реализовано 2026-06-05 (7 фаз с llm_verify.py cross-validation)
- **Gemma 3:27b** → добавлена 2026-06-07 (gemma3:27b-cloud для medium-сложности задач)
- Teams Graph API (полноценный, не только IC3)
- **ConversationId-based sticky routing** (Sprint 009)
- **ChangeKey re-read after UpdateItem** (Sprint 009)
- **Action confirmation via Telegram inline buttons** (Sprint 009)
- **Cron persistence на клиентских VPS** → выявлено 2026-06-08, **документировано 2026-06-10**: gateway inactive на клиентском VPS, cron jobs не добавлены — документировано в deploy playbook (chicken-egg через device pairing)
- **Friday Daily Digest error (Telegram delivery)** → выявлено 2026-06-08, **error 2026-06-13**: Telegram delivery failed, consecutiveErrors=3. Возможно: delivery channel/to неправильно настроены, или Telegram API rate limit. Не восстановлено.
- **Teams token refresh reliability** → выявлено 2026-06-08, **workaround работает**: custom script с 48h window + 30s HTTP timeout, 2 транскрипта успешно скачаны (08.06), token обновлён 09.06 15:00, **протух 04.06 ~13:34** — авторефреш нестабилен (net::ERR_TIMED_OUT, MFA/captcha)
- **Brain Stats (Ultron) cron jobs** → добавлены 2026-06-13: утро 15:00 + вечер 03:10, 2 крон-джоба документированы и работают
- **Config hash baseline** → обновлён 2026-06-14: sha256 b0f29774b752e129, совпадает с текущим

---

## Архитектурные решения

| Решение | Дата | Обоснование |
|---------|------|-------------|
| Local-first | 2026-05-21 | ПДн не покидают устройство. Cloud = опция. |
| RED/GREEN pipeline | 2026-05-21 | Исходники (RED) chmod 600, обезличенные (GREEN) для обработки |
| 3 тира | 2026-05-21 | Private → Enhanced → Knowledge, progressive disclosure |
| state.json, не SQLite | 2026-05-21 | v0.x — простой JSON. v1.0 → SQLite при необходимости |
| keyrings.alt на Linux | 2026-05-21 | PlaintextKeyring для CI/CD, libsecret для продакшна |
| ~~Model fallback вычеркнут~~ → **Model fallback включён** | 2026-05-21 → 2026-06-01 | Ollama cloud модели (deepseek-v4-pro:cloud) дают 502 TLS timeout. Fallback на glm-5.1:cloud + qwen2.5:14b спасает |
| Brain Ingest v2.1: LLM Cross-Validation (7 фаз, zero tolerance) | 2026-06-05 | verify.py + llm_verify.py с 3 correction cycles. 32 новых notes, 514 medium-confidence на ревизии |
| Gateway drain fix: ExitTimeOut 20→120 сек | 2026-06-05 | launchd больше не убивает gateway при graceful drain |
| Allowlist моделей: 12 шт | 2026-06-05 | Убраны qwen2.5:7b/14b, добавлены deepseek-v4, gemma4, nemotron-3 |
| Friday-Ops = отдельный агент | 2026-05-25 | Мониторинг + self-heal + tunnel, клиент не имеет доступа |
| Docker Compose деплой | 2026-05-25 | Изоляция, воспроизводимость, лёгкое обновление |
| Zero Inbox = действия + аналитика | 2026-06-01 | Слияние подходов: А101 Zero Inbox (сортировка+черно) + The Jarvice (сводки+память). PII pipeline и self-validation — наше преимущество |
| Two-level routing | 2026-06-01 | Правила без LLM (40-60% писем) + LLM для остального. Экономия запросов и latency |
| Gemma 3:27b для medium задач | 2026-06-07 | Добавлена gemma3:27b-cloud в Ollama, используется для задач средней сложности |
| GTM AI-Assistants в The Brain | 2026-06-10 | Проект консолидации в The Brain: 3 новые заметки (стратегия, партнёр, MOC) |
| Cron persistence на клиенте | 2026-06-08 | Gateway inactive на клиентском VPS, cron jobs не добавлены — документировано в deploy playbook (chicken-egg через device pairing) |
| Jarvis model switch | 2026-06-05 | deepseek-v4-pro:cloud → glm-5.1:cloud (fallbacks: kimi-k2.6:cloud, deepseek-v4-flash:cloud) — по причине timeout deepseek |
| Brain Ingest дневной cron missing | 2026-06-12 | Cron job на 15:00 для brain ingest отсутствует в cron list — известная проблема |
| **Jarvis MEMORY.md compaction** | 2026-06-12 | Компактизирован с 23.4 KB → 19.8 KB, дубли паттернов удалены |
| **Friday Daily Digest Telegram delivery** | 2026-06-13 | consecutiveErrors=3, Telegram delivery failed — не восстановлено (14.06) |
| **Friday Weekly Docs Update Telegram delivery** | 2026-06-08 | Telegram delivery failed — не восстановлено (7d ago, 14.06) |
| **GLM-5.2 доступна** | 2026-06-13 | Zhipu выпустила GLM-5.2: 1M контекст, MIT лицензия — ждём в Ollama cloud |
| **HERA перепрофилирована** | 2026-06-14 | Бизнес-консультант, кризис-менеджер, startup launcher для МИТ-оф |
| **Config hash baseline restored** | 2026-06-14 | sha256 b0f29774b752e129 — baseline обновлён и совпадает с текущим |
| **Jarvis MEMORY.md overflow (повторное)** | 2026-06-17 | 22-23KB > 20KB порога — 5 срабатываний watchdog 16.06, требуется компактизация |
| **Ollama brew outdated** | 2026-06-17 | ollama, node, nss, pandoc, poppler в списке outdated brew (13 пакетов) |

---

## Версионирование

| Версия | Спринт | Ключевое |
|--------|--------|----------|
| v0.1.0 | Sprint 001 | CLI, config, doctor, setup |
| v0.1.1 | Sprint 002 | Exchange, PII, pipeline |
| v0.1.2 | Sprint 003 | Teams, security fixes |
| v0.2.0 | Sprint 004 | Providers, configure --quick, cron |
| v0.2.1 | Sprint 005 | Linux, CI, non-interactive, status |
| **v0.3.0** | **Sprint 006** | **Friday-Ops Agent** |
| **v0.3.1** | **Sprint 007** | **Multi-Client Deployment** |
| v0.4.0 | Sprint 008 | Enhanced Mode (cloud) |
| **v0.5.0** | **Sprint 009** | **Zero Inbox: умная сортировка + черновики** |
| v0.6.0 | Sprint 010 | Knowledge Mode (RAG) |
| v0.7.0 | Sprint 011 | Ops Dashboard |