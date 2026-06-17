"""The Jarvice — State manager for cursor tracking."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path("~/.the-jarvice/state.json")


class StateManager:
    """Manages cursor tracking for scrapers via state.json.

    State file format::

        {
            "version": 1,
            "scrapers": {
                "exchange": { "last_scrape": "2026-05-20T14:30:00+03:00" },
                "teams": { "last_scrape": "2026-05-20T14:30:00+03:00" }
            },
            "last_run": "2026-05-20T14:30:00+03:00"
        }

    All timestamps are stored as ISO 8601 strings.
    """

    def __init__(self, state_file: Path = DEFAULT_STATE_PATH) -> None:
        self.state_file = Path(state_file).expanduser()
        self._state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load state from disk, returning empty default if missing."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load state file %s: %s — starting fresh", self.state_file, exc)
        return {"version": 1, "scrapers": {}, "last_run": None}

    def save(self) -> None:
        """Persist current state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self._state, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("State saved to %s", self.state_file)

    # ── Cursor operations ───────────────────────────────────────────────

    def get_cursor(self, scraper_name: str) -> Optional[datetime]:
        """Get last scrape timestamp for a scraper.

        Args:
            scraper_name: Identifier like "exchange" or "teams".

        Returns:
            Last scrape datetime, or None if never scraped.
        """
        ts = self._state.get("scrapers", {}).get(scraper_name, {}).get("last_scrape")
        if ts is None:
            return None
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            logger.warning("Invalid timestamp in state for %s: %s", scraper_name, ts)
            return None

    def set_cursor(self, scraper_name: str, timestamp: datetime) -> None:
        """Update last scrape timestamp for a scraper.

        Also updates the global last_run timestamp.

        Args:
            scraper_name: Identifier like "exchange" or "teams".
            timestamp: The datetime to record.
        """
        if "scrapers" not in self._state:
            self._state["scrapers"] = {}
        if scraper_name not in self._state["scrapers"]:
            self._state["scrapers"][scraper_name] = {}

        self._state["scrapers"][scraper_name]["last_scrape"] = timestamp.isoformat()
        self._state["last_run"] = datetime.now().isoformat()
        self.save()

    # ── Metadata operations ──────────────────────────────────────────────

    def get_last_run(self) -> Optional[datetime]:
        """Get the timestamp of the last pipeline run (any scraper)."""
        ts = self._state.get("last_run")
        if ts is None:
            return None
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            logger.warning("Invalid last_run timestamp: %s", ts)
            return None

    def get_scraper_meta(self, scraper_name: str, key: str) -> Optional[Any]:
        """Get arbitrary metadata for a scraper."""
        return self._state.get("scrapers", {}).get(scraper_name, {}).get(key)

    def set_scraper_meta(self, scraper_name: str, key: str, value: Any) -> None:
        """Set arbitrary metadata for a scraper."""
        if "scrapers" not in self._state:
            self._state["scrapers"] = {}
        if scraper_name not in self._state["scrapers"]:
            self._state["scrapers"][scraper_name] = {}
        self._state["scrapers"][scraper_name][key] = value
        self.save()

    def get_scraper_error_count(self, scraper_name: str) -> int:
        """Get consecutive error count for a scraper."""
        return self.get_scraper_meta(scraper_name, "error_count") or 0

    def increment_error_count(self, scraper_name: str) -> int:
        """Increment and return the consecutive error count for a scraper."""
        count = self.get_scraper_error_count(scraper_name) + 1
        self.set_scraper_meta(scraper_name, "error_count", count)
        return count

    def reset_error_count(self, scraper_name: str) -> None:
        """Reset consecutive error count for a scraper (after success)."""
        self.set_scraper_meta(scraper_name, "error_count", 0)

    # ── Reset ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all state (useful for testing or --reset flag)."""
        self._state = {"version": 1, "scrapers": {}, "last_run": None}
        self.save()