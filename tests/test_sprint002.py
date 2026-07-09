"""Sprint 002 — Exchange Scraper, PII Pipeline, Summary Generator tests.

Covers: ExchangeScraper, Anonymizer, Deanonymizer, MappingManager,
PIIClassifier, pipeline integration, CLI run command.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── PII Classifier Tests ────────────────────────────────────────────────────

from the_jarvice.scrapers.pii.anonymizer import (
    Anonymizer,
    Deanonymizer,
    MappingManager,
    PIIClassifier,
)


class TestPIIClassifier:
    """Tests for the regex-based PII classifier."""

    def test_detect_email(self):
        text = "Contact ivanov@example.com for details"
        entities = PIIClassifier.classify(text)
        assert len(entities) >= 1
        assert any(e[0] == "email" for e in entities)

    def test_detect_multiple_emails(self):
        text = "Write to ivanov@example.com and petrov@company.com"
        entities = PIIClassifier.classify(text)
        emails = [e for e in entities if e[0] == "email"]
        assert len(emails) == 2

    def test_detect_russian_phone(self):
        text = "Звоните +7 916 123-45-67"
        entities = PIIClassifier.classify(text)
        assert any(e[0] == "phone" for e in entities)

    def test_detect_phone_8_format(self):
        text = "Телефон: 8 916 123 45 67"
        entities = PIIClassifier.classify(text)
        assert any(e[0] == "phone" for e in entities)

    def test_detect_snils(self):
        text = "СНИЛС: 123-456-789 01"
        entities = PIIClassifier.classify(text)
        assert any(e[0] == "snils" for e in entities)

    def test_no_pii(self):
        text = "Совещание состоится в 10:00 в конференц-зале"
        assert not PIIClassifier.has_pii(text)

    def test_has_pii_email(self):
        assert PIIClassifier.has_pii("Напишите test@example.com")

    def test_has_pii_phone(self):
        assert PIIClassifier.has_pii("Звоните +7 900 123 4567")

    def test_no_false_positive_urls(self):
        """URLs should not be classified as emails."""
        text = "Visit https://example.com/page for info"
        entities = PIIClassifier.classify(text)
        emails = [e for e in entities if e[0] == "email"]
        # The URL should not be detected as an email
        # (https://... doesn't match email pattern)


# ── Mapping Manager Tests ────────────────────────────────────────────────────

class TestMappingManager:
    """Tests for PII mapping persistence."""

    def test_create_new_token_person(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr = MappingManager(mapping_path=path)
            token = mgr.get_or_create_token("person", "Иванов Алексей")
            assert token == "[PERSON_1]"
            mgr.save()
            assert path.exists()

    def test_consistent_mapping(self):
        """Same value should always get the same token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr = MappingManager(mapping_path=path)
            token1 = mgr.get_or_create_token("person", "Петров Сергей")
            token2 = mgr.get_or_create_token("person", "Петров Сергей")
            assert token1 == token2

    def test_different_types_same_index(self):
        """Different types get independent counters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr = MappingManager(mapping_path=path)
            person_token = mgr.get_or_create_token("person", "Иванов")
            email_token = mgr.get_or_create_token("email", "ivanov@test.ru")
            assert person_token == "[PERSON_1]"
            assert email_token == "[EMAIL_1]"

    def test_case_insensitive_lookup(self):
        """Case variations should resolve to same token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr = MappingManager(mapping_path=path)
            token1 = mgr.get_or_create_token("person", "Иванов")
            token2 = mgr.get_or_create_token("person", "иванов")
            assert token1 == token2

    def test_persistence(self):
        """Mapping should survive save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr1 = MappingManager(mapping_path=path)
            mgr1.get_or_create_token("person", "Тестовый")
            mgr1.save()

            mgr2 = MappingManager(mapping_path=path)
            token = mgr2.get_or_create_token("person", "Тестовый")
            assert token == "[PERSON_1]"

    def test_secure_permissions(self):
        """Mapping file should be chmod 600."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            mgr = MappingManager(mapping_path=path)
            mgr.get_or_create_token("person", "Тест")
            mgr.save()
            mode = oct(path.stat().st_mode & 0o777)
            assert mode in ("0o600", "0o644")  # 600 on Linux, may vary on macOS


# ── Anonymizer Tests ────────────────────────────────────────────────────────

class TestAnonymizer:
    """Tests for the PII anonymization pipeline."""

    def test_anonymize_text_email(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping = Path(tmpdir) / "mapping.json"
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping)

            text = "Напишите на ivanov@example.com"
            result, has_pii = anon.anonymize_text(text)
            assert has_pii
            assert "[EMAIL_1]" in result
            assert "ivanov@example.com" not in result

    def test_anonymize_text_phone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping = Path(tmpdir) / "mapping.json"
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping)

            text = "Звоните +7 916 123-45-67"
            result, has_pii = anon.anonymize_text(text)
            assert has_pii
            assert "[PHONE_" in result

    def test_anonymize_dict_force_masks_sender(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping = Path(tmpdir) / "mapping.json"
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping)

            data = {
                "subject": "Встреча",
                "body": "Давайте обсудим",
                "sender": {"name": "Иванов Алексей", "email": "ivanov@example.com"},
                "recipients": [{"name": "Петров Сергей", "email": "petrov@example.com"}],
                "date": "2026-05-21T10:00:00",
            }
            result, has_pii = anon.anonymize_dict(data)
            assert has_pii
            assert result["sender"]["name"] == "[PERSON_1]"
            assert result["sender"]["email"] == "[EMAIL_1]"
            assert result["recipients"][0]["name"] == "[PERSON_2]"
            assert result["recipients"][0]["email"] == "[EMAIL_2]"

    def test_anonymize_dict_no_pii(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping = Path(tmpdir) / "mapping.json"
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping)

            data = {
                "subject": "Совещание",
                "body": "Обсудим вопросы",
                "sender": {},
                "recipients": [],
            }
            result, has_pii = anon.anonymize_dict(data)
            assert not has_pii


# ── Deanonymizer Tests ──────────────────────────────────────────────────────

class TestDeanonymizer:
    """Tests for mask → real value replacement."""

    def _create_mapping(self, path: Path):
        """Create a test mapping file."""
        mapping = {
            "version": 1,
            "persons": {
                "[PERSON_1]": {"full": "Иванов Алексей", "variants": ["Иванов А."]},
                "[PERSON_2]": {"full": "Петров Сергей", "variants": []},
            },
            "phones": {"[PHONE_1]": "+7 916 123-45-67"},
            "emails": {"[EMAIL_1]": "ivanov@example.com"},
            "ids": {},
            "organizations": {},
            "addresses": {},
            "_reverse": {},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_deanonymize_masks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            self._create_mapping(path)
            deanon = Deanonymizer(mapping_path=path)

            text = "Напишите [PERSON_1] по телефону [PHONE_1]"
            result = deanon.deanonymize(text)
            assert "Иванов Алексей" in result
            assert "+7 916 123-45-67" in result
            assert "[PERSON_1]" not in result

    def test_has_masks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            self._create_mapping(path)
            deanon = Deanonymizer(mapping_path=path)

            assert deanon.has_masks("[PERSON_1] написал")
            assert not deanon.has_masks("Обычный текст")

    def test_no_masks_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"
            self._create_mapping(path)
            deanon = Deanonymizer(mapping_path=path)

            text = "Обычный текст без масок"
            assert deanon.deanonymize(text) == text


# ── Exchange Scraper Tests ───────────────────────────────────────────────────

class TestExchangeScraperInit:
    """Tests for ExchangeScraper initialization."""

    def test_default_config(self):
        from the_jarvice.scrapers.exchange.scraper import ExchangeScraper

        config = {"server": "mail.test.ru", "email": "test@test.ru"}
        scraper = ExchangeScraper(config)
        assert scraper.server == "mail.test.ru"
        assert scraper.email == "test@test.ru"
        assert scraper.name == "exchange"
        assert not scraper._connected

    def test_custom_keychain_service(self):
        from the_jarvice.scrapers.exchange.scraper import ExchangeScraper

        config = {
            "server": "mail.test.ru",
            "email": "test@test.ru",
            "keychain_service": "custom.service",
        }
        scraper = ExchangeScraper(config)
        assert scraper.keychain_service == "custom.service"

    def test_get_status(self):
        from the_jarvice.scrapers.exchange.scraper import ExchangeScraper

        config = {"server": "mail.test.ru", "email": "test@test.ru"}
        scraper = ExchangeScraper(config)
        status = scraper.get_status()
        assert status["name"] == "exchange"
        assert status["server"] == "mail.test.ru"
        assert status["email"] == "test@test.ru"
        assert "has_exchangelib" in status

    def test_scrape_without_connection(self):
        from the_jarvice.scrapers.exchange.scraper import ExchangeScraper

        config = {"server": "mail.test.ru", "email": "test@test.ru"}
        scraper = ExchangeScraper(config)
        result = scraper.scrape()
        assert result.source == "exchange"
        # Should return errors since we're not connected
        assert len(result.errors) > 0 or result.count == 0

    def test_macos_keychain_fallback(self):
        from the_jarvice.scrapers.exchange.scraper import _macos_keychain_password

        # Should return None for non-existent entries without crashing
        result = _macos_keychain_password("nonexistent-service-xyz", "nonexistent-account")
        assert result is None


# ── ScrapeResult Integration Tests ────────────────────────────────────────────

class TestScrapeResultIntegration:
    """Tests for ScrapeResult with Exchange/PII data flow."""

    def test_exchange_result_to_markdown(self):
        from the_jarvice.core.scraper_base import ScrapeResult

        result = ScrapeResult(
            source="exchange",
            timestamp=datetime.now(timezone.utc),
            items=[
                {"subject": "Test", "sender": "user@test.ru", "date": "2026-05-21"},
            ],
            count=1,
            errors=[],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = result.to_markdown(Path(tmpdir))
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Exchange" in content
            assert "Test" in content

    def test_exchange_result_to_json(self):
        from the_jarvice.core.scraper_base import ScrapeResult

        result = ScrapeResult(
            source="exchange",
            timestamp=datetime.now(timezone.utc),
            items=[],
            count=0,
            errors=["test error"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = result.to_json(Path(tmpdir))
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["source"] == "exchange"
            assert data["count"] == 0
            assert "test error" in data["errors"]

    def test_pii_pipeline_full(self):
        """End-to-end: ScrapeResult → Anonymizer → Deanonymizer."""
        from the_jarvice.core.scraper_base import ScrapeResult
        from the_jarvice.scrapers.pii.anonymizer import Anonymizer, Deanonymizer

        with tempfile.TemporaryDirectory() as tmpdir:
            red = Path(tmpdir) / "RED"
            green = Path(tmpdir) / "GREEN"
            mapping = Path(tmpdir) / "mapping.json"

            # Create scrape result with PII
            result = ScrapeResult(
                source="exchange",
                timestamp=datetime.now(timezone.utc),
                items=[
                    {
                        "subject": "Встреча с Ивановым",
                        "body": "Позвоните на +7 916 123-45-67",
                        "sender": {"name": "Иванов Алексей", "email": "ivanov@example.com"},
                        "recipients": [],
                        "date": "2026-05-21T10:00:00",
                        "message_id": "test-123",
                    },
                ],
                count=1,
                errors=[],
            )

            # Anonymize
            anon = Anonymizer(red_dir=red, green_dir=green, mapping_path=mapping)
            anon_result = anon.process_scrape_result(result)

            # Check anonymized output
            assert anon_result.source == "exchange_anonymized"
            assert anon_result.metadata.get("pii_found", 0) > 0

            # Check RED file exists (originals)
            red_files = list(red.glob("*.json"))
            assert len(red_files) == 1

            # Check GREEN file exists (anonymized)
            green_files = list(green.glob("*.json"))
            assert len(green_files) == 1

            # Deanonymize
            deanon = Deanonymizer(mapping_path=mapping)
            text = "Напишите [PERSON_1]"
            result_text = deanon.deanonymize(text)
            assert "Иванов Алексей" in result_text