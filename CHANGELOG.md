# Changelog

All notable changes to The Jarvice will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-07-09

### Added
- **Brain v3.1 Knowledge Graph Engine** — separate release ([brain-3.1](https://github.com/negatix-creator/brain-3.1))
- **PII Pipeline v2.1** — full anonymization: Natasha NER + regex + Yargy + verify-LLM
- **Re-identification Risk Gate** — 6-step check before data enters GREEN zone
- **Identity Store** — SQLite-based with encrypted values, OS Keychain key, alias history
- **Cloud Consolidator** — GLM-5.2 / DeepSeek V4 Pro on masked (GREEN) data only
- **GREEN Projector** — canon → green.sqlite with FTS5 + sqlite-vec + capsules + MOC
- **Policy Engine** — realm × sensitivity × principal access control
- **Cloud Egress Layer** — context minimization + session-scoped aliasing
- **Deletion Saga** — crypto-shredding + cascade deletion from all stores
- **OS Isolation** — RED/GREEN zones separated by OS users and file permissions
- **Full architecture specification** — see `docs/ARCHITECTURE-FULL.md` and `docs/pii-pipeline-architecture.md`
- **8 agents ecosystem** — Friday (orchestrator), Jarvis (strategic copilot), Ultron (DevOps), Dev (code), Sophie (product), ArGO (health), Edith (finance), Hera (strategy)
- **23 active cron jobs** — summaries, scraping, brain ingest, health checks, backup

### Changed
- **Brain v3.0 → v3.1** — consolidator moved from RED (local) to GREEN (cloud): cloud models never see PII
- **NER Worker** — now a separate local-only component (extracts entities + builds identity_map)
- **mapping.json → identity_map.sqlite** — transactional, encrypted, with alias history
- **Jarvice Sell Bot** — fixed SyntaxError in survey handler

### Fixed
- **Ultron cron jobs** — delivery now routes through Ultron's bot (was sending through Friday's bot)
- **Brain Stats cron** — fixed model path `ollama/kimi-k2.6:cloud` → `ollama-cloud/kimi-k2.6`
- **Ultron Daily Digest** — fixed delivery accountId to route correctly

## [0.5.4] - 2026-07-03

### Changed
- Updated ROADMAP with Brain v3.1 pipeline progress

## [0.5.1] - 2026-06-26

### Changed
- SEO landing page improvements
- ROADMAP update
- CHANGELOG fix

## [0.5.0] - 2026-06-20

### Added
- PII Pipeline — full anonymization with RED/GREEN zones
- Brain Ingest v2.1 — knowledge graph from agent memories
- Commercial License

## [0.4.0] - 2026-06-10

### Added
- One-command deploy scripts (macOS + Linux)

## [0.3.1] - 2026-06-05

### Changed
- Version bump

## [0.3.0] - 2026-06-05

### Added
- Setup.sh — fully in Russian
- Humor improvements
- Critical bug fixes

## [0.2.0] - 2026-05-21

### Added
- **configure --quick**: 3-field setup (email + password + bot token), auto-detect Exchange server & chat_id
- **enable/disable commands**: system crontab scheduling with `# the-jarvice-managed` marker
- **run --cron**: suppress Rich output for scheduled runs
- **run --label**: tag scheduled runs (morning/evening/weekly)
- **run --dry-run**: test pipeline without sending to Telegram (with preview)
- **check_cron()**: 12th doctor diagnostic for cron status
- **_send_error_notification()**: Telegram notification on Ollama failures in cron mode
- **setup.sh**: idempotent installer with --quick and --check modes
- **README.md**: Quick Start, Commands, Security, Architecture, Example Summary
- **.gitignore**: Python + macOS + PII exclusions
- **LICENSE**: MIT
- **CONTRIBUTING.md**: dev setup, tests, PR process, architecture
- **Provider abstraction**: OllamaProvider, OpenAIProvider, AnthropicProvider with fallback chains
- **Context scrubber**: standard (remove title+org) / strict (remove budgets, dates, times)
- **Audit log**: JSON lines log of all PII operations
- **Log sanitization**: sanitize_for_log(), mask_value(), SENSITIVE_FIELDS
- **Token age tracking**: set_token_timestamp(), get_token_age_hours() in TeamsScraper
- **Rate limiting**: request_delay_ms (default 200ms) between Teams API requests
- **Sender pseudonymization**: deterministic [SENDER_N] via _SenderIndex

### Fixed
- **cron_mode bug**: pass cron_mode as explicit parameter to _generate_summary()
- **Exchange "Continue anyway?" default**: changed to False (safer default)
- **Version chaos**: unified version source (VERSION file → importlib.metadata)
- **DIM variable**: missing color code in setup.sh

### Changed
- **Doctor checks**: 11 → 12 (added check_cron)
- **Version**: 0.1.3 → 0.2.0

## [0.1.2] - 2026-05-21

### Added
- **Teams Scraper**: IC3 token auth + Graph API stub (httpx, no playwright)
- **PII Path Validation (CRIT-01)**: PIIConfig rejects paths outside ~/.the-jarvice/
- **Telegram HTML Delivery (WARN-02)**: parse_mode=HTML, html.escape(), chunk_html()
- **Ollama Prompt Hardening (WARN-01)**: system_prompt in ModelsConfig
- **Keyring Fallback (P1)**: env var fallback (JARVICE_*_PASSWORD)
- **Doctor PII Check (WARN-04)**: check_pii_permissions()
- **detect_exchange_server()**: auto-detect from email domain
- **autodetect_chat_id()**: auto-detect via Telegram getUpdates
- **TeamsConfig**: max_messages, include_transcripts fields
- **httpx** dependency (replaces playwright)
- **teams-graph** optional extra

### Fixed
- PIIConfig path traversal blocked (CRIT-01)
- Telegram delivery uses HTML instead of Markdown
- Ollama calls include anti-injection system prompt
- YAML parse error returns defaults instead of crash
- logger added to cli/main.py

### Tests
- 44 new tests (Sprint 003)
- Total: 231 tests passing

## [0.1.1] - 2026-05-21

### Added

- **Exchange Scraper** (`scrapers/exchange/scraper.py`)
  - Connects to on-premise Exchange (EWS) via exchangelib with stealth User-Agent
  - Credential resolution: keyring → macOS Keychain → legacy service name
  - Email scraping: inbox filter by date range, cursor-based incremental via state.json
  - Calendar scraping: upcoming events with attendees, organizer, free/busy status
  - Force-masks sender/recipient PII even if NER misses it
  - ScrapeResult output with markdown/JSON export

- **PII Anonymizer** (`scrapers/pii/anonymizer.py`)
  - Regex-based PII classifier: Russian phones, emails, INN, SNILS
  - MappingManager: consistent [PERSON_1] style masks across all uses
  - RED (originals, chmod 600) / GREEN (anonymized) pipeline
  - Deanonymizer: mask → real value replacement for Telegram delivery
  - Force-masking: sender/recipient names and emails always masked

- **Pipeline: `run` command** now executes end-to-end:
  1. Scrape (Exchange + Teams) → ScrapeResult
  2. Anonymize (RED → GREEN) via PII pipeline
  3. Summarize via Ollama qwen3:14b (local)
  4. Deliver to Telegram via Bot API
  5. Save outputs to ~/.the-jarvice/memory/

- **Summary Generator** (`_generate_summary` in CLI)
  - Sends anonymized data to local Ollama
  - Russian-language prompt, markdown output
  - Temperature 0.3, max 2048 tokens

- **Telegram Delivery** (`_deliver_telegram` in CLI)
  - Bot token from keyring
  - 4096-char chunking for long messages
  - Markdown parse mode

### Changed

- `pyproject.toml`: added `[exchange]`, `[pii]`, `[telegram]` optional dependency groups
- CLI `run` command: full pipeline instead of stub
- `doctor` command: Exchange scraper now importable and testable

## [0.1.0] - 2025-05-21

### Added

- **CLI** (`the-jarvice`) with Typer + Rich output
  - `version` — Show version information
  - `configure` — Interactive configuration wizard with live validation
    - `--skip-exchange`, `--skip-teams`, `--skip-model`, `--skip-telegram` flags
    - `--reauth SERVICE` to re-configure a specific service
  - `run` — Execute the data pipeline (scrape → anonymize → summarize → deliver)
    - `--once` flag (default: True)
    - `--verbose` / `-v` for step-by-step progress
    - `--dry-run` to run without sending to Telegram
  - `doctor` — System health diagnostics
    - `--verbose` / `-v` for detailed output
    - `--json` for machine-readable output
    - `--fix` to attempt automatic fixes
    - Checks: Python, Ollama, model, keyring, config, Exchange, Teams, Telegram, disk space, OpenClaw
    - Exit code 0 (all pass) or 1 (problems found)
  - `uninstall` — Remove The Jarvice from the machine
    - `--keep-config` to preserve config.yaml and data
    - `--force` to skip confirmation prompt

- **Configuration** (`~/.the-jarvice/config.yaml`)
  - Pydantic v2 validation with `JarviceConfig` model
  - Sections: `exchange`, `teams`, `telegram`, `pii`, `models`, `schedule`, `logging`
  - `load_config()` / `save_config()` for YAML I/O
  - `generate_openclaw_config()` — generates `openclaw.json` from template + config

- **State Management** (`~/.the-jarvice/state.json`)
  - `StateManager` for cursor tracking between scraper runs
  - Per-scraper `last_scrape` timestamps (ISO 8601)
  - Global `last_run` timestamp
  - Error count tracking with `increment_error_count()` / `reset_error_count()`
  - Arbitrary metadata storage per scraper

- **Scraper Architecture**
  - `BaseScraper` ABC with `configure()`, `test_connection()`, `scrape()`, `get_status()`
  - `ScrapeResult` dataclass with `source`, `timestamp`, `items`, `count`, `errors`, `metadata`
  - Export methods: `to_markdown()`, `to_json()`

- **Diagnostic Module** (`doctor.py`)
  - 10 individual check functions: Python, Ollama, model, keyring, config, Exchange, Teams, Telegram, disk, OpenClaw
  - `CheckResult` dataclass with `ok`, `name`, `message`, `details`
  - `run_all_checks()` — run all checks, collect results
  - `format_results_table()` — human-readable output
  - `format_results_json()` — machine-readable JSON output

- **Setup** (`setup/setup.sh`)
  - Idempotent installation script (safe to re-run)
  - Checks: OS (macOS), Homebrew, Python 3.10+, Node.js 20+, Ollama, disk space (≥12 GB)
  - Creates virtual environment at `~/.the-jarvice/venv/`
  - Installs Python dependencies from `pyproject.toml`
  - Downloads Ollama model (`qwen3:14b`) if missing
  - Creates directory structure with secure PII directories (chmod 700)
  - Copies config template or generates default
  - Prints welcome message with next steps

- **Uninstall** (`setup/uninstall.sh`)
  - Removes keyring entries, cron jobs, data directory, OpenClaw config
  - `--keep-config` preserves config.yaml and data
  - `--force` skips confirmation
  - Fallback to macOS `security` command if Python keyring unavailable

- **Keyring Utilities** (`keyring_utils.py`)
  - `test_keyring()` — verify keyring read/write works
  - `get_credential()` — retrieve credentials from macOS Keychain
  - Credential services: `the-jarvice.exchange`, `the-jarvice.teams`, `the-jarvice.telegram-bot`, `the-jarvice.telegram`

- **OpenClaw Integration**
  - `openclaw_template.json` with `{{PLACEHOLDER}}` substitution
  - Auto-generated from `config.yaml` during `configure`

### Dependencies

- `typer[all]>=0.9.0` — CLI framework
- `pydantic>=2.0` — Config validation
- `keyring>=24.0` — Credential storage
- `rich>=13.0` — Terminal output
- `pyyaml>=6.0` — YAML config parsing
- `requests>=2.31` — HTTP requests (Telegram API, Ollama)
- Optional: `exchangelib>=5.0` (Exchange), `playwright>=1.40` (Teams)

### Known Limitations

- Playwright (~300MB) is a dependency for Teams token refresh — documented as known limitation
- `state.json` for cursor tracking (not SQLite) — acceptable for single-user v0.1.0
- Teams IC3 tokens expire ~24 hours — requires periodic `--reauth`
- Exchange auth: supports Basic Auth and NTLM; OAuth (365) deferred to v0.3.0
- macOS 13+ is the primary target for v0.1.0
## [0.3.0] - 2026-06-17

### Changed
- **BREAKING**: setup.sh completely rewritten as full system installer
- Installs OpenClaw + The Jarvice + Ollama + models + agent config (13 steps)
- Default model: `glm-5.1:cloud` (no local GPU needed)
- Default embeddings: `nomic-embed-text` (for memory search)
- Interactive credential prompts: Telegram token, Exchange, Ollama signin
- Generates `config.yaml` with cloud models preconfigured
- Creates workspace files: AGENTS.md, SOUL.md, MEMORY.md
- Starts OpenClaw gateway automatically
- Health check in summary shows what's not configured
- Disk requirement lowered to 3GB (cloud models need ~300MB locally)

### Fixed
- `ollama cloud login` → `ollama signin` (correct command)
- Removed unnecessary cloud key prompt (public models work without auth)
- `openclaw pair` → `openclaw channels add` (correct CLI)
- Exchange password: hidden input (`read -s`)
- Keychain: `-U` flag for update-or-create
- `pip install -e` → `pip install .` (safer, no git dependency)
- `set -euo pipefail` → `set -uo pipefail` (avoids crashes on non-critical failures)
- Venv recreation fallback if broken
- `cd "$HOME"` after git operations
- Ollama start via macOS app with daemon fallback
- Config.yaml now generated with `glm-5.1:cloud` (was `qwen3:14b`)

### Added
- ModelsConfig.embeddings field
- Gateway start step
- Config.yaml generation during setup
- Interactive Telegram/Exchange/OpenClaw credential setup
- .zshrc/.bashrc PATH configuration

## [0.5.0] - 2026-06-20

### Added
- **PII Pipeline**: 7-script anonymization pipeline (Teams/Exchange → GREEN/RED)
- **Brain Ingest v2.1**: 7-phase validation, 937→1042 atoms, 16 entity types, 12 link types
- **Commercial License**: MIT → Proprietary (Production/Hosting/Integration/Evaluation)
- **Create-bot skill v2**: Part 12 — Memory Management & Session Health
- **Deploy scripts**: macOS + Linux one-command deploy (scripts/deploy-openclaw-macos.sh, scripts/deploy-openclaw-linux.sh)
- **INFRASTRUCTURE_REGISTRY.md**: Unified registry of all machines, services, credentials
- **6 agents**: Jarvis, Friday, Edith, HERA, Ultron, Jeeves
- **27 cron jobs**: summaries, scraping, brain ingest, health checks, backup, security watchdog
- **CI**: GitHub Actions (macOS + Ubuntu, Python 3.10-3.13)

### Changed
- Brain Ingest: DeepSeek V4 Pro extract + GLM 5.1 validate + qwen3:14b NER
- Pipeline: 707s → 198s (−72%)
- Multi-client deployment: VPS, macOS, Linux — tested in production (mac Мурада, 19.06)

## [0.4.0] - 2026-06-17

### Added
- **One-command deploy**: macOS + Linux scripts (scp + run = full install)
- **Setup.sh rewrite**: 13-step full system installer with humor
- **Cloud-only models**: glm-5.2:cloud primary, glm-5.1:cloud fallback
- **Ollama SSH key**: cloud auth via ollama.com signin

### Fixed
- `ollama cloud login` → `ollama signin`
- `openclaw pair` → `openclaw channels add`
- `pip install -e` → `pip install .`

## [0.5.1] - 2026-06-23

### Changed
- **Landing SEO**: Open Graph, Twitter Card, Schema.org, canonical URL, keywords, robots
- **Landing CTA**: Telegram link updated to @Mit_sell_ai_bot, PII disclaimer added
- **ROADMAP**: Updated with deploy scripts, create-bot v2 session health, backup fix, memory_search timeout

### Added
- **robots.txt + sitemap.xml** for landing SEO

### Fixed
- **Backup script**: exit 23 (sqlite-wal race condition) handled gracefully
- **memory_search timeout**: QMD embedding provider timeout 15s documented, BM25 fallback works
