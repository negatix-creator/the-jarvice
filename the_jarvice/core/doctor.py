"""
Diagnostic checks module for The Jarvice.

Performs health checks on all system components and reports status.
Used by `the-jarvice doctor` CLI command.

Each check returns a CheckResult with:
  - ok: bool — whether the check passed
  - name: str — human-readable check name
  - message: str — status message
  - details: dict — optional extra information
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
JARVICE_DIR = Path.home() / ".the-jarvice"
CONFIG_FILE = JARVICE_DIR / "config.yaml"
STATE_FILE = JARVICE_DIR / "state.json"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:14b"
MIN_DISK_GB = 12
MIN_PYTHON_MAJOR = 3
MIN_PYTHON_MINOR = 10
MIN_NODE_MAJOR = 20


# ---------------------------------------------------------------------------
# Check result dataclass
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    ok: bool
    name: str
    message: str
    details: dict = field(default_factory=dict)

    @property
    def status_icon(self) -> str:
        if self.ok:
            return "✅"
        return "❌"

    def __str__(self) -> str:
        return f"{self.status_icon} {self.name}: {self.message}"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_python() -> CheckResult:
    """Check Python version (3.10+ required)."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major > MIN_PYTHON_MAJOR or (
        version.major == MIN_PYTHON_MAJOR and version.minor >= MIN_PYTHON_MINOR
    ):
        return CheckResult(
            ok=True,
            name="Python",
            message=f"Python {version_str}",
            details={"version": version_str, "path": sys.executable},
        )
    return CheckResult(
        ok=False,
        name="Python",
        message=f"Python {version_str} (need {MIN_PYTHON_MAJOR}.{MIN_PYTHON_MINOR}+)",
        details={"version": version_str, "path": sys.executable},
    )


def check_ollama() -> CheckResult:
    """Check if Ollama is running and accessible."""
    host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

    ollama_path = shutil.which("ollama")
    if not ollama_path:
        return CheckResult(
            ok=False,
            name="Ollama",
            message="Ollama not found (install: brew install ollama)",
            details={"installed": False},
        )

    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip() or "unknown"
    except Exception:
        version = "unknown"

    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        if resp.status_code == 200:
            return CheckResult(
                ok=True,
                name="Ollama",
                message=f"Running ({host}) [{version}]",
                details={
                    "installed": True,
                    "running": True,
                    "host": host,
                    "version": version,
                    "path": ollama_path,
                },
            )
        return CheckResult(
            ok=False,
            name="Ollama",
            message=f"Not responding at {host} (status {resp.status_code})",
            details={"installed": True, "running": False, "host": host},
        )
    except requests.ConnectionError:
        return CheckResult(
            ok=False,
            name="Ollama",
            message=f"Not running at {host} (start with: ollama serve)",
            details={"installed": True, "running": False, "host": host},
        )
    except requests.Timeout:
        return CheckResult(
            ok=False,
            name="Ollama",
            message=f"Timeout connecting to {host}",
            details={"installed": True, "running": False, "host": host},
        )


def check_model(model_name: Optional[str] = None) -> CheckResult:
    """Check if the required model is downloaded in Ollama."""
    if model_name is None:
        model_name = _get_config_model() or DEFAULT_MODEL

    host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        if resp.status_code != 200:
            return CheckResult(
                ok=False,
                name="Model",
                message="Cannot check model (Ollama not responding)",
                details={"model": model_name, "ollama_running": False},
            )
    except Exception:
        return CheckResult(
            ok=False,
            name="Model",
            message="Cannot check model (Ollama not running)",
            details={"model": model_name, "ollama_running": False},
        )

    data = resp.json()
    models = {m.get("name", ""): m for m in data.get("models", [])}
    model_info = models.get(model_name) or models.get(f"{model_name}:latest")

    if model_info:
        size_bytes = model_info.get("size", 0)
        size_gb = size_bytes / (1024**3) if size_bytes else 0
        size_str = f"{size_gb:.1f} GB" if size_gb > 0 else "unknown size"
        return CheckResult(
            ok=True,
            name="Model",
            message=f"{model_name} downloaded ({size_str})",
            details={
                "model": model_name,
                "downloaded": True,
                "size_bytes": size_bytes,
                "size_gb": round(size_gb, 1),
            },
        )

    return CheckResult(
        ok=False,
        name="Model",
        message=f"{model_name} not downloaded (run: ollama pull {model_name})",
        details={"model": model_name, "downloaded": False},
    )


def check_keyring() -> CheckResult:
    """Check keyring accessibility (macOS Keychain / Linux libsecret)."""
    from the_jarvice.core.keyring_utils import test_keyring

    ok, message = test_keyring()
    return CheckResult(
        ok=ok,
        name="Keyring",
        message=message,
        details={"platform": platform.system()},
    )


def check_config() -> CheckResult:
    """Check if config.yaml exists and is valid."""
    if not CONFIG_FILE.exists():
        return CheckResult(
            ok=False,
            name="Config",
            message=f"Not found ({CONFIG_FILE})",
            details={"path": str(CONFIG_FILE), "exists": False},
        )

    try:
        import yaml

        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)

        if config is None:
            return CheckResult(
                ok=False,
                name="Config",
                message="Config file is empty",
                details={"path": str(CONFIG_FILE), "exists": True, "valid": False},
            )

        version = config.get("version", 0)
        if version < 1:
            return CheckResult(
                ok=False,
                name="Config",
                message=f"Invalid config version: {version}",
                details={"path": str(CONFIG_FILE), "exists": True, "valid": False},
            )

        try:
            from the_jarvice.core.config import JarviceConfig

            JarviceConfig(**config)
        except ImportError:
            pass
        except Exception as e:
            return CheckResult(
                ok=False,
                name="Config",
                message=f"Config validation error: {e}",
                details={"path": str(CONFIG_FILE), "exists": True, "valid": False},
            )

        return CheckResult(
            ok=True,
            name="Config",
            message=f"Valid ({CONFIG_FILE})",
            details={"path": str(CONFIG_FILE), "exists": True, "valid": True},
        )

    except ImportError:
        return CheckResult(
            ok=True,
            name="Config",
            message=f"Exists ({CONFIG_FILE})",
            details={"path": str(CONFIG_FILE), "exists": True, "valid": "unknown"},
        )
    except Exception as e:
        return CheckResult(
            ok=False,
            name="Config",
            message=f"Parse error: {e}",
            details={"path": str(CONFIG_FILE), "exists": True, "valid": False},
        )


def check_exchange() -> CheckResult:
    """Check Exchange connection (if enabled in config)."""
    config = _load_config()
    if not config:
        return CheckResult(
            ok=False,
            name="Exchange",
            message="Config not found (run: the-jarvice configure)",
            details={"enabled": False},
        )

    exchange_cfg = config.get("exchange", {})
    if not exchange_cfg.get("enabled", True):
        return CheckResult(
            ok=True,
            name="Exchange",
            message="Disabled in config",
            details={"enabled": False},
        )

    server = exchange_cfg.get("server", "")
    email = exchange_cfg.get("email", "")

    if not server:
        return CheckResult(
            ok=False,
            name="Exchange",
            message="Server not configured (run: the-jarvice configure)",
            details={"enabled": True, "configured": False},
        )

    from the_jarvice.core.keyring_utils import get_credential

    keychain_service = exchange_cfg.get("keychain_service", "the-jarvice.exchange")
    password = get_credential(keychain_service, email or "default")

    if not password:
        return CheckResult(
            ok=False,
            name="Exchange",
            message=f"Credentials not found (server: {server})",
            details={"enabled": True, "configured": True, "has_credentials": False},
        )

    try:
        from exchangelib import Account, Configuration, Credentials, DELEGATE

        creds = Credentials(email, password)
        config_obj = Configuration(server=server, credentials=creds)
        account = Account(
            primary_smtp_address=email,
            config=config_obj,
            autodiscover=False,
            access_type=DELEGATE,
        )
        folder_count = len(list(account.root.get_folders()))
        return CheckResult(
            ok=True,
            name="Exchange",
            message=f"Connected ({server}, {folder_count} folders)",
            details={
                "enabled": True,
                "configured": True,
                "has_credentials": True,
                "server": server,
                "email": email,
                "folders": folder_count,
            },
        )
    except ImportError:
        return CheckResult(
            ok=False,
            name="Exchange",
            message="exchangelib not installed",
            details={"enabled": True, "configured": True},
        )
    except Exception as e:
        return CheckResult(
            ok=False,
            name="Exchange",
            message=f"Connection failed: {e}",
            details={
                "enabled": True,
                "configured": True,
                "has_credentials": True,
                "server": server,
                "error": str(e),
            },
        )


def check_teams() -> CheckResult:
    """Check Teams token validity and age (if enabled in config)."""
    config = _load_config()
    if not config:
        return CheckResult(
            ok=False,
            name="Teams",
            message="Config not found (run: the-jarvice configure)",
            details={"enabled": False},
        )

    teams_cfg = config.get("teams", {})
    if not teams_cfg.get("enabled", True):
        return CheckResult(
            ok=True,
            name="Teams",
            message="Disabled in config",
            details={"enabled": False},
        )

    from the_jarvice.core.keyring_utils import get_credential

    keychain_service = teams_cfg.get("keychain_service", "the-jarvice.teams")
    token = get_credential(keychain_service, "ic3_token")

    if not token:
        return CheckResult(
            ok=False,
            name="Teams",
            message="Token not found (run: the-jarvice configure --reauth teams)",
            details={"enabled": True, "has_token": False},
        )

    # Check token age from state.json
    details: dict[str, Any] = {
        "enabled": True,
        "has_token": True,
        "auth_mode": teams_cfg.get("auth_mode", "ic3_token"),
    }

    try:
        from the_jarvice.core.state import StateManager
        from the_jarvice.scrapers.teams.scraper import _is_token_expired

        # Check if token is expired via JWT decode
        is_expired = _is_token_expired(token)
        details["token_expired"] = is_expired

        # Check age from state.json
        state = StateManager()
        token_set_at = state.get_scraper_meta("teams", "token_set_at")
        if token_set_at:
            from datetime import datetime
            set_at = datetime.fromisoformat(token_set_at)
            age_hours = (datetime.now(set_at.tzinfo) - set_at).total_seconds() / 3600
            details["token_age_hours"] = round(age_hours, 1)
            details["token_set_at"] = token_set_at

            if is_expired:
                return CheckResult(
                    ok=False,
                    name="Teams",
                    message=f"IC3 token expired ({age_hours:.0f}h old, re-extract from browser)",
                    details=details,
                )
            elif age_hours > 20:
                return CheckResult(
                    ok=True,
                    name="Teams",
                    message=f"Token valid but aging ({age_hours:.0f}h old, expires ~24h)",
                    details=details,
                )
            else:
                return CheckResult(
                    ok=True,
                    name="Teams",
                    message=f"Token valid ({age_hours:.0f}h old)",
                    details=details,
                )
        else:
            # No age info — just check JWT expiry
            if is_expired:
                return CheckResult(
                    ok=False,
                    name="Teams",
                    message="IC3 token expired (re-extract from browser DevTools)",
                    details=details,
                )
            return CheckResult(
                ok=True,
                name="Teams",
                message="Token present (age unknown, IC3 tokens expire ~24h)",
                details=details,
            )
    except Exception as exc:
        logger.debug("Token age check failed: %s", exc)
        return CheckResult(
            ok=True,
            name="Teams",
            message="Token present (IC3 tokens expire ~24h, use --reauth to refresh)",
            details=details,
        )


def check_telegram() -> CheckResult:
    """Check Telegram bot token validity (if enabled in config)."""
    config = _load_config()
    if not config:
        return CheckResult(
            ok=False,
            name="Telegram",
            message="Config not found (run: the-jarvice configure)",
            details={"enabled": False},
        )

    tg_cfg = config.get("telegram", {})
    if not tg_cfg.get("enabled", True):
        return CheckResult(
            ok=True,
            name="Telegram",
            message="Disabled in config",
            details={"enabled": False},
        )

    from the_jarvice.core.keyring_utils import get_credential

    keychain_service = tg_cfg.get("bot_token_keychain", "the-jarvice.telegram-bot")
    bot_token = get_credential(keychain_service, "bot_token")

    if not bot_token:
        return CheckResult(
            ok=False,
            name="Telegram",
            message="Bot token not found (run: the-jarvice configure)",
            details={"enabled": True, "has_token": False},
        )

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10,
        )
        data = resp.json()

        if data.get("ok"):
            bot_info = data.get("result", {})
            bot_name = bot_info.get("username", "unknown")
            return CheckResult(
                ok=True,
                name="Telegram",
                message=f"Bot connected (@{bot_name})",
                details={
                    "enabled": True,
                    "has_token": True,
                    "bot_username": bot_name,
                    "bot_id": bot_info.get("id"),
                },
            )
        else:
            error_msg = data.get("description", "unknown error")
            return CheckResult(
                ok=False,
                name="Telegram",
                message=f"Token invalid: {error_msg}",
                details={"enabled": True, "has_token": True, "error": error_msg},
            )
    except requests.RequestException as e:
        return CheckResult(
            ok=False,
            name="Telegram",
            message=f"Cannot reach Telegram API: {e}",
            details={"enabled": True, "has_token": True},
        )


def check_disk() -> CheckResult:
    """Check available disk space (≥12GB recommended)."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["df", "-g", str(Path.home())],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                free_gb = float(parts[3]) if len(parts) > 3 else 0
            else:
                free_gb = 0
        else:
            usage = shutil.disk_usage(Path.home())
            free_gb = usage.free / (1024**3)

        free_gb = round(free_gb, 1)

        if free_gb >= MIN_DISK_GB:
            return CheckResult(
                ok=True,
                name="Disk",
                message=f"{free_gb} GB free",
                details={"free_gb": free_gb, "min_required_gb": MIN_DISK_GB},
            )
        return CheckResult(
            ok=False,
            name="Disk",
            message=f"Only {free_gb} GB free (need {MIN_DISK_GB}+ GB)",
            details={"free_gb": free_gb, "min_required_gb": MIN_DISK_GB},
        )
    except Exception as e:
        return CheckResult(
            ok=False,
            name="Disk",
            message=f"Cannot check disk space: {e}",
            details={},
        )


def check_openclaw() -> CheckResult:
    """Check if OpenClaw is installed and running."""
    openclaw_path = shutil.which("openclaw")
    if not openclaw_path:
        return CheckResult(
            ok=False,
            name="OpenClaw",
            message="Not found (install: npm install -g openclaw)",
            details={"installed": False},
        )

    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip() or "unknown"
        version = version.split("\n")[0].strip()
    except Exception:
        version = "unknown"

    try:
        result = subprocess.run(
            ["openclaw", "gateway", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        running = "running" in result.stdout.lower() or "running" in result.stderr.lower()
    except Exception:
        running = False

    if running:
        return CheckResult(
            ok=True,
            name="OpenClaw",
            message=f"Running (v{version})",
            details={"installed": True, "running": True, "version": version, "path": openclaw_path},
        )

    return CheckResult(
        ok=False,
        name="OpenClaw",
        message=f"Installed (v{version}) but not running",
        details={"installed": True, "running": False, "version": version, "path": openclaw_path},
    )


# ---------------------------------------------------------------------------
# Run all checks
# ---------------------------------------------------------------------------
def check_pii_permissions() -> CheckResult:
    """Check PII directory and mapping.json permissions.

    Verifies that:
    - ~/.the-jarvice/data/pii/RED/ has mode 0o700 (owner-only)
    - mapping.json has mode 0o600 (owner read/write only)

    Returns:
        CheckResult with ok=True if permissions are correct,
        ok=False with fix instructions if too permissive.
    """
    red_dir = Path.home() / ".the-jarvice" / "data" / "pii" / "RED"
    mapping_file = red_dir / "mapping.json"

    issues = []

    # Check RED directory
    if red_dir.exists():
        mode = red_dir.stat().st_mode & 0o777
        if mode & 0o077:  # group or others have any access
            issues.append(
                f"RED dir permissions {oct(mode)} are too permissive. "
                f"Fix: chmod 700 {red_dir}"
            )
    else:
        # Directory doesn't exist yet — that's fine, it'll be created with correct perms
        pass

    # Check mapping.json
    if mapping_file.exists():
        mode = mapping_file.stat().st_mode & 0o777
        if mode & 0o077:  # group or others have any access
            issues.append(
                f"mapping.json permissions {oct(mode)} are too permissive. "
                f"Fix: chmod 600 {mapping_file}"
            )
    else:
        pass  # File doesn't exist yet

    if issues:
        return CheckResult(
            ok=False,
            name="PII Permissions",
            message="; ".join(issues),
            details={
                "red_dir": str(red_dir),
                "mapping_file": str(mapping_file),
                "issues": issues,
            },
        )

    # All good
    details: dict[str, Any] = {}
    if red_dir.exists():
        details["red_dir_mode"] = oct(red_dir.stat().st_mode & 0o777)
    if mapping_file.exists():
        details["mapping_mode"] = oct(mapping_file.stat().st_mode & 0o777)

    return CheckResult(
        ok=True,
        name="PII Permissions",
        message="PII directory permissions are correct",
        details=details,
    )


def check_cron() -> CheckResult:
    """Check if cron-based scheduled summaries are enabled.

    Looks for the-jarvice-managed entries in the user's crontab.

    Returns:
        CheckResult with ok=True if cron is configured, ok=False otherwise.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return CheckResult(
                ok=False,
                name="Cron",
                message="No crontab found (run: the-jarvice enable)",
                details={"cron_active": False},
            )

        cron_lines = result.stdout.strip().split("\n")
        jarvice_lines = [line for line in cron_lines if "the-jarvice-managed" in line or "the_jarvice" in line]

        if jarvice_lines:
            schedules = []
            for line in jarvice_lines:
                if "morning" in line:
                    schedules.append("morning")
                elif "evening" in line:
                    schedules.append("evening")
                elif "weekly" in line:
                    schedules.append("weekly")
            return CheckResult(
                ok=True,
                name="Cron",
                message=f"Scheduled summaries active ({', '.join(schedules or ['custom'])})",
                details={"cron_active": True, "schedules": schedules, "raw_lines": jarvice_lines},
            )
        else:
            return CheckResult(
                ok=False,
                name="Cron",
                message="No scheduled summaries (run: the-jarvice enable)",
                details={"cron_active": False},
            )

    except FileNotFoundError:
        return CheckResult(
            ok=False,
            name="Cron",
            message="crontab not available on this system",
            details={"cron_active": False, "crontab_missing": True},
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            ok=False,
            name="Cron",
            message="crontab check timed out",
            details={"cron_active": False},
        )
    except Exception as exc:
        return CheckResult(
            ok=False,
            name="Cron",
            message=f"Cron check error: {exc}",
            details={"cron_active": False, "error": str(exc)},
        )


def run_all_checks() -> list[CheckResult]:
    """Run all diagnostic checks and return results.

    Returns:
        List of CheckResult objects, one per check.
    """
    checks = [
        check_python,
        check_ollama,
        check_model,
        check_keyring,
        check_config,
        check_exchange,
        check_teams,
        check_telegram,
        check_disk,
        check_openclaw,
        check_pii_permissions,
        check_cron,
    ]

    results = []
    for check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
        except Exception as e:
            results.append(
                CheckResult(
                    ok=False,
                    name=check_fn.__name__,
                    message=f"Check failed: {e}",
                    details={"error": str(e)},
                )
            )

    return results


def format_results_table(results: list[CheckResult], verbose: bool = False) -> str:
    """Format check results as a readable table.

    Args:
        results: List of CheckResult objects.
        verbose: If True, include detailed information.

    Returns:
        Formatted string for terminal output.
    """
    lines = []
    for r in results:
        line = f"{r.status_icon} {r.message}"
        lines.append(line)
        if verbose and r.details:
            for key, value in r.details.items():
                lines.append(f"   {key}: {value}")

    passed = sum(1 for r in results if r.ok)
    total = len(results)
    lines.append("")
    if passed == total:
        lines.append(f"✅ All {total} checks passed!")
    else:
        lines.append(f"⚠️  {passed}/{total} checks passed. Fix the issues above.")

    return "\n".join(lines)


def format_results_json(results: list[CheckResult]) -> str:
    """Format check results as JSON.

    Args:
        results: List of CheckResult objects.

    Returns:
        JSON string with all results.
    """
    data = {
        "checks": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "all_passed": all(r.ok for r in results),
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_config() -> Optional[dict]:
    """Load config.yaml if it exists."""
    if not CONFIG_FILE.exists():
        return None
    try:
        import yaml

        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _get_config_model() -> Optional[str]:
    """Get model name from config, or None."""
    config = _load_config()
    if config:
        return config.get("models", {}).get("primary")
    return None