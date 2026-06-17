"""Sprint 004 tests — Provider Abstraction, Context Scrubber, Audit Log."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Provider Abstraction ──────────────────────────────────────────────────


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_config(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType

        config = ProviderConfig()
        assert config.provider == ProviderType.OLLAMA
        assert config.model == "qwen3:14b"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 120

    def test_openai_config(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            model="gpt-4o",
            api_key_service="the-jarvice.openai",
        )
        assert config.provider == ProviderType.OPENAI
        assert config.model == "gpt-4o"

    def test_anthropic_config(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType

        config = ProviderConfig(
            provider=ProviderType.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key_service="the-jarvice.anthropic",
        )
        assert config.provider == ProviderType.ANTHROPIC


class TestProviderFactory:
    """Tests for create_provider and create_provider_chain."""

    def test_create_ollama_provider(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType, create_provider

        config = ProviderConfig(provider=ProviderType.OLLAMA)
        provider = create_provider(config)
        assert provider.name == "ollama"

    def test_create_openai_provider(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType, create_provider

        config = ProviderConfig(provider=ProviderType.OPENAI, model="gpt-4o")
        provider = create_provider(config)
        assert provider.name == "openai"

    def test_create_anthropic_provider(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType, create_provider

        config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        provider = create_provider(config)
        assert provider.name == "anthropic"

    def test_create_unknown_provider_raises(self):
        from the_jarvice.core.providers import ProviderConfig, create_provider

        config = ProviderConfig(provider="unknown")  # type: ignore
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider(config)

    def test_provider_chain(self):
        from the_jarvice.core.providers import ProviderConfig, ProviderType, create_provider_chain

        primary = ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b")
        fallback1 = ProviderConfig(provider=ProviderType.OPENAI, model="gpt-4o")
        fallback2 = ProviderConfig(provider=ProviderType.ANTHROPIC, model="claude-sonnet-4-20250514")

        chain = create_provider_chain(primary, [fallback1, fallback2])
        assert len(chain) == 3
        assert chain[0].name == "ollama"
        assert chain[1].name == "openai"
        assert chain[2].name == "anthropic"


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_summarize_success(self):
        from the_jarvice.core.providers import OllamaProvider, ProviderConfig, ProviderType

        config = ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b")
        provider = OllamaProvider(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Summary text here",
            "prompt_eval_count": 100,
            "eval_count": 50,
        }

        with patch("requests.post", return_value=mock_response):
            result = provider.summarize("Some text", "System prompt")
            assert result.text == "Summary text here"
            assert result.provider == "ollama"
            assert result.tokens_in == 100
            assert result.tokens_out == 50

    def test_summarize_timeout(self):
        from the_jarvice.core.providers import OllamaProvider, ProviderConfig, ProviderType

        config = ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b")
        provider = OllamaProvider(config)

        with patch("requests.post", side_effect=__import__("requests").exceptions.Timeout()):
            result = provider.summarize("Some text")
            assert result.error is not None
            assert "Timeout" in result.error

    def test_summarize_connection_error(self):
        from the_jarvice.core.providers import OllamaProvider, ProviderConfig, ProviderType

        config = ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b")
        provider = OllamaProvider(config)

        with patch("requests.post", side_effect=__import__("requests").exceptions.ConnectionError()):
            result = provider.summarize("Some text")
            assert result.error is not None
            assert "not reachable" in result.error

    def test_test_connection_success(self):
        from the_jarvice.core.providers import OllamaProvider, ProviderConfig, ProviderType

        config = ProviderConfig(provider=ProviderType.OLLAMA, model="qwen3:14b")
        provider = OllamaProvider(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "qwen3:14b"}]}

        with patch("requests.get", return_value=mock_response):
            ok, msg = provider.test_connection()
            assert ok is True
            assert "1 models" in msg


class TestSummarizeWithFallback:
    """Tests for summarize_with_fallback."""

    def test_primary_succeeds(self):
        from the_jarvice.core.providers import (
            SummarizeResult,
            summarize_with_fallback,
        )

        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.summarize.return_value = SummarizeResult(
            text="Summary", provider="mock", model="test"
        )

        result = summarize_with_fallback("text", [mock_provider])
        assert result.text == "Summary"
        assert result.fallback_used is False

    def test_fallback_on_primary_failure(self):
        from the_jarvice.core.providers import (
            SummarizeResult,
            summarize_with_fallback,
        )

        failing = MagicMock()
        failing.name = "primary"
        failing.summarize.return_value = SummarizeResult(
            text="", provider="primary", model="test", error="Timeout"
        )

        succeeding = MagicMock()
        succeeding.name = "fallback"
        succeeding.summarize.return_value = SummarizeResult(
            text="Fallback summary", provider="fallback", model="test2"
        )

        result = summarize_with_fallback("text", [failing, succeeding])
        assert result.text == "Fallback summary"
        assert result.fallback_used is True

    def test_all_providers_fail(self):
        from the_jarvice.core.providers import (
            SummarizeResult,
            summarize_with_fallback,
        )

        p1 = MagicMock()
        p1.name = "p1"
        p1.summarize.return_value = SummarizeResult(
            text="", provider="p1", model="m1", error="Timeout"
        )

        p2 = MagicMock()
        p2.name = "p2"
        p2.summarize.return_value = SummarizeResult(
            text="", provider="p2", model="m2", error="Connection error"
        )

        result = summarize_with_fallback("text", [p1, p2])
        assert result.text == ""
        assert "All providers failed" in result.error


# ── Context Scrubber ──────────────────────────────────────────────────────


class TestContextScrubber:
    """Tests for context scrubbing pass."""

    def test_scrub_job_title_org(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "CFO [ORG_1] отметил рост выручки"
        result = scrub_for_cloud(text)
        assert "[ORG_1]" not in result
        assert "[ROLE]" in result

    def test_scrub_russian_job_title(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "Директор [ORG_1] представил план"
        result = scrub_for_cloud(text)
        assert "[ROLE]" in result

    def test_scrub_russian_job_title_with_department(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        # "Директор по ИТ [ORG_1]" pattern
        text = "директор по ИТ [ORG_1] представил план"
        result = scrub_for_cloud(text)
        assert "[ROLE]" in result

    def test_scrub_room_names(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "Встреча в комната B-204"
        result = scrub_for_cloud(text)
        assert "[МЕСТО]" in result

    def test_scrub_small_team(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "команда из 3 человек работает над проектом"
        result = scrub_for_cloud(text)
        assert "[МАЛАЯ_ГРУППА]" in result

    def test_strict_mode_removes_budgets(self):
        from the_jarvice.core.context_scrubber import ScrubLevel, scrub_for_cloud

        text = "Бюджет составил 5 млн рублей"
        result = scrub_for_cloud(text, level=ScrubLevel.STRICT)
        assert "[СУММА]" in result

    def test_standard_mode_keeps_budgets(self):
        from the_jarvice.core.context_scrubber import ScrubLevel, scrub_for_cloud

        text = "Бюджет составил 5 млн рублей"
        result = scrub_for_cloud(text, level=ScrubLevel.STANDARD)
        assert "5 млн рублей" in result

    def test_strict_mode_removes_dates(self):
        from the_jarvice.core.context_scrubber import ScrubLevel, scrub_for_cloud

        text = "Встреча 15 января в 10:30"
        result = scrub_for_cloud(text, level=ScrubLevel.STRICT)
        assert "[ДАТА]" in result
        assert "[ВРЕМЯ]" in result

    def test_custom_patterns(self):
        import re

        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "Проект АЛЬФА-2024 запущен"
        pattern = re.compile(r"АЛЬФА-\d{4}")
        result = scrub_for_cloud(text, custom_patterns=[pattern])
        assert "[УДАЛЕНО]" in result

    def test_no_scrubbing_needed(self):
        from the_jarvice.core.context_scrubber import scrub_for_cloud

        text = "[PERSON_1] написал что встреча прошла хорошо"
        result = scrub_for_cloud(text)
        assert result == text  # No re-identification vectors


class TestReidentificationRisk:
    """Tests for risk estimation."""

    def test_estimate_risk_clean(self):
        from the_jarvice.core.context_scrubber import estimate_reidentification_risk

        text = "[PERSON_1] написал что встреча прошла хорошо"
        risks = estimate_reidentification_risk(text)
        assert risks["job_title_org"] == 0
        assert risks["budget_figures"] == 0

    def test_estimate_risk_with_vectors(self):
        from the_jarvice.core.context_scrubber import estimate_reidentification_risk

        text = "CFO [ORG_1] сообщил что бюджет 10 млн рублей"
        risks = estimate_reidentification_risk(text)
        assert risks["job_title_org"] >= 1
        assert risks["budget_figures"] >= 1


# ── Audit Log ──────────────────────────────────────────────────────────────


class TestAuditLog:
    """Tests for audit logging."""

    def test_log_to_audit(self):
        from the_jarvice.core.providers import log_to_audit

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            audit_path = Path(f.name)

        try:
            log_to_audit(
                action="summarize",
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                items=5,
                tokens_in=1200,
                tokens_out=300,
                audit_log=audit_path,
            )

            content = audit_path.read_text()
            entry = json.loads(content.strip())
            assert entry["action"] == "summarize"
            assert entry["provider"] == "anthropic"
            assert entry["tokens_in"] == 1200
            assert entry["tokens_out"] == 300
            assert "ts" in entry
        finally:
            audit_path.unlink(missing_ok=True)

    def test_log_to_audit_with_error(self):
        from the_jarvice.core.providers import log_to_audit

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            audit_path = Path(f.name)

        try:
            log_to_audit(
                action="summarize",
                provider="openai",
                model="gpt-4o",
                error="Timeout after 120s",
                audit_log=audit_path,
            )

            content = audit_path.read_text()
            entry = json.loads(content.strip())
            assert entry["error"] == "Timeout after 120s"
        finally:
            audit_path.unlink(missing_ok=True)