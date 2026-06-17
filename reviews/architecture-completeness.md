# Architecture Council — Completeness Review

**Project:** The Jarvice v0.1.2 (Sprint 003)  
**Reviewer:** Friday (Completeness Lens)  
**Date:** 2026-05-21  
**Principle:** "What are we missing? What could break? Where are the blind spots?"

---

## 1. ✅ Approved Decisions (Secure, Complete)

### PII Path Validation (CRIT-01 fix)
`model_validator` with `resolve()` + `realpath()` blocks `/etc/passwd`, `../../../etc/shadow`, symlinks. Tested and passing. Correct defense-in-depth.

### Telegram HTML Delivery (WARN-02 fix)
`html.escape(text, quote=True)` covers all five HTML special chars. `chunk_html()` with 4096-char Telegram limit and paragraph-boundary splitting is complete — no message will be lost or truncated.

### Keyring Fallback Chain
Resolution order (keyring → env var → None) covers all deployment scenarios. `_ensure_prefix()` prevents namespace collisions. Logging at INFO level for env var usage provides audit trail.

### Ollama Prompt Hardening (WARN-01 fix)
System prompt in config is append-only in practice — operators can strengthen but not easily remove the core instruction. Passing as `system` parameter to Ollama gives it higher priority than user content.

### Doctor PII Check (WARN-04 fix)
`check_pii_permissions()` verifies RED dir `0o700` and mapping.json `0o600`. Correct threat model for single-user macOS.

---

## 2. 🔴 CRITICAL Issues (Must Fix Before Release)

### C-01: IC3 Token Has No Expiry Detection or Refresh

**Location:** `scrapers/teams/scraper.py` — `_get_token()`, `configure()`

The Teams IC3 token expires in 8-24 hours. There is:
- No `token_expiry` field in state.json or config
- No `doctor` check for token age
- No warning when token is approaching expiry
- No automated refresh mechanism
- No `the-jarvice auth refresh teams` command

When the token expires, the user gets a generic error with no recovery path. This will be the #1 support issue.

**Fix for v0.2.0:**
1. Store `teams_token_set_at` timestamp in state.json
2. Add `check_teams_token_age()` to doctor — warn at 20h, fail at 24h
3. Document token refresh procedure in README
4. Plan Graph API OAuth for v0.3.0

### C-02: Duplicate Function Definitions in keyring_utils.py

**Location:** `core/keyring_utils.py`

`get_credential()`, `save_credential()`, and `delete_credential()` are each defined twice — first without env var fallback, then with. Python uses the last definition, making the first versions dead code. This is confusing and error-prone.

**Fix:** Remove the first (simpler) definitions. Keep only the full versions with env var fallback. ~60 lines removed.

### C-03: No Credential Sanitization in Logging

**Location:** `cli/main.py`, `core/keyring_utils.py`, `scrapers/teams/scraper.py`

Multiple log statements include configuration data that could contain tokens or passwords:
- `configure()` logs full config on completion
- Teams scraper logs IC3 token metadata
- Error messages include service names that could be correlated with credential stores

While no passwords are logged directly, the pattern of logging config objects is risky — a future change could easily add a field containing secrets.

**Fix for v0.2.0:**
1. Add a `SanitizedConfig` repr that masks all `*_token`, `*_password`, `*_secret` fields
2. Replace direct `logger.info(config)` with `logger.info(sanitize_for_log(config))`
3. Add a test that verifies no credential appears in any log output

---

## 3. 🟡 WARNING Issues (Fix Soon)

### W-01: `_mask_sender_name()` Destroys Conversation Context

**Location:** `scrapers/teams/scraper.py` — `_mask_sender_name()`

Returns `[REDACTED]` for ALL senders. In a multi-person chat, messages become:
```
[REDACTED]: Давайте обсудим проект
[REDACTED]: Я за вариант 2
[REDACTED]: Согласен, давайте так
```

The PII pipeline cannot re-identify which `[REDACTED]` is which person. This makes Teams summaries useless for multi-person chats.

**Fix:** Use deterministic pseudonymization: `[SENDER_1]`, `[SENDER_2]`, etc. based on a per-run sender index. The PII Anonymizer can then map these consistently.

### W-02: `state.json` Has No File Locking or Atomic Writes

**Location:** `core/state.py` (inferred from usage)

The state file is read and rewritten as plain JSON. If two `the-jarvice run` processes overlap (cron + manual run), the file can be corrupted. No `fcntl` locking, no write-to-temp-then-rename.

**Fix for v0.2.0:**
1. Add `fcntl.flock()` around state.json writes
2. Write to `.tmp` file, then `os.rename()` (atomic on POSIX)
3. Add `--no-cron-overlap` flag that checks for lock file before starting

### W-03: `_generate_summary()` and `_deliver_telegram()` Are Business Logic in CLI

**Location:** `cli/main.py` — ~60 lines each

These functions contain core pipeline logic (Ollama call, Telegram API, HTML escaping) but live in the CLI module. They can't be tested independently or reused by other entry points.

**Fix for v0.2.0:** Extract to `core/summarizer.py` and `core/delivery.py`.

### W-04: `graph_api` Auth Mode Is Dead Code

**Location:** `scrapers/teams/scraper.py` — 5 methods with `if self.auth_mode == "graph_api": return <error stub>`

The validator accepts `graph_api` as valid, but every method immediately rejects it. This is ~30 lines of dead code that will be rewritten entirely when Graph API is actually implemented (needs OAuth2, different endpoints, different response parsing).

**Fix:** Remove `graph_api` from `auth_mode` validator. Raise `ValueError` if passed. Add back when Graph API is real.

### W-05: No Rate Limit Awareness in Teams Scraper

**Location:** `scrapers/teams/scraper.py` — `_request_with_retry()`, `scrape_chats()`

The scraper fetches up to 20 chats per run with no delay between requests. Microsoft's undocumented IC3 API may have aggressive rate limits. The current approach of "fetch everything and retry on 429" could trigger temporary IP bans.

**Fix for v0.2.0:** Add configurable `request_delay_ms` (default: 200ms) between API calls. Parse `Retry-After` headers.

### W-06: Prompt Injection Defense Is Shallow

**Location:** `cli/main.py` — `_generate_summary()`, `config.py` — `ModelsConfig.system_prompt`

Current defense: a single system prompt. This is insufficient for production:
1. No input truncation — a 10,000-char email body consumes the entire context window
2. No output PII check — the summary is sent directly to Telegram
3. System prompt is fully overridable from config.yaml

**Fix for v0.2.0:**
1. Add max input length per item (300 chars) enforced at prompt construction time
2. Add output PII scan before Telegram delivery (regex for email addresses, phone numbers)
3. Make system prompt append-only (core instructions can't be removed via config)

---

## 4. 🔵 INFO Items (Nice to Have)

### I-01: `autodetect_chat_id()` Uses urllib Instead of httpx/requests
The function imports `urllib.request` inline instead of using the project's HTTP dependencies. Works fine for a one-shot configure call, but inconsistent with the rest of the codebase.

### I-02: Doctor Has 11 Checks But No Grouping or Skip Mechanism
Adding checks is easy, but removing or conditionalizing them isn't. At 20+ checks, you'll want `--only=security` or `--skip=network` filtering.

### I-03: `_version_file` Read at Module Level
`_VERSION_FILE = Path(__file__).parent.parent / "VERSION"` is computed at import time. If the package is installed via pip, this path may not exist. Fallback to `importlib.metadata.version()` for installed packages.

### I-04: Teams Scraper Has No Pagination
`scrape_chats()` fetches up to `max_chats=20` but doesn't handle `@odata.nextLink` pagination from the IC3 API. If a user has more than 20 chats, only the first 20 are scraped.

### I-05: No Cross-Source PII Consistency
Exchange and Teams scrapers produce independent `ScrapeResult` objects. If the same person appears in both, they get different `[PERSON_N]` masks because each Anonymizer instance works independently. A shared `MappingManager` across scrapers would ensure consistency.

---

## 5. 🔍 Blind Spots

### BS-01: No Token/Secret Rotation Story
IC3 tokens expire. Exchange passwords change. Telegram bot tokens get revoked. There is no rotation mechanism, no expiry tracking, no proactive warning. The only signal is a failed scrape.

### BS-02: No Graceful Degradation When Ollama Is Unavailable
If Ollama is down, the pipeline saves RED data (raw PII) but never produces GREEN data (anonymized). On the next run, the pipeline skips already-scraped data (cursor-based) but the unsummarized data sits in RED forever. No fallback to a simpler summarizer (template-based, rule-based) or retry mechanism.

### BS-03: No Audit Trail for PII Access
The PII pipeline reads RED data and produces GREEN data, but there's no log of who accessed PII, when, or for what purpose. For corporate deployment, this is a compliance gap.

### BS-04: `_chat_message_to_dict()` Replaces Names Before Anonymizer
The Teams scraper replaces sender names with `[REDACTED]` in `_chat_message_to_dict()`, before the PII Anonymizer runs. The Anonymizer then sees `[REDACTED]` and can't assign consistent `[PERSON_N]` tokens. This breaks multi-person conversation context.

### BS-05: Telegram Bot Token in Config.yaml
The Telegram bot token is stored in `config.yaml` alongside non-sensitive settings. While `doctor` doesn't display it, the file is readable by any process with access to `~/.the-jarvice/`. The Exchange password is in keyring; the Telegram bot token should be too.

---

## 6. 🛡️ Credential Leakage Vectors

| Vector | Severity | Status |
|--------|----------|--------|
| IC3 Bearer token in keyring | HIGH | ✅ Stored in keyring, not in config.yaml |
| Exchange password in keyring | HIGH | ✅ Stored in keyring |
| Telegram bot token in config.yaml | MEDIUM | ⚠️ Not in keyring — should be |
| Config object logged with all fields | MEDIUM | ⚠️ No sanitization — could leak tokens |
| State.json contains cursor data only | LOW | ✅ No credentials |
| PII RED directory | HIGH | ✅ Protected: chmod 700, path traversal blocked |
| PII mapping.json | HIGH | ✅ Protected: chmod 600, path traversal blocked |
| Env vars JARVICE_*_PASSWORD | MEDIUM | ✅ Standard practice, but visible in /proc on Linux |
| Ollama responses cached in memory | LOW | ✅ Not persisted to disk |
| Error messages referencing services | LOW | ⚠️ Could be used for service enumeration |

---

## Verdict

**Overall: ✅ APPROVE with conditions**

Sprint 003 delivers real security fixes and a working Teams scraper. The PII path validation, HTML delivery, and keyring fallback are well-executed. The main gaps are:

1. **IC3 token lifecycle** (C-01) — #1 user pain point, needs expiry tracking
2. **Dead code in keyring_utils** (C-02) — confusing, easy fix
3. **Credential sanitization in logs** (C-03) — proactive defense
4. **`[REDACTED]` destroying conversation context** (W-01) — makes Teams summaries useless for multi-person chats
5. **Business logic in CLI** (W-03) — blocks reuse and testing

**Ship Sprint 003.** Fix C-01, C-02, C-03 in v0.2.0. Track W-01 through W-06 for v0.2.0–v0.3.0.

---

*Friday — Completeness Lens — Architecture Council — 2026-05-21*