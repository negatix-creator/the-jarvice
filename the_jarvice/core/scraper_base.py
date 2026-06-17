"""The Jarvice — BaseScraper ABC and ScrapeResult dataclass."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Standardized output from any scraper.

    Attributes:
        source: Scraper identifier ("exchange", "teams", etc.)
        timestamp: When the scrape was performed.
        items: Raw scraped data items (list of dicts).
        count: Number of items scraped.
        errors: List of error messages (non-fatal).
        metadata: Extra info (e.g. folder count, token TTL).
    """

    source: str
    timestamp: datetime
    items: list[dict[str, Any]]
    count: int
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self, output_dir: Path) -> Path:
        """Convert scraped data to markdown for memory/ dir.

        Creates a structured markdown file with timestamp header,
        source badge, and item details.

        Args:
            output_dir: Directory to write the markdown file.

        Returns:
            Path to the created markdown file.
        """
        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.source}_{self.timestamp.strftime('%Y-%m-%d_%H%M%S')}.md"
        filepath = output_dir / filename

        lines = [
            f"# {self.source.title()} Scrape — {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"- **Source:** {self.source}",
            f"- **Items:** {self.count}",
            f"- **Errors:** {len(self.errors)}" if self.errors else f"- **Errors:** 0",
        ]

        if self.metadata:
            lines.append("")
            lines.append("## Metadata")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}:** {value}")

        if self.errors:
            lines.append("")
            lines.append("## Errors")
            for err in self.errors:
                lines.append(f"- {err}")

        if self.items:
            lines.append("")
            lines.append("## Items")
            for i, item in enumerate(self.items, 1):
                lines.append("")
                lines.append(f"### Item {i}")
                for key, value in item.items():
                    # Truncate very long values
                    val_str = str(value)
                    if len(val_str) > 500:
                        val_str = val_str[:500] + "..."
                    lines.append(f"- **{key}:** {val_str}")

        lines.append("")
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown saved to %s", filepath)
        return filepath

    def to_json(self, output_dir: Path) -> Path:
        """Save raw data as JSON for data/ dir.

        Args:
            output_dir: Directory to write the JSON file.

        Returns:
            Path to the created JSON file.
        """
        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.source}_{self.timestamp.strftime('%Y-%m-%d_%H%M%S')}.json"
        filepath = output_dir / filename

        payload = {
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "count": self.count,
            "errors": self.errors,
            "metadata": self.metadata,
            "items": self.items,
        }

        filepath.write_text(
            json.dumps(payload, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("JSON saved to %s", filepath)
        return filepath


class BaseScraper(ABC):
    """Abstract base class for all data scrapers.

    Every scraper must implement:
    - configure(): Validate config and test connection.
    - test_connection(): Check if the data source is reachable.
    - scrape(): Fetch data since a given timestamp.

    The `name` attribute uniquely identifies the scraper (e.g. "exchange", "teams").
    """

    name: str = "base"

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize scraper with its config section.

        Args:
            config: The relevant section from JarviceConfig (e.g. config.exchange dict).
        """
        self.config = config
        self._connected = False

    @abstractmethod
    def configure(self) -> bool:
        """Interactive or config-driven setup.

        Validates configuration, tests connection, and stores credentials
        in keyring if needed.

        Returns:
            True if configured successfully, False otherwise.
        """
        ...

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test connection to the data source.

        Used by `the-jarvice doctor` to verify connectivity.

        Returns:
            Tuple of (success: bool, message: str).
        """
        ...

    @abstractmethod
    def scrape(self, since: Optional[datetime] = None) -> ScrapeResult:
        """Scrape data since given timestamp.

        If `since` is None, scrapes last 24 hours of data.
        Uses state.json for cursor tracking between runs.

        Args:
            since: Optional timestamp to scrape data after.

        Returns:
            ScrapeResult with scraped items and metadata.
        """
        ...

    def get_status(self) -> dict[str, Any]:
        """Return current scraper status for doctor.

        Default implementation returns basic info. Subclasses may override
        to provide more detail.
        """
        return {
            "name": self.name,
            "connected": self._connected,
            "last_scrape": None,
        }