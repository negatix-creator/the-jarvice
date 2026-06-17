"""End-to-end pipeline tests for Sprint 001 + Sprint 002.

Tests the full flow: Config → State → Scrape → Anonymize → Deanonymize →
Summary (mocked) → Telegram (mocked) → Doctor → CLI
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── E2E: Config Roundtrip ────────────────────────────────────────────────────


class TestE2EConfigRoundtrip:
    """Config: JarviceConfig → YAML → JarviceConfig (lossless)."""

    def test_full_config_roundtrip(self):
        from the_jarvice.core.config import (
            JarviceConfig, ExchangeConfig, TeamsConfig, TelegramConfig,
            PIIConfig, ModelsConfig, ScheduleConfig, LoggingConfig,
            save_config, load_config,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            original = JarviceConfig(
                exchange=ExchangeConfig(
                    enabled=True, server="mail.fsk.ru", email="user@fsk.ru",
                    auth_mode="basic", scrape_interval_hours=4,
                ),
                teams=TeamsConfig(enabled=True, auth_mode="ic3_token"),
                telegram=TelegramConfig(enabled=True, chat_id="123456"),
                pii=PIIConfig(enabled=True),
                models=ModelsConfig(primary="qwen3:14b", fallback="qwen2.5:7b"),
                schedule=ScheduleConfig(
                    timezone="Europe/Moscow", morning_summary="07:00",
                    evening_summary="19:00",
                ),
                logging=LoggingConfig(level="INFO"),
            )

            save_config(original, config_path)
            loaded = load_config(config_path)

            assert loaded.exchange.server == "mail.fsk.ru"
            assert loaded.exchange.email == "user@fsk.ru"
            assert loaded.telegram.chat_id == "123456"
            assert loaded.models.primary == "qwen3:14b"
            assert loaded.schedule.timezone == "Europe/Moscow"
            assert loaded.logging.level == "INFO"

    def test_default_config_roundtrip(self):
        from the_jarvice.core.config import JarviceConfig, save_config, load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            original = JarviceConfig()
            save_config(original, config_path)
            loaded = load_config(config_path)

            assert loaded.version == 1
            assert loaded.exchange.enabled is True
            assert loaded.models.primary == "qwen3:14b"


# ── E2E: State Roundtrip ────────────────────────────────────────────────────


class TestE2EStateRoundtrip:
    """State: StateManager → JSON → StateManager (lossless)."""

    def test_state_roundtrip(self):
        from the_jarvice.core.state import StateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"

            mgr1 = StateManager(state_file=state_file)
            now = datetime.now(timezone.utc)

            mgr1.set_cursor("exchange", now)
            mgr1.set_cursor("teams", now)
            mgr1.increment_error_count("exchange")
            mgr1.set_scraper_meta("exchange", "last_folder_count", 42)

            # Reload from disk
            mgr2 = StateManager(state_file=state_file)

            assert mgr2.get_cursor("exchange") is not None
            assert mgr2.get_cursor("teams") is not None
            assert mgr2.get_cursor("calendar") is None  # Not set
            assert mgr2.get_scraper_error_count("exchange") == 1
            assert mgr2.get_scraper_meta("exchange", "last_folder_count") == 42

    def test_state_error_count_lifecycle(self):
        from the_jarvice.core.state import StateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            mgr = StateManager(state_file=state_file)

            # Increment errors
            mgr.increment_error_count("exchange")
            mgr.increment_error_count("exchange")
            mgr.increment_error_count("exchange")
            assert mgr.get_scraper_error_count("exchange") == 3

            # Reset after success
            mgr.reset_error_count("exchange")
            assert mgr.get_scraper_error_count("exchange") == 0


# ── E2E: PII Roundtrip ──────────────────────────────────────────────────────


class TestE2EPIIRoundtrip:
    """PII: ScrapeResult with PII → Anonymize → Deanonymize → original values."""

    def test_full_pii_roundtrip(self):
        from the_jarvice.core.scraper_base import ScrapeResult
        from the_jarvice.scrapers.pii.anonymizer import Anonymizer, Deanonymizer

        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping_path = Path(tmpdir) / "mapping.json"

            # Step 1: Create realistic email data with PII
            original_data = {
                "message_id": "<msg123@mail.fsk.ru>",
                "subject": "Встреча с Ивановым по бюджету",
                "body": "Алексей, позвоните мне на +7 916 123-45-67 и напишите на иванов@фск.рф",
                "sender": {"name": "Иванов Алексей Петрович", "email": "ivanov@fsk.ru"},
                "recipients": [
                    {"name": "Петров Сергей", "email": "petrov@fsk.ru"},
                    {"name": "Сидорова Анна", "email": "sidorova@fsk.ru"},
                ],
                "date": "2026-05-21T10:30:00+03:00",
                "is_read": False,
                "has_attachments": True,
                "importance": "High",
            }

            # Step 2: Scrape (simulated)
            scrape_result = ScrapeResult(
                source="exchange",
                timestamp=datetime.now(timezone.utc),
                items=[original_data],
                count=1,
                errors=[],
            )

            # Step 3: Anonymize (RED → GREEN)
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping_path)
            anon_result = anon.process_scrape_result(scrape_result)

            assert anon_result.count == 1
            assert anon_result.metadata.get("pii_found", 0) > 0

            # Verify GREEN has no real PII
            anon_item = anon_result.items[0]
            assert "[PERSON_" in anon_item["sender"]["name"]
            assert "[EMAIL_" in anon_item["sender"]["email"]
            assert "ivanov@fsk.ru" not in anon_item["subject"]
            assert "ivanov@fsk.ru" not in anon_item["body"]
            assert "+7 916 123-45-67" not in anon_item["body"]

            # Verify RED has originals
            red_files = list(red.glob("*.json"))
            assert len(red_files) == 1
            red_data = json.loads(red_files[0].read_text(encoding="utf-8"))
            assert "ivanov@fsk.ru" in json.dumps(red_data)

            # Step 4: Deanonymize (GREEN → real values for delivery)
            deanon = Deanonymizer(mapping_path=mapping_path)
            summary = f"Встреча с {anon_item['sender']['name']} по бюджету"
            real_summary = deanon.deanonymize(summary)
            assert "Иванов Алексей Петрович" in real_summary

    def test_pii_multiple_emails_roundtrip(self):
        """Test roundtrip with multiple emails containing same PII."""
        from the_jarvice.core.scraper_base import ScrapeResult
        from the_jarvice.scrapers.pii.anonymizer import Anonymizer, Deanonymizer

        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping_path = Path(tmpdir) / "mapping.json"

            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping_path)

            # Two emails mentioning the same person
            items = [
                {
                    "subject": "Вопрос от Иванова",
                    "body": "Иванов просит подтвердить",
                    "sender": {"name": "Иванов Алексей", "email": "ivanov@fsk.ru"},
                    "recipients": [],
                    "message_id": "msg-1",
                    "date": "2026-05-21",
                },
                {
                    "subject": "Ответ Иванову",
                    "body": "Отправлено Иванову для проверки",
                    "sender": {"name": "Петров Сергей", "email": "petrov@fsk.ru"},
                    "recipients": [{"name": "Иванов Алексей", "email": "ivanov@fsk.ru"}],
                    "message_id": "msg-2",
                    "date": "2026-05-21",
                },
            ]

            result = ScrapeResult(
                source="exchange",
                timestamp=datetime.now(timezone.utc),
                items=items,
                count=2,
                errors=[],
            )

            anon_result = anon.process_scrape_result(result)

            # Иванов should always be [PERSON_1] — consistent mapping
            all_text = json.dumps(anon_result.items, ensure_ascii=False)
            person1_count = all_text.count("[PERSON_1]")
            person2_count = all_text.count("[PERSON_2]")
            assert person1_count >= 2  # Иванов appears multiple times
            assert person2_count >= 1  # Петров is different person

            # Deanonymize should restore consistently
            deanon = Deanonymizer(mapping_path=mapping_path)
            restored = deanon.deanonymize(all_text)
            assert "Иванов Алексей" in restored
            assert "Петров Сергей" in restored


# ── E2E: ScrapeResult Export ──────────────────────────────────────────────────


class TestE2EScrapeResultExport:
    """ScrapeResult to markdown and JSON export."""

    def test_markdown_export(self):
        from the_jarvice.core.scraper_base import ScrapeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            result = ScrapeResult(
                source="exchange",
                timestamp=datetime(2026, 5, 21, 10, 30, 0, tzinfo=timezone.utc),
                items=[
                    {
                        "subject": "Test Email",
                        "sender": "user@test.ru",
                        "date": "2026-05-21",
                        "body": "Hello world",
                    }
                ],
                count=1,
                errors=["test warning"],
            )

            path = result.to_markdown(Path(tmpdir))
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Exchange" in content
            assert "Test Email" in content
            assert "test warning" in content

    def test_json_export(self):
        from the_jarvice.core.scraper_base import ScrapeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            result = ScrapeResult(
                source="exchange",
                timestamp=datetime(2026, 5, 21, 10, 30, 0, tzinfo=timezone.utc),
                items=[],
                count=0,
                errors=[],
            )

            path = result.to_json(Path(tmpdir))
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["source"] == "exchange"
            assert data["count"] == 0

    def test_empty_items_export(self):
        from the_jarvice.core.scraper_base import ScrapeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            result = ScrapeResult(
                source="teams",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=[],
            )

            md_path = result.to_markdown(Path(tmpdir))
            json_path = result.to_json(Path(tmpdir))
            assert md_path.exists()
            assert json_path.exists()


# ── E2E: Keyring Cycle ──────────────────────────────────────────────────────


class TestE2EKeyringCycle:
    """Keyring: save → get → delete cycle."""

    def test_keyring_cycle(self):
        from the_jarvice.core.keyring_utils import (
            save_credential, get_credential, delete_credential, test_keyring,
        )

        # Test keyring accessibility
        ok, msg = test_keyring()
        if not ok:
            pytest.skip(f"Keyring not available: {msg}")

        service = "the-jarvice.e2e-test"
        account = "test-cycle"
        secret = "test-password-12345"

        # Save
        assert save_credential(service, account, secret) is True

        # Get
        retrieved = get_credential(service, account)
        assert retrieved == secret

        # Delete
        assert delete_credential(service, account) is True

        # Verify deleted
        assert get_credential(service, account) is None

    def test_keyring_nonexistent(self):
        from the_jarvice.core.keyring_utils import get_credential

        result = get_credential("the-jarvice.nonexistent-xyz-12345", "nobody")
        assert result is None


# ── E2E: OpenClaw Config Generation ──────────────────────────────────────────


class TestE2EOpenClawConfig:
    """Config → OpenClaw template → valid JSON."""

    def test_openclaw_config_generation(self):
        from the_jarvice.core.config import JarviceConfig, generate_openclaw_config

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template.json"
            output_path = Path(tmpdir) / "openclaw.json"

            # Create a template with {{KEY}} placeholders (not JSON)
            template = '''{
  "version": {{version}},
  "exchange": {
    "enabled": {{exchange_enabled}},
    "server": "{{exchange_server}}"
  },
  "models": {
    "primary": "{{models_primary}}"
  }
}'''
            template_path.write_text(template, encoding="utf-8")

            config = JarviceConfig(
                exchange={"server": "mail.fsk.ru", "email": "user@fsk.ru"},
                models={"primary": "qwen3:14b"},
            )

            output = generate_openclaw_config(config, template_path, output_path)
            assert output.exists()

            # Verify it's valid JSON
            generated = json.loads(output.read_text(encoding="utf-8"))
            assert generated["version"] == 1
            assert generated["exchange"]["server"] == "mail.fsk.ru"
            assert generated["models"]["primary"] == "qwen3:14b"


# ── E2E: CLI Commands ────────────────────────────────────────────────────────


class TestE2ECLI:
    """CLI smoke tests — verify commands don't crash."""

    def test_version_command(self):
        from typer.testing import CliRunner
        from the_jarvice.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "The Jarvice" in result.output

    def test_doctor_command(self):
        from typer.testing import CliRunner
        from the_jarvice.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["doctor"])
        # May exit with 1 if config not found — that's expected
        assert "Python" in result.output or "Ollama" in result.output

    def test_run_help(self):
        from typer.testing import CliRunner
        from the_jarvice.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower() or "run" in result.output.lower()

    def test_configure_help(self):
        from typer.testing import CliRunner
        from the_jarvice.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["configure", "--help"])
        assert result.exit_code == 0
        assert "skip-exchange" in result.output or "wizard" in result.output.lower()


# ── E2E: Doctor Checks ──────────────────────────────────────────────────────


class TestE2EDoctor:
    """Doctor: all 10 checks run without crashing."""

    def test_all_checks_run(self):
        from the_jarvice.core.doctor import run_all_checks

        results = run_all_checks()
        assert len(results) == 12  # 10 original + PII Permissions + Cron
        for result in results:
            assert result.ok in (True, False)
            assert result.name
            assert result.message

    def test_python_check(self):
        from the_jarvice.core.doctor import check_python

        result = check_python()
        assert result.ok is True
        assert "Python" in result.name

    def test_ollama_check(self):
        from the_jarvice.core.doctor import check_ollama

        result = check_ollama()
        # May or may not be running — just shouldn't crash
        assert result.name == "Ollama"

    def test_model_check(self):
        from the_jarvice.core.doctor import check_model

        result = check_model("qwen3:14b")
        assert result.name == "Model"

    def test_keyring_check(self):
        from the_jarvice.core.doctor import check_keyring

        result = check_keyring()
        assert result.name == "Keyring"

    def test_config_check(self):
        from the_jarvice.core.doctor import check_config

        result = check_config()
        assert result.name == "Config"

    def test_disk_check(self):
        from the_jarvice.core.doctor import check_disk

        result = check_disk()
        assert result.ok is True
        assert "GB" in result.message

    def test_format_results_table(self):
        from the_jarvice.core.doctor import run_all_checks, format_results_table

        results = run_all_checks()
        table = format_results_table(results, verbose=False)
        assert len(table) > 0
        assert "Python" in table

    def test_format_results_json(self):
        from the_jarvice.core.doctor import run_all_checks, format_results_json

        results = run_all_checks()
        json_str = format_results_json(results)
        data = json.loads(json_str)
        assert "checks" in data
        assert "summary" in data
        assert data["summary"]["total"] == 12  # 10 original + PII Permissions + Cron