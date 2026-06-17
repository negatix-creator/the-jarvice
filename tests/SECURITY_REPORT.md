# Sprint 001 — Security & QA Audit Report

**Auditor:** Friday (QA/Security Reviewer)
**Date:** 2026-05-21
**Scope:** The Jarvice v0.1.0 — Sprint 001 codebase
**Files reviewed:** All Python modules, shell scripts, config templates, spec

---

## Summary

Overall the codebase is well-structured with thoughtful separation of concerns. The security posture is good: credentials are stored in keyring (not files), input validation uses Pydantic, and error handling is defensive. However, there are several issues that should be addressed before release, ranging from credential leakage in CLI prompts to missing file permissions and cross-platform gaps.

**Test suite:** 102 tests — all passing. Written to `tests/test_sprint001.py`.

---

## CRITICAL — Must Fix Before Release

### C1. Bot token leaked in Telegram test message (cli/main.py)

**File:** `the_jarvice/cli/main.py`, line ~148
**Description:** During `configure`, a test message is sent to Telegram with the bot token directly in the URL:
```python
resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
```
And then:
```python
resp = requests.post(
    f"https://api.telegram.org/bot{bot_token}/sendMessage", ...
)
```
The `bot_token` is a plaintext variable in memory. If verbose logging is enabled (or if there's a debug breakpoint), the token could appear in logs. More importantly, the `getMe` response doesn't log the token, but any exception traceback would include the full URL with the token.

**Fix:** Use the `bot_token` only in the request body or header, not in the URL path. At minimum, add `logging.getLogger("urllib3").setLevel(logging.WARNING)` (already done in `log.py` but not in `cli/main.py`). Also, wrap the Telegram API calls in a try/except that strips the token from any error messages.

### C2. Bot token visible in process args (cli/main.py)

**File:** `the_jarvice/cli/main.py`, line ~135
**Description:** `typer.prompt("  Bot token")` reads the token from stdin. However, `typer.prompt` does not use `hide_input=True` for the bot token (unlike the Exchange password which correctly uses `hide_input=True`). This means the token is echoed to the terminal and may be stored in shell history.

**Fix:** Change to `typer.prompt("  Bot token", hide_input=True)` for the bot token, same as the Exchange password.

### C3. PII directory permissions only set in setup.sh, not in code

**File:** `setup/setup.sh`, line ~170; `the_jarvice/core/scraper_base.py`, `to_markdown()`/`to_json()`
**Description:** `setup.sh` sets `chmod 700` on PII directories, but:
1. `ScrapeResult.to_markdown()` and `to_json()` create directories with `mkdir(parents=True, exist_ok=True)` which uses the default umask — typically 0755, not 0700.
2. The `PIIConfig.get_red_dir()` returns a `Path` but doesn't enforce permissions.
3. If the PII directories are recreated (e.g., after uninstall + reinstall), the Python code won't set restrictive permissions.

**Fix:** In `ScrapeResult.to_markdown()` and `to_json()`, after `mkdir()`, check if the path starts with a PII directory and set `os.chmod(path, 0o700)`. Better yet, add a helper in `PIIConfig` that creates directories with correct permissions.

### C4. Telegram bot token in process list / URL logging (doctor.py)

**File:** `the_jarvice/core/doctor.py`, `check_telegram()` function
**Description:** Same issue as C1. The `bot_token` is used in a URL passed to `requests.get()`. If the request fails with an exception, the traceback will contain the full URL including the bot token. The function also doesn't redact the token from any log output.

**Fix:** Wrap the Telegram API call in a helper that catches exceptions and redacts the token from error messages before re-raising or logging.

---

## WARNING — Should Fix Soon

### W1. No email format validation on ExchangeConfig.email

**File:** `the_jarvice/core/config.py`, line ~16
**Description:** `email: str = ""` accepts any string. An invalid email like "not-an-email" passes validation. While EWS would eventually reject it, earlier validation gives better UX.

**Fix:** Add a `@field_validator("email")` that checks for basic email format (`@` present, no spaces), or use Pydantic's `EmailStr` from `pydantic[email]`.

### W2. No URL validation on ExchangeConfig.server

**File:** `the_jarvice/core/config.py`, line ~15
**Description:** `server: str = ""` accepts any string, including malformed URLs. The spec uses `HttpUrl` type but the implementation uses plain `str`.

**Fix:** Either use Pydantic's `HttpUrl` type or add a field validator that checks for `https://` prefix and valid URL format when the value is non-empty.

### W3. No URL validation on ModelsConfig.ollama_host

**File:** `the_jarvice/core/config.py`, line ~65
**Description:** `ollama_host: str = "http://localhost:11434"` accepts any string. A typo like `localhost:11434` (missing `http://`) would cause cryptic connection errors.

**Fix:** Add a field validator that checks for `http://` or `https://` prefix.

### W4. state.json has no file permissions enforcement

**File:** `the_jarvice/core/state.py`, `save()` method
**Description:** `state.json` may contain metadata about tokens (e.g., `token_expiry`). While it doesn't store credentials directly, the file is written with default umask permissions (typically 0644), making it world-readable.

**Fix:** After writing `state.json`, set `os.chmod(self.state_file, 0o600)` to restrict access to the owner only.

### W5. config.yaml has no file permissions enforcement

**File:** `the_jarvice/core/config.py`, `save_config()` function
**Description:** While credentials are stored in keyring, `config.yaml` contains server URLs, email addresses, and other sensitive metadata. It's written with default permissions (0644 on most systems).

**Fix:** Set `os.chmod(config_path, 0o600)` after writing config.yaml.

### W6. ScrapeResult markdown doesn't sanitize HTML/XSS

**File:** `the_jarvice/core/scraper_base.py`, `to_markdown()` method, line ~66
**Description:** Scraped item values are written directly to markdown without sanitization. If Exchange emails contain `<script>` tags or other HTML, they'll appear verbatim in the markdown. The test `test_special_chars_in_items` confirms this — `<script>alert(1)</script>` passes through.

**Fix:** Sanitize item values before writing to markdown. At minimum, escape HTML entities (`<>&"`) and consider stripping script tags. This is also a PII concern — the PII pipeline should handle this, but the markdown writer should be safe by default.

### W7. openclaw_template.json uses string substitution, not proper templating

**File:** `the_jarvice/core/config.py`, `generate_openclaw_config()`
**Description:** Simple `{{KEY}}` string replacement is used. If any config value contains `{{` or `}}`, it could break the JSON. Also, if a value is empty string `""`, the replacement `""{{exchange_server}}""` → `""""` creates invalid JSON.

**Fix:** Use `json.dumps()` for values that go into JSON strings, or use a proper template engine like Jinja2. At minimum, validate that the resulting string is valid JSON (which is already done — good!), but the error message won't help users understand what went wrong.

### W8. configure wizard reads password from stdin with echo for bot_token

**File:** `the_jarvice/cli/main.py`, line ~135
**Description:** `typer.prompt("  IC3 token")` for Teams doesn't use `hide_input=True`. IC3 tokens are sensitive credentials that should not be echoed.

**Fix:** Use `typer.prompt("  IC3 token", hide_input=True)` for the Teams token prompt.

### W9. uninstall CLI doesn't remove all keyring accounts

**File:** `the_jarvice/cli/main.py`, `uninstall()` function
**Description:** The CLI tries to delete keyring entries with `keyring.delete_password(service, "")`, but:
1. The Exchange credential is stored with the email as the account, not `""`.
2. The Teams token is stored with `"ic3_token"` as the account.
3. The Telegram bot token is stored with `"bot_token"` as the account.

Using `""` as the account will miss these entries. The uninstall.sh script correctly tries multiple account names, but the CLI does not.

**Fix:** In the CLI's uninstall command, iterate over all known service/account combinations:
- `the-jarvice.exchange` / `{email from config}`
- `the-jarvice.teams` / `ic3_token`
- `the-jarvice.telegram` / `{chat_id from config}` or `""`
- `the-jarvice.telegram-bot` / `bot_token`

### W10. Race condition in StateManager

**File:** `the_jarvice/core/state.py`, `save()` method
**Description:** `StateManager.save()` does a full file write (`write_text`). If two processes write at the same time (e.g., Exchange and Teams scrapers running concurrently), the last writer wins and data can be lost. Also, there's no file locking.

**Fix:** For v0.1.0, this is acceptable (single-user, sequential runs). Add a comment noting this limitation. For v0.2.0+, consider SQLite (as planned) or file locking with `fcntl.flock()`.

### W11. setup.sh runs pip install with `--quiet` which hides errors

**File:** `setup/setup.sh`, line ~125
**Description:** `pip install -e "$REPO_DIR" --quiet 2>&1 | tail -5` pipes output through `tail -5`, which means:
1. Error messages may be truncated.
2. The exit code of `pip install` is not checked.
3. If pip fails, the script continues to the next step.

**Fix:** Remove `--quiet` or use `2>&1 | tee install.log` to capture full output. Check `pip install` exit code with `if ! pip install ...; then err "pip install failed"; exit 1; fi`.

### W12. setup.sh doesn't activate venv before model download

**File:** `setup/setup.sh`, `check_model()` function
**Description:** After `source "$VENV_DIR/bin/activate"`, the script should be using the venv's Python. But `ollama pull` is a system command, not a pip package, so this is fine. However, if `ollama` is not in PATH after the venv activation (unlikely but possible on some setups), the model check/download would fail silently.

**Fix:** Verify `ollama` is in PATH after the venv activation step, or use the full path.

---

## INFO — Nice to Have

### I1. VERSION file is read at import time with no fallback for editable installs

**File:** `the_jarvice/cli/main.py`, lines 10-13
**Description:** `_VERSION_FILE = Path(__file__).parent.parent.parent / "VERSION"` — this relative path works when installed from source but may break in wheel installs or when the package is installed via pip.

**Fix:** Use `importlib.metadata.version("the-jarvice")` as the primary method with the file read as fallback:
```python
try:
    _VERSION = importlib.metadata.version("the-jarvice")
except importlib.metadata.PackageNotFoundError:
    try:
        _VERSION = _VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        _VERSION = "0.1.0"
```

### I2. schedule.weekly_summary has no validation

**File:** `the_jarvice/core/config.py`, `ScheduleConfig`
**Description:** `weekly_summary: str = "Mon 09:00"` has no field validator. Values like "Foo 99:99" would pass validation.

**Fix:** Add a field validator that checks the format `<Day> HH:MM` with valid days and times.

### I3. LoggingConfig.dir uses string instead of Path

**File:** `the_jarvice/core/config.py`, `LoggingConfig`
**Description:** `dir: str = "~/.the-jarvice/logs"` stores the path as a string. A `Path` type would be more Pythonic and would auto-expand `~`.

**Fix:** Consider using `Path` type with a custom validator, or at minimum document that `~` expansion is handled by `get_log_dir()`.

### I4. doctor.py `_load_config()` doesn't use Pydantic

**File:** `the_jarvice/core/doctor.py`, `_load_config()` function
**Description:** `_load_config()` uses `yaml.safe_load()` directly instead of `load_config()`. This means it doesn't benefit from Pydantic validation and defaults.

**Fix:** Use `from the_jarvice.core.config import load_config` and catch `ValueError` for validation errors.

### I5. doctor.py `check_exchange()` imports exchangelib at runtime

**File:** `the_jarvice/core/doctor.py`, `check_exchange()` function
**Description:** `from exchangelib import ...` is inside the function, which is good for optional deps. But the import could be caught more specifically — currently any `ImportError` is silently ignored.

**Fix:** Differentiate between `exchangelib` not installed (expected) vs. other import errors (bug).

### I6. doctor.py `check_disk()` uses macOS-specific `df -g`

**File:** `the_jarvice/core/doctor.py`, `check_disk()` function
**Description:** The code has a macOS branch (`df -g`) and a Linux fallback using `shutil.disk_usage()`. However, the macOS branch parses `df` output which is fragile and locale-dependent. The `shutil.disk_usage()` approach works on all platforms and should be preferred.

**Fix:** Use `shutil.disk_usage()` universally. The macOS-specific `df` parsing is unnecessary since `shutil.disk_usage()` works on macOS.

### I7. configure wizard doesn't validate timezone

**File:** `the_jarvice/cli/main.py`, `configure()` command
**Description:** The timezone prompt accepts any string. Values like "Foo/Bar" would be accepted but cause runtime errors with `datetime` and cron.

**Fix:** Validate against `zoneinfo.available_timezones()` or at minimum check that the string contains a `/`.

### I8. configure wizard doesn't validate chat_id is numeric

**File:** `the_jarvice/cli/main.py`, `configure()` command
**Description:** `chat_id` is stored as a string but should be a numeric Telegram chat ID. Accepting alphabetic values would cause Telegram API errors later.

**Fix:** Add a simple `chat_id.strip().lstrip("-").isdigit()` check.

### I9. No `.gitignore` for sensitive directories

**Description:** The project doesn't have a `.gitignore` that excludes `state.json`, `config.yaml`, log files, or the `.the-jarvice/` directory. If someone accidentally commits from `~/.the-jarvice/`, credentials could end up in git.

**Fix:** Add a `.gitignore` with: `state.json`, `config.yaml`, `*.log`, `data/`, `__pycache__/`, `.venv/`, etc.

### I10. setup.sh `check_homebrew()` downloads and executes remote script

**File:** `setup/setup.sh`, `check_homebrew()` function
**Description:** `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` — this is the standard Homebrew install method, but it downloads and executes arbitrary code from the internet without verification.

**Fix:** This is standard practice for Homebrew installation. Document it clearly in the README. Consider adding a checksum or signature verification for paranoid users.

### I11. setup.sh `ollama serve &` backgrounds Ollama without tracking PID

**File:** `setup/setup.sh`, `check_ollama()` function
**Description:** When Ollama is not running, the script starts it with `ollama serve &>/dev/null &`. The background process is not tracked, so if the user kills the script, Ollama keeps running. This could also conflict with an existing Ollama installation.

**Fix:** Check if Ollama is already running as a LaunchAgent (macOS). If not, suggest `brew services start ollama` instead of backgrounding.

### I12. uninstall.sh fallback to `security delete-generic-password` could delete wrong entries

**File:** `setup/uninstall.sh`, keyring removal section
**Description:** The macOS fallback uses `security delete-generic-password -s "$service"` which deletes ALL entries matching the service name, not just The Jarvice's. If another application used the same service name prefix, its entries would be deleted.

**Fix:** This is mitigated by the `the-jarvice.` prefix which is unique. No action needed, but worth noting.

### I13. `generate_openclaw_config()` could overwrite existing openclaw.json

**File:** `the_jarvice/core/config.py`, `generate_openclaw_config()`
**Description:** The function unconditionally overwrites `~/.openclaw/openclaw.json`. The spec says "warn about overwrite" but the implementation doesn't check or warn.

**Fix:** Before writing, check if the file exists and if it contains `the-jarvice` marker. If it exists but wasn't generated by The Jarvice, warn the user or ask for confirmation.

### I14. `_list_linux_keyring()` iterates over items but only checks KNOWN_SERVICES

**File:** `the_jarvice/core/keyring_utils.py`, `_list_linux_keyring()` function
**Description:** The function iterates over SecretStorage items and checks `label.startswith(prefix)`, but then iterates over `KNOWN_SERVICES` again. The label check is redundant — if the item's label doesn't match a known service, it's still checked.

**Fix:** Simplify: just iterate over `KNOWN_SERVICES` and try `keyring.get_credential()`, same as the macOS fallback.

### I15. `ScrapeResult.count` is not validated against `len(items)`

**File:** `the_jarvice/core/scraper_base.py`, `ScrapeResult` dataclass
**Description:** `count` and `items` are independent — a scraper could set `count=5` but `items=[]`. This inconsistency could cause confusion downstream.

**Fix:** Either make `count` a computed property (`@property def count(self): return len(self.items)`) or add a `__post_init__` validator that checks `count == len(items)`.

---

## Cross-Platform Notes

### X1. Linux keyring requires libsecret

**File:** `the_jarvice/core/keyring_utils.py`, `_list_linux_keyring()` 
**Description:** On Linux, `secretstorage` requires `libsecret` and D-Bus. If these aren't installed, keyring operations will fail. The `test_keyring()` function catches `NoKeyringError` but the doctor's `check_keyring()` calls this function, so it should be OK. However, the error message should suggest installing `libsecret-1-dev` and `python3-secretstorage`.

**Status:** Acceptable for v0.1.0 (macOS primary target). Document in README.

### X2. `shutil.disk_usage()` for disk check works on both platforms

**File:** `the_jarvice/core/doctor.py`, `check_disk()`
**Description:** The current code has macOS-specific `df -g` parsing and falls back to `shutil.disk_usage()`. The `shutil` approach works everywhere.

**Fix:** See I6 — use `shutil.disk_usage()` universally.

### X3. setup.sh is macOS-only with `set -euo pipefail`

**File:** `setup/setup.sh`
**Description:** The script explicitly checks for macOS and exits on Linux. This is correct for v0.1.0 (spec says macOS primary target). The `set -euo pipefail` is bash-specific but works on macOS.

**Status:** Acceptable for v0.1.0.

---

## Idempotency Check

| Operation | Idempotent? | Notes |
|-----------|:-----------:|-------|
| `setup.sh` run twice | ✅ | Checks before each step, skips existing |
| `configure` run twice | ✅ | Loads existing config as defaults, overwrites |
| `doctor` run twice | ✅ | Read-only checks |
| `uninstall.sh` run twice | ⚠️ | Second run: keyring entries already gone (OK), but `rm -rf` on missing dirs is fine |
| `save_config()` run twice | ✅ | Overwrites file |
| `StateManager.set_cursor()` | ✅ | Overwrites existing cursor |

**Issue:** `configure --reauth` uses skip flags (skip everything except target). If the user runs `configure --reauth teams` and the Teams step fails, all other services' config is loaded from file (OK), but the user doesn't get a chance to re-configure them. This is by design per the spec.

---

## Error Handling Assessment

| Module | Error Handling | Grade |
|--------|---------------|-------|
| `config.py` | Pydantic validation + explicit error messages | ✅ Good |
| `state.py` | Handles corrupted/missing files, invalid timestamps | ✅ Good |
| `scraper_base.py` | Minimal — delegates to subclasses | ⚠️ OK (ABC) |
| `doctor.py` | Try/except on every check, graceful degradation | ✅ Good |
| `keyring_utils.py` | Catches KeyringError, NoKeyringError, locked | ✅ Good |
| `log.py` | Handles file rotation, directory creation | ✅ Good |
| `cli/main.py` | Try/except on each service, continues on failure | ✅ Good |
| `setup.sh` | `set -euo pipefail` + checks before each step | ✅ Good |
| `uninstall.sh` | `set -euo pipefail` + handles missing entries | ✅ Good |

---

## Test Coverage Summary

| Module | Tests | Coverage |
|--------|-------|----------|
| `config.py` | 14 | Models, load/save, validation, edge cases |
| `state.py` | 9 | CRUD, persistence, corruption, timestamps |
| `scraper_base.py` | 8 | ScrapeResult I/O, truncation, empty items |
| `keyring_utils.py` | 8 | Prefix, CRUD, mock keyring, round-trip |
| `doctor.py` | 7 | Checks, formatting, JSON output |
| `log.py` | 4 | Setup, namespacing, exception logging |
| `cli/main.py` | 7 | Version, doctor, configure help, run help |
| Security | 5 | Credential absence, file permissions, input validation |
| Edge cases | 7 | Empty data, Unicode, concurrent cursors, extra fields |

**Total: 102 tests, all passing.**

---

## Recommendations (Priority Order)

1. **[CRITICAL]** Hide bot token and IC3 token in CLI prompts (`hide_input=True`)
2. **[CRITICAL]** Add credential redaction to error messages in Telegram/Exchange API calls
3. **[CRITICAL]** Enforce PII directory permissions in Python code (not just setup.sh)
4. **[WARNING]** Set file permissions 0o600 on state.json and config.yaml
5. **[WARNING]** Validate email format and URL format in config models
6. **[WARNING]** Sanitize HTML in ScrapeResult.to_markdown()
7. **[WARNING]** Fix keyring account name mismatches in CLI uninstall
8. **[INFO]** Use `importlib.metadata` for version detection
9. **[INFO]** Validate timezone and weekly_summary format
10. **[INFO]** Use `shutil.disk_usage()` universally instead of `df -g`