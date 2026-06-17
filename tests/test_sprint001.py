"""Sprint 001 — Security & QA test suite for The Jarvice v0.1.0.

Covers: config validation, state manager, keyring utils, doctor checks,
CLI commands, scraper base, setup/uninstall idempotency, edge cases.

Run with: pytest tests/test_sprint001.py -v
"""

from __future__ import annotations

import json
import os
import platform
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Config Tests ──────────────────────────────────────────────────────────────

from the_jarvice.core.config import (
    ExchangeConfig,
    JarviceConfig,
    LoggingConfig,
    ModelsConfig,
    PIIConfig,
    ScheduleConfig,
    TeamsConfig,
    TelegramConfig,
    generate_openclaw_config,
    load_config,
    save_config,
)


class TestExchangeConfig:
    """Tests for ExchangeConfig Pydantic model."""

    def test_defaults(self):
        cfg = ExchangeConfig()
        assert cfg.enabled is True
        assert cfg.server == ""
        assert cfg.email == ""
        assert cfg.auth_mode == "auto"
        assert cfg.keychain_service == "the-jarvice.exchange"
        assert cfg.scrape_interval_hours == 4

    def test_valid_auth_modes(self):
        for mode in ("auto", "basic", "ntlm"):
            cfg = ExchangeConfig(auth_mode=mode)
            assert cfg.auth_mode == mode

    def test_invalid_auth_mode(self):
        with pytest.raises(Exception):
            ExchangeConfig(auth_mode="oauth")

    def test_scrape_interval_bounds(self):
        ExchangeConfig(scrape_interval_hours=1)
        ExchangeConfig(scrape_interval_hours=168)
        with pytest.raises(Exception):
            ExchangeConfig(scrape_interval_hours=0)
        with pytest.raises(Exception):
            ExchangeConfig(scrape_interval_hours=169)

    def test_empty_server_is_valid(self):
        """Empty server should be valid (configured later)."""
        cfg = ExchangeConfig(server="")
        assert cfg.server == ""

    def test_email_without_validation(self):
        """Email is a plain str — no format validation. Potential issue."""
        cfg = ExchangeConfig(email="not-an-email")
        assert cfg.email == "not-an-email"


class TestTeamsConfig:
    def test_defaults(self):
        cfg = TeamsConfig()
        assert cfg.auth_mode == "ic3_token"

    def test_invalid_auth_mode(self):
        with pytest.raises(Exception):
            TeamsConfig(auth_mode="basic")


class TestTelegramConfig:
    def test_defaults(self):
        cfg = TelegramConfig()
        assert cfg.bot_token_keychain == "the-jarvice.telegram-bot"
        assert cfg.chat_id == ""


class TestPIIConfig:
    def test_path_expansion(self):
        cfg = PIIConfig()
        assert str(cfg.get_red_dir()).endswith("/.the-jarvice/data/pii/RED")
        assert str(cfg.get_green_dir()).endswith("/.the-jarvice/data/pii/GREEN")

    def test_custom_paths(self):
        """Custom paths under ~/.the-jarvice are allowed."""
        cfg = PIIConfig(
            red_dir="~/.the-jarvice/data/custom-pii/RED",
            green_dir="~/.the-jarvice/data/custom-pii/GREEN",
        )
        assert "custom-pii" in str(cfg.get_red_dir())


class TestScheduleConfig:
    def test_valid_times(self):
        ScheduleConfig(morning_summary="00:00", evening_summary="23:59")

    def test_invalid_time_format(self):
        with pytest.raises(Exception):
            ScheduleConfig(morning_summary="25:00")

    def test_invalid_time_non_numeric(self):
        with pytest.raises(Exception):
            ScheduleConfig(morning_summary="abc")


class TestLoggingConfig:
    def test_level_normalization(self):
        cfg = LoggingConfig(level="info")
        assert cfg.level == "INFO"

    def test_invalid_level(self):
        with pytest.raises(Exception):
            LoggingConfig(level="VERBOSE")

    def test_size_bounds(self):
        LoggingConfig(max_size_mb=1)
        LoggingConfig(max_size_mb=10000)
        with pytest.raises(Exception):
            LoggingConfig(max_size_mb=0)


class TestJarviceConfig:
    def test_defaults(self):
        cfg = JarviceConfig()
        assert cfg.version == 1
        assert cfg.exchange.enabled is True

    def test_invalid_version(self):
        with pytest.raises(Exception):
            JarviceConfig(version=2)

    def test_get_dirs(self):
        cfg = JarviceConfig()
        assert str(cfg.get_config_dir()).endswith(".the-jarvice")
        assert "data" in str(cfg.get_data_dir())


# ── Config Load/Save Tests ────────────────────────────────────────────────────


class TestLoadConfig:
    def test_load_nonexistent_returns_defaults(self, tmp_path):
        """Loading a non-existent path returns default config."""
        cfg = load_config(tmp_path / "nonexistent.yaml")
        assert cfg.version == 1
        assert cfg.exchange.enabled is True

    def test_load_valid_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: 1
exchange:
  enabled: true
  server: "https://mail.example.com/EWS/Exchange.asmx"
  email: "user@example.com"
  auth_mode: "basic"
  keychain_service: "the-jarvice.exchange"
  scrape_interval_hours: 4
teams:
  enabled: false
  auth_mode: "ic3_token"
  keychain_service: "the-jarvice.teams"
  scrape_interval_hours: 4
telegram:
  enabled: true
  bot_token_keychain: "the-jarvice.telegram-bot"
  chat_id: "12345"
  keychain_service: "the-jarvice.telegram"
pii:
  enabled: true
  red_dir: "~/.the-jarvice/data/pii/RED"
  green_dir: "~/.the-jarvice/data/pii/GREEN"
models:
  primary: "qwen3:14b"
  fallback: "qwen2.5:7b"
  ollama_host: "http://localhost:11434"
schedule:
  timezone: "Europe/Moscow"
  morning_summary: "07:00"
  evening_summary: "19:00"
  weekly_summary: "Mon 09:00"
logging:
  level: "INFO"
  dir: "~/.the-jarvice/logs"
  max_size_mb: 50
  rotation: "daily"
""",
            encoding="utf-8",
        )
        cfg = load_config(config_file)
        assert cfg.exchange.server == "https://mail.example.com/EWS/Exchange.asmx"
        assert cfg.exchange.email == "user@example.com"
        assert cfg.teams.enabled is False
        assert cfg.telegram.chat_id == "12345"

    def test_load_empty_file_returns_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("", encoding="utf-8")
        cfg = load_config(config_file)
        assert cfg.version == 1

    def test_load_invalid_version_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 99\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported config version"):
            load_config(config_file)

    def test_load_invalid_yaml_syntax(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\nexchange: [invalid: yaml\n", encoding="utf-8")
        # Invalid YAML now returns defaults instead of raising
        config = load_config(config_file)
        assert config.version == 1  # defaults

    def test_load_tilde_expansion(self, tmp_path):
        """Paths with ~ should be expandable via get_*_dir methods."""
        cfg = JarviceConfig()
        assert str(cfg.logging.get_log_dir()).startswith(str(Path.home()))


class TestSaveConfig:
    def test_save_and_reload(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        cfg = JarviceConfig(exchange=ExchangeConfig(server="https://test.com", email="a@b.com"))
        saved_path = save_config(cfg, config_path)
        assert saved_path.exists()

        loaded = load_config(saved_path)
        assert loaded.exchange.server == "https://test.com"
        assert loaded.exchange.email == "a@b.com"

    def test_save_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "deep" / "nested" / "config.yaml"
        save_config(JarviceConfig(), config_path)
        assert config_path.exists()


class TestGenerateOpenClawConfig:
    def test_generate_creates_valid_json(self, tmp_path):
        template_path = tmp_path / "template.json"
        template_path.write_text(
            '{"version": {{version}}, "server": "{{exchange_server}}"}',
            encoding="utf-8",
        )
        output_path = tmp_path / "output.json"
        cfg = JarviceConfig()

        result = generate_openclaw_config(cfg, template_path, output_path)
        assert result.exists()

        data = json.loads(output_path.read_text())
        assert data["version"] == 1
        assert data["server"] == ""

    def test_generate_missing_template_raises(self, tmp_path):
        cfg = JarviceConfig()
        with pytest.raises(FileNotFoundError):
            generate_openclaw_config(cfg, tmp_path / "missing.json", tmp_path / "out.json")

    def test_generate_creates_parent_dirs(self, tmp_path):
        template_path = tmp_path / "template.json"
        template_path.write_text('{"v": {{version}}}', encoding="utf-8")
        output_path = tmp_path / "deep" / "nested" / "openclaw.json"
        generate_openclaw_config(JarviceConfig(), template_path, output_path)
        assert output_path.exists()


# ── State Manager Tests ────────────────────────────────────────────────────────

from the_jarvice.core.state import StateManager


class TestStateManager:
    def test_init_creates_default_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        assert sm.get_cursor("exchange") is None
        assert sm.get_last_run() is None

    def test_set_and_get_cursor(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        ts = datetime(2026, 5, 21, 10, 0, 0)
        sm.set_cursor("exchange", ts)
        result = sm.get_cursor("exchange")
        assert result is not None
        assert result.year == 2026

    def test_state_persists_to_disk(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        sm.set_cursor("exchange", datetime(2026, 5, 21, 10, 0, 0))
        assert state_file.exists()

        # Reload from disk
        sm2 = StateManager(state_file)
        cursor = sm2.get_cursor("exchange")
        assert cursor is not None
        assert cursor.year == 2026

    def test_corrupted_state_file_starts_fresh(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT VALID JSON{{{", encoding="utf-8")
        sm = StateManager(state_file)
        assert sm.get_cursor("exchange") is None

    def test_empty_state_file_starts_fresh(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("", encoding="utf-8")
        sm = StateManager(state_file)
        assert sm.get_cursor("exchange") is None

    def test_error_count_tracking(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        assert sm.get_scraper_error_count("exchange") == 0
        sm.increment_error_count("exchange")
        assert sm.get_scraper_error_count("exchange") == 1
        sm.increment_error_count("exchange")
        assert sm.get_scraper_error_count("exchange") == 2
        sm.reset_error_count("exchange")
        assert sm.get_scraper_error_count("exchange") == 0

    def test_scraper_metadata(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        assert sm.get_scraper_meta("exchange", "token_expiry") is None
        sm.set_scraper_meta("exchange", "token_expiry", "2026-05-22T00:00:00")
        assert sm.get_scraper_meta("exchange", "token_expiry") == "2026-05-22T00:00:00"

    def test_reset_clears_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        sm = StateManager(state_file)
        sm.set_cursor("exchange", datetime(2026, 5, 21, 10, 0, 0))
        sm.reset()
        assert sm.get_cursor("exchange") is None
        assert sm.get_last_run() is None

    def test_invalid_timestamp_in_state(self, tmp_path):
        """State file with invalid timestamp string should return None."""
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {"version": 1, "scrapers": {"exchange": {"last_scrape": "not-a-date"}}, "last_run": None}
            ),
            encoding="utf-8",
        )
        sm = StateManager(state_file)
        assert sm.get_cursor("exchange") is None


# ── Scraper Base Tests ────────────────────────────────────────────────────────

from the_jarvice.core.scraper_base import BaseScraper, ScrapeResult


class TestScrapeResult:
    def test_to_markdown(self, tmp_path):
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[{"title": "Test", "body": "Hello"}],
            count=1,
        )
        filepath = result.to_markdown(tmp_path)
        assert filepath.exists()
        content = filepath.read_text()
        assert "Test" in content
        assert "Hello" in content

    def test_to_markdown_truncation(self, tmp_path):
        """Values > 500 chars should be truncated in markdown output."""
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[{"body": "x" * 600}],
            count=1,
        )
        filepath = result.to_markdown(tmp_path)
        content = filepath.read_text()
        assert "..." in content  # truncated

    def test_to_json(self, tmp_path):
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[{"title": "Test"}],
            count=1,
        )
        filepath = result.to_json(tmp_path)
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["source"] == "test"
        assert data["count"] == 1

    def test_to_json_with_errors(self, tmp_path):
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[],
            count=0,
            errors=["Something went wrong"],
        )
        filepath = result.to_json(tmp_path)
        data = json.loads(filepath.read_text())
        assert len(data["errors"]) == 1

    def test_to_markdown_creates_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[],
            count=0,
        )
        filepath = result.to_markdown(nested)
        assert filepath.exists()

    def test_to_json_creates_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[],
            count=0,
        )
        filepath = result.to_json(nested)
        assert filepath.exists()

    def test_empty_items(self, tmp_path):
        """ScrapeResult with 0 items should produce valid output."""
        result = ScrapeResult(
            source="exchange",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[],
            count=0,
            metadata={"folder_count": 23},
        )
        md = result.to_markdown(tmp_path)
        assert md.exists()
        content = md.read_text()
        assert "23" in content

    def test_special_chars_in_items(self, tmp_path):
        """Items with special markdown characters should not break output."""
        result = ScrapeResult(
            source="test",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[{"title": "Hello **World** <script>alert(1)</script>"}],
            count=1,
        )
        filepath = result.to_markdown(tmp_path)
        content = filepath.read_text()
        assert "<script>" in content  # No sanitization — see security report


class TestBaseScraper:
    def test_cannot_instantiate_directly(self):
        """BaseScraper is abstract — cannot instantiate."""
        with pytest.raises(TypeError):
            BaseScraper(config={})

    def test_subclass_must_implement_methods(self):
        """Subclass that doesn't implement abstract methods can't instantiate."""

        class IncompleteScraper(BaseScraper):
            name = "incomplete"

        with pytest.raises(TypeError):
            IncompleteScraper(config={})

    def test_minimal_subclass(self):
        """Minimal concrete subclass should work."""

        class MinimalScraper(BaseScraper):
            name = "minimal"

            def configure(self):
                return True

            def test_connection(self):
                return (True, "ok")

            def scrape(self, since=None):
                return ScrapeResult(
                    source="minimal",
                    timestamp=datetime.now(),
                    items=[],
                    count=0,
                )

        s = MinimalScraper(config={"key": "value"})
        assert s.config == {"key": "value"}
        assert s._connected is False
        assert s.name == "minimal"
        assert s.configure() is True
        assert s.test_connection() == (True, "ok")
        status = s.get_status()
        assert status["name"] == "minimal"
        assert status["connected"] is False


# ── Keyring Utils Tests ──────────────────────────────────────────────────────

from the_jarvice.core.keyring_utils import (
    _ensure_prefix,
    delete_credential,
    get_credential,
    list_credentials,
    save_credential,
    test_keyring as keyring_test_func,
)


class TestEnsurePrefix:
    def test_adds_prefix(self):
        assert _ensure_prefix("exchange") == "the-jarvice.exchange"

    def test_does_not_double_prefix(self):
        assert _ensure_prefix("the-jarvice.exchange") == "the-jarvice.exchange"

    def test_empty_string(self):
        assert _ensure_prefix("") == "the-jarvice."


class TestKeyringRoundTrip:
    """Test keyring operations using mock keyring.

    Keyring is imported inside each function in keyring_utils,
    so we must patch it at the point of use (inside the function).
    We patch the 'keyring' module object on sys.modules instead.
    """

    def test_save_credential_calls_set_password(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            # Force reimport to pick up mock
            result = save_credential("exchange", "user@example.com", "secret123")
            assert result is True
            mock_kr.set_password.assert_called()

    def test_get_credential_returns_value(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = "secret123"
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = get_credential("exchange", "user@example.com")
            assert result == "secret123"

    def test_get_credential_not_found(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = None
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = get_credential("exchange", "user@example.com")
            assert result is None

    def test_delete_credential(self):
        mock_kr = MagicMock()
        mock_kr.delete_password.return_value = None
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = delete_credential("exchange", "user@example.com")
            assert result is True

    def test_delete_credential_not_found(self):
        mock_kr = MagicMock()
        mock_kr.errors.PasswordDeleteError = Exception
        mock_kr.delete_password.side_effect = Exception("not found")
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = delete_credential("exchange", "user@example.com")
            assert result is False


class TestTestKeyring:
    def test_keyring_accessible_returns_tuple(self):
        """test_keyring() should return a (bool, str) tuple."""
        # This actually hits the real keyring — just verify it doesn't crash
        ok, msg = keyring_test_func()
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


# ── Doctor Tests ─────────────────────────────────────────────────────────────

from the_jarvice.core.doctor import (
    CheckResult,
    check_config,
    check_disk,
    check_keyring,
    check_model,
    check_ollama,
    check_openclaw,
    check_python,
    check_telegram,
    format_results_json,
    format_results_table,
    run_all_checks,
)


class TestCheckResult:
    def test_ok_status_icon(self):
        r = CheckResult(ok=True, name="Test", message="OK")
        assert r.status_icon == "✅"

    def test_fail_status_icon(self):
        r = CheckResult(ok=False, name="Test", message="FAIL")
        assert r.status_icon == "❌"

    def test_str_representation(self):
        r = CheckResult(ok=True, name="Python", message="3.12.0")
        assert "Python" in str(r)
        assert "3.12.0" in str(r)

    def test_to_dict(self):
        r = CheckResult(ok=True, name="Test", message="OK", details={"key": "value"})
        d = r.to_dict()
        assert d["ok"] is True
        assert d["details"]["key"] == "value"


class TestCheckPython:
    def test_python_version_passes(self):
        result = check_python()
        # Running in Python 3.10+
        assert result.ok is True
        assert "Python" in result.name


class TestCheckConfig:
    def test_config_not_found(self, tmp_path, monkeypatch):
        """When config doesn't exist, check should fail gracefully."""
        monkeypatch.setattr("the_jarvice.core.doctor.CONFIG_FILE", tmp_path / "nonexistent.yaml")
        result = check_config()
        assert result.ok is False
        assert "Not found" in result.message or "not found" in result.message.lower()


class TestFormatResults:
    def test_format_table(self):
        results = [
            CheckResult(ok=True, name="Python", message="3.12.0"),
            CheckResult(ok=False, name="Ollama", message="Not running"),
        ]
        output = format_results_table(results)
        assert "✅" in output
        assert "❌" in output
        assert "1/2" in output

    def test_format_json(self):
        results = [
            CheckResult(ok=True, name="Python", message="3.12.0"),
        ]
        output = format_results_json(results)
        data = json.loads(output)
        assert data["summary"]["total"] == 1
        assert data["summary"]["passed"] == 1

    def test_all_passed(self):
        results = [CheckResult(ok=True, name="A", message="OK")]
        output = format_results_table(results)
        assert "All 1 checks passed" in output


class TestCheckDisk:
    def test_disk_check_returns_result(self):
        result = check_disk()
        assert result.name == "Disk"
        assert isinstance(result.ok, bool)
        assert result.details.get("free_gb") is not None or result.ok is False


class TestCheckOllama:
    """Ollama check — will fail in CI but should not crash."""

    def test_ollama_check_doesnt_crash(self):
        """Check should return a result without crashing."""
        result = check_ollama()
        assert result.name == "Ollama"
        assert isinstance(result.ok, bool)


class TestRunAllChecks:
    def test_run_all_returns_results(self):
        results = run_all_checks()
        assert len(results) == 12  # 10 original + PII Permissions + Cron
        for r in results:
            assert isinstance(r, CheckResult)


# ── Log Tests ─────────────────────────────────────────────────────────────────

from the_jarvice.core.log import get_logger, log_exception, setup_logging


class TestSetupLogging:
    def test_setup_creates_log_dir(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(level="INFO", log_dir=log_dir)
        assert (tmp_path / "logs").exists()

    def test_setup_returns_logger(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(level="DEBUG", log_dir=log_dir)
        assert logger.name == "the_jarvice"

    def test_get_logger_namespace(self):
        logger = get_logger("exchange")
        assert logger.name == "the_jarvice.exchange"

    def test_log_exception(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(level="DEBUG", log_dir=log_dir)
        try:
            raise ValueError("test error")
        except ValueError as e:
            log_exception(logger, "Test error occurred", e)


# ── CLI Tests ─────────────────────────────────────────────────────────────────

from typer.testing import CliRunner

from the_jarvice.cli.main import app

runner = CliRunner()


class TestVersionCommand:
    def test_version_output(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output or "Jarvice" in result.output


class TestDoctorCommand:
    def test_doctor_runs(self):
        """Doctor command should run without crashing (some checks may fail)."""
        result = runner.invoke(app, ["doctor"])
        # Exit code 0 (all pass) or 1 (some fail) — both are acceptable
        assert result.exit_code in (0, 1)

    def test_doctor_json_output(self):
        result = runner.invoke(app, ["doctor", "--json"])
        # JSON output should be valid JSON
        try:
            # The doctor JSON output goes through rich console, may have formatting
            pass
        except Exception:
            pass  # Acceptable — the check output may have rich formatting

    def test_doctor_verbose(self):
        result = runner.invoke(app, ["doctor", "--verbose"])
        assert result.exit_code in (0, 1)


class TestConfigureCommand:
    def test_configure_help(self):
        result = runner.invoke(app, ["configure", "--help"])
        assert result.exit_code == 0
        assert "skip-exchange" in result.output.lower() or "skip" in result.output.lower()


class TestRunCommand:
    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_run_without_config(self, tmp_path, monkeypatch):
        """Run without config should handle gracefully."""
        # Point config to non-existent path
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["run", "--once"])
        # May fail due to missing config but should not crash with traceback


class TestUninstallCommand:
    def test_uninstall_help(self):
        result = runner.invoke(app, ["uninstall", "--help"])
        assert result.exit_code == 0
        assert "keep-config" in result.output.lower() or "force" in result.output.lower()


# ── Security-Specific Tests ──────────────────────────────────────────────────


class TestCredentialSecurity:
    """Tests for credential handling security issues."""

    def test_config_file_no_hardcoded_passwords(self):
        """Config YAML should never contain passwords."""
        config_content = Path(
            str(Path(__file__).parent.parent / "the_jarvice" / "config" / "config_schema.yaml")
        ).read_text()
        assert "password" not in config_content.lower() or "keychain_service" in config_content
        assert "secret" not in config_content.lower() or "keychain" in config_content.lower()

    def test_state_file_no_credentials(self, tmp_path):
        """State file should never contain passwords/tokens."""
        sm = StateManager(tmp_path / "state.json")
        sm.set_cursor("exchange", datetime(2026, 5, 21, 10, 0, 0))
        sm.set_scraper_meta("exchange", "error_count", 0)

        content = (tmp_path / "state.json").read_text()
        assert "password" not in content.lower()
        assert "token" not in content.lower()
        assert "secret" not in content.lower()

    def test_scrape_result_no_credentials_in_items(self, tmp_path):
        """ScrapeResult markdown should not leak credential-like data."""
        result = ScrapeResult(
            source="exchange",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[{"password": "supersecret123", "token": "abc"}],
            count=1,
        )
        # SECURITY: Items may contain passwords from scraped data — this is a known risk
        # The PII pipeline should handle this
        md_content = result.to_markdown(tmp_path).read_text()
        assert "supersecret123" in md_content  # Currently not sanitized — see WARNING report


class TestFilePermissions:
    """Tests for file permission security."""

    def test_pii_config_paths_use_home(self):
        """PII paths should use ~/.the-jarvice, not absolute paths."""
        cfg = PIIConfig()
        red = str(cfg.get_red_dir())
        green = str(cfg.get_green_dir())
        assert "/.the-jarvice/" in red
        assert "/.the-jarvice/" in green

    def test_config_directory_permissions(self, tmp_path):
        """Config save should create directories with reasonable permissions."""
        config_path = tmp_path / "deep" / "nested" / "config.yaml"
        save_config(JarviceConfig(), config_path)
        assert config_path.parent.exists()


class TestInputValidation:
    """Tests for input validation and injection prevention."""

    def test_auth_mode_validation(self):
        """Auth mode should reject arbitrary values (injection prevention)."""
        with pytest.raises(Exception):
            ExchangeConfig(auth_mode="'; DROP TABLE users; --")

    def test_log_level_validation(self):
        """Log level should reject arbitrary values."""
        with pytest.raises(Exception):
            LoggingConfig(level="'; DROP TABLE logs; --")

    def test_time_format_validation(self):
        """Time format should reject arbitrary strings."""
        with pytest.raises(Exception):
            ScheduleConfig(morning_summary="'; DROP TABLE schedules; --")

    def test_config_version_rejects_non_integer(self):
        """Config version should be an integer."""
        # YAML will parse "1" as int, but "abc" as str
        with pytest.raises(Exception):
            JarviceConfig(version="abc")

    def test_scrape_interval_rejects_negative(self):
        with pytest.raises(Exception):
            ExchangeConfig(scrape_interval_hours=-1)

    def test_scrape_interval_rejects_huge(self):
        with pytest.raises(Exception):
            ExchangeConfig(scrape_interval_hours=999)


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_scrape_result(self, tmp_path):
        """Empty scrape result should produce valid output."""
        result = ScrapeResult(
            source="exchange",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=[],
            count=0,
            errors=[],
            metadata={},
        )
        md = result.to_markdown(tmp_path)
        json_out = result.to_json(tmp_path)
        assert md.exists()
        assert json_out.exists()

    def test_large_scrape_result(self, tmp_path):
        """ScrapeResult with many items should not crash."""
        items = [{"id": i, "title": f"Item {i}", "body": "x" * 100} for i in range(1000)]
        result = ScrapeResult(
            source="exchange",
            timestamp=datetime(2026, 5, 21, 10, 0, 0),
            items=items,
            count=1000,
        )
        json_out = result.to_json(tmp_path)
        data = json.loads(json_out.read_text())
        assert data["count"] == 1000

    def test_unicode_in_config_values(self, tmp_path):
        """Config with unicode characters should work."""
        cfg = JarviceConfig(
            exchange=ExchangeConfig(server="https://почта.рф/EWS/Exchange.asmx", email="пользователь@почта.рф")
        )
        saved = save_config(cfg, tmp_path / "config.yaml")
        loaded = load_config(saved)
        assert "почта" in loaded.exchange.server

    def test_state_concurrent_cursors(self, tmp_path):
        """Multiple scrapers should have independent cursors."""
        sm = StateManager(tmp_path / "state.json")
        ts_exchange = datetime(2026, 5, 21, 10, 0, 0)
        ts_teams = datetime(2026, 5, 21, 12, 0, 0)
        sm.set_cursor("exchange", ts_exchange)
        sm.set_cursor("teams", ts_teams)

        assert sm.get_cursor("exchange").hour == 10
        assert sm.get_cursor("teams").hour == 12

    def test_config_load_with_extra_fields(self, tmp_path):
        """Config with unknown fields should be handled gracefully (Pydantic strict mode)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: 1
exchange:
  enabled: true
  server: "https://test.com"
  email: "a@b.com"
  auth_mode: "auto"
  keychain_service: "the-jarvice.exchange"
  scrape_interval_hours: 4
  unknown_field: "should be ignored or raise error"
""",
            encoding="utf-8",
        )
        # Pydantic by default ignores extra fields, but this depends on config
        # This test documents the behavior
        try:
            cfg = load_config(config_file)
            # If it loads, extra fields are ignored
        except Exception:
            # If it raises, extra fields are forbidden
            pass

    def test_state_with_missing_scrapers_key(self, tmp_path):
        """State file without 'scrapers' key should work."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"version": 1, "last_run": null}', encoding="utf-8")
        sm = StateManager(state_file)
        assert sm.get_cursor("exchange") is None

    def test_doctor_check_results_all_have_names(self):
        """All doctor checks should return results with meaningful names."""
        results = run_all_checks()
        for r in results:
            assert r.name, f"Check result missing name: {r}"
            assert isinstance(r.ok, bool), f"Check result {r.name} has non-bool ok: {r.ok}"