"""Model provider abstraction for The Jarvice.

Supports multiple LLM providers with a unified interface:
- Ollama (local, default)
- OpenAI (cloud)
- Anthropic (cloud)

Each provider handles its own API format, auth, and error handling.
Falls back to the next provider in the chain on failure.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Data Classes ──────────────────────────────────────────────────────────


class ProviderType(str, Enum):
    """Supported model provider types."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class SummarizeResult:
    """Result of a summarization call."""

    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_ms: float = 0.0
    fallback_used: bool = False
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    provider: ProviderType = ProviderType.OLLAMA
    model: str = "qwen3:14b"
    system_prompt: str = ""
    api_key_service: str = ""  # Keychain service name for cloud providers
    endpoint: str = ""  # Custom endpoint override
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_seconds: int = 120


# ── Audit Log ──────────────────────────────────────────────────────────────

DEFAULT_AUDIT_LOG = Path("~/.the-jarvice/audit.log")


def log_to_audit(
    action: str,
    provider: str,
    model: str,
    items: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    green_path: str = "",
    error: str = "",
    audit_log: Path = DEFAULT_AUDIT_LOG,
) -> None:
    """Append an entry to the audit log."""
    audit_log = Path(audit_log).expanduser()
    audit_log.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "provider": provider,
        "model": model,
        "items": items,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }
    if green_path:
        entry["green_path"] = green_path
    if error:
        entry["error"] = error

    with open(audit_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Base Provider ──────────────────────────────────────────────────────────


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    name: str = "unknown"

    @abstractmethod
    def summarize(self, text: str, system_prompt: str = "") -> SummarizeResult:
        """Summarize text using the model provider."""

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test connectivity to the provider.

        Returns:
            Tuple of (success, message).
        """


# ── Ollama Provider ────────────────────────────────────────────────────────


class OllamaProvider(ModelProvider):
    """Local Ollama provider (default)."""

    name = "ollama"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.host = config.endpoint or "http://localhost:11434"

    def summarize(self, text: str, system_prompt: str = "") -> SummarizeResult:
        """Summarize text using Ollama API."""
        import requests

        start = time.time()
        prompt = text
        if system_prompt:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
            }
        else:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
            }

        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            # Ollama returns the response in the "response" field
            # It may send multiple JSON objects (streaming), take the last complete one
            if isinstance(data, list):
                data = data[-1]

            summary = data.get("response", "")
            if not summary and isinstance(data, str):
                # Try parsing as streaming response
                for line in data.strip().split("\n"):
                    try:
                        obj = json.loads(line)
                        if obj.get("response"):
                            summary = obj["response"]
                    except json.JSONDecodeError:
                        continue

            elapsed = (time.time() - start) * 1000

            return SummarizeResult(
                text=summary,
                provider=self.name,
                model=self.config.model,
                tokens_in=data.get("prompt_eval_count", 0),
                tokens_out=data.get("eval_count", 0),
                elapsed_ms=elapsed,
            )

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out (%ds)", self.config.timeout_seconds)
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=f"Timeout after {self.config.timeout_seconds}s",
            )
        except requests.exceptions.ConnectionError:
            logger.error("Ollama not reachable at %s", self.host)
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=f"Ollama not reachable at {self.host}",
            )
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=str(exc),
            )

    def test_connection(self) -> tuple[bool, str]:
        """Test Ollama connectivity."""
        import requests

        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                return True, f"Ollama running ({len(models)} models)"
            return False, f"Ollama returned status {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot reach Ollama at {self.host}"
        except Exception as exc:
            return False, f"Ollama error: {exc}"


# ── OpenAI Provider ────────────────────────────────────────────────────────


class OpenAIProvider(ModelProvider):
    """OpenAI API provider (cloud)."""

    name = "openai"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        """Resolve API key from keyring or env var."""
        if self.config.api_key_service:
            from the_jarvice.core.keyring_utils import get_credential

            key = get_credential(self.config.api_key_service, "api_key")
            if key:
                return key

        # Fallback to env var
        import os

        return os.environ.get("OPENAI_API_KEY", "")

    def summarize(self, text: str, system_prompt: str = "") -> SummarizeResult:
        """Summarize text using OpenAI API."""
        import requests

        start = time.time()

        if not self.api_key:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error="No API key found (set OPENAI_API_KEY or store in Keychain)",
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": text})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        endpoint = self.config.endpoint or "https://api.openai.com/v1/chat/completions"

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            summary = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            elapsed = (time.time() - start) * 1000

            # Audit log
            log_to_audit(
                action="summarize",
                provider=self.name,
                model=self.config.model,
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )

            return SummarizeResult(
                text=summary,
                provider=self.name,
                model=self.config.model,
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
                elapsed_ms=elapsed,
            )

        except requests.exceptions.Timeout:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=f"Timeout after {self.config.timeout_seconds}s",
            )
        except requests.exceptions.ConnectionError:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error="Cannot reach OpenAI API",
            )
        except Exception as exc:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=str(exc),
            )

    def test_connection(self) -> tuple[bool, str]:
        """Test OpenAI API connectivity."""
        if not self.api_key:
            return False, "No API key (set OPENAI_API_KEY or store in Keychain)"
        import requests

        try:
            resp = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "OpenAI API reachable"
            return False, f"OpenAI API returned status {resp.status_code}"
        except Exception as exc:
            return False, f"OpenAI API error: {exc}"


# ── Anthropic Provider ─────────────────────────────────────────────────────


class AnthropicProvider(ModelProvider):
    """Anthropic API provider (cloud)."""

    name = "anthropic"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        """Resolve API key from keyring or env var."""
        if self.config.api_key_service:
            from the_jarvice.core.keyring_utils import get_credential

            key = get_credential(self.config.api_key_service, "api_key")
            if key:
                return key

        import os

        return os.environ.get("ANTHROPIC_API_KEY", "")

    def summarize(self, text: str, system_prompt: str = "") -> SummarizeResult:
        """Summarize text using Anthropic API."""
        import requests

        start = time.time()

        if not self.api_key:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error="No API key found (set ANTHROPIC_API_KEY or store in Keychain)",
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": text}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        endpoint = self.config.endpoint or "https://api.anthropic.com/v1/messages"

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            summary = data["content"][0]["text"]
            usage = data.get("usage", {})

            elapsed = (time.time() - start) * 1000

            log_to_audit(
                action="summarize",
                provider=self.name,
                model=self.config.model,
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
            )

            return SummarizeResult(
                text=summary,
                provider=self.name,
                model=self.config.model,
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
                elapsed_ms=elapsed,
            )

        except requests.exceptions.Timeout:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=f"Timeout after {self.config.timeout_seconds}s",
            )
        except requests.exceptions.ConnectionError:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error="Cannot reach Anthropic API",
            )
        except Exception as exc:
            return SummarizeResult(
                text="",
                provider=self.name,
                model=self.config.model,
                error=str(exc),
            )

    def test_connection(self) -> tuple[bool, str]:
        """Test Anthropic API connectivity."""
        if not self.api_key:
            return False, "No API key (set ANTHROPIC_API_KEY or store in Keychain)"
        # Anthropic doesn't have a simple health endpoint, test with a minimal request
        return True, "Anthropic API key configured (no health endpoint available)"


# ── Provider Factory ───────────────────────────────────────────────────────


def create_provider(config: ProviderConfig) -> ModelProvider:
    """Create a model provider instance from configuration.

    Args:
        config: Provider configuration.

    Returns:
        ModelProvider instance.

    Raises:
        ValueError: If provider type is unknown.
    """
    if config.provider == ProviderType.OLLAMA:
        return OllamaProvider(config)
    elif config.provider == ProviderType.OPENAI:
        return OpenAIProvider(config)
    elif config.provider == ProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {config.provider}")


def create_provider_chain(
    primary: ProviderConfig,
    fallbacks: list[ProviderConfig] | None = None,
) -> list[ModelProvider]:
    """Create a chain of providers with fallback.

    Args:
        primary: Primary provider configuration.
        fallbacks: Optional list of fallback provider configurations.

    Returns:
        List of ModelProvider instances in priority order.
    """
    chain = [create_provider(primary)]
    if fallbacks:
        for fb in fallbacks:
            chain.append(create_provider(fb))
    return chain


def summarize_with_fallback(
    text: str,
    providers: list[ModelProvider],
    system_prompt: str = "",
) -> SummarizeResult:
    """Summarize text with fallback to next provider on failure.

    Args:
        text: Text to summarize.
        providers: List of providers in priority order.
        system_prompt: Optional system prompt.

    Returns:
        SummarizeResult from the first successful provider.
    """
    last_error = ""

    for i, provider in enumerate(providers):
        result = provider.summarize(text, system_prompt)

        if result.text and not result.error:
            if i > 0:
                logger.info(
                    "Successfully used fallback provider %s after %s",
                    provider.name,
                    providers[0].name,
                )
                result.fallback_used = True
            return result

        last_error = result.error or "Empty response"
        logger.warning(
            "Provider %s failed: %s, trying next fallback",
            provider.name,
            last_error,
        )

    # All providers failed
    return SummarizeResult(
        text="",
        provider=providers[0].name if providers else "none",
        model="",
        error=f"All providers failed. Last error: {last_error}",
    )