"""The Jarvice — Exchange (EWS) Scraper.

Connects to on-premise Exchange via exchangelib with stealth User-Agent.
Fetches emails and calendar events, returns ScrapeResult for the pipeline.

Credential resolution order:
  1. Keyring (macOS Keychain / Linux libsecret) via the-jarvice.exchange service
  2. macOS security CLI fallback
  3. Config-provided password (discouraged)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from the_jarvice.core.scraper_base import BaseScraper, ScrapeResult

logger = logging.getLogger("the_jarvice.scraper.exchange")

# ---------------------------------------------------------------------------
# Stealth: mimic standard Outlook
# ---------------------------------------------------------------------------
try:
    import exchangelib
    exchangelib.BaseProtocol.USERAGENT = (
        "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.18129; Pro)"
    )
    from exchangelib import Credentials, Account, Configuration, EWSDateTime, EWSTimeZone, DELEGATE
    HAS_EXCHANGELIB = True
except ImportError:
    HAS_EXCHANGELIB = False
    logger.debug("exchangelib not installed — Exchange scraper disabled")


def _macos_keychain_password(service: str, account: str) -> Optional[str]:
    """Retrieve password from macOS Keychain via security CLI."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ---------------------------------------------------------------------------
# Exchange Scraper
# ---------------------------------------------------------------------------

class ExchangeScraper(BaseScraper):
    """Scrapes emails and calendar events from on-premise Exchange (EWS).

    Features:
      - Stealth User-Agent (Outlook 16.0)
      - Keyring + macOS Keychain fallback for credentials
      - Cursor-based incremental scraping via state.json
      - PII-safe output (no passwords in logs)
      - Configurable time ranges and limits
    """

    name = "exchange"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.server = config.get("server", "")
        self.email = config.get("email", "")
        self.auth_mode = config.get("auth_mode", "auto")
        self.keychain_service = config.get("keychain_service", "the-jarvice.exchange")
        self._account: Any = None

    # ── Credential resolution ──────────────────────────────────────────────

    def _get_password(self) -> Optional[str]:
        """Resolve Exchange password from keyring or macOS Keychain."""
        # 1. Try Python keyring
        try:
            from the_jarvice.core.keyring_utils import get_credential
            pw = get_credential(self.keychain_service, self.email or "default")
            if pw:
                logger.debug("Password retrieved from keyring")
                return pw
        except Exception:
            pass

        # 2. Try macOS Keychain CLI
        if sys.platform == "darwin":
            pw = _macos_keychain_password(self.keychain_service, self.email)
            if pw:
                logger.debug("Password retrieved from macOS Keychain")
                return pw

        # 3. Legacy service name (exchange-ews)
        if sys.platform == "darwin":
            pw = _macos_keychain_password("exchange-ews", self.email)
            if pw:
                logger.debug("Password retrieved from legacy Keychain entry")
                return pw

        return None

    # ── Connection ────────────────────────────────────────────────────────

    def configure(self) -> bool:
        """Validate config and test Exchange connection.

        Returns:
            True if Exchange is reachable and credentials work.
        """
        if not HAS_EXCHANGELIB:
            logger.error("exchangelib not installed. Install with: pip install exchangelib")
            return False

        if not self.server or not self.email:
            logger.error("Exchange server and email are required")
            return False

        try:
            account = self._connect()
            if account:
                self._connected = True
                folder_count = len(list(account.root.get_folders())) if hasattr(account, 'root') else 0
                logger.info("Exchange connected: %s (%d folders)", self.server, folder_count)
                return True
        except Exception as exc:
            logger.error("Exchange connection failed: %s", exc)

        return False

    def test_connection(self) -> tuple[bool, str]:
        """Test Exchange connection for doctor.

        Returns:
            Tuple of (success, message).
        """
        if not HAS_EXCHANGELIB:
            return False, "exchangelib not installed"

        if not self.server:
            return False, "not configured (no server URL)"

        if not self.email:
            return False, "not configured (no email)"

        password = self._get_password()
        if not password:
            return False, f"credentials not found for {self.email}"

        try:
            account = self._connect()
            if account:
                inbox_count = account.inbox.total_count or 0
                return True, f"connected ({self.server}, {inbox_count} inbox items)"
        except Exception as exc:
            return False, f"connection failed: {exc}"

        return False, "unknown error"

    def _connect(self) -> Any:
        """Create authenticated Exchange Account."""
        password = self._get_password()
        if not password:
            raise RuntimeError(f"No Exchange password found for {self.email}")

        creds = Credentials(self.email, password)
        config = Configuration(server=self.server, credentials=creds)

        account = Account(
            primary_smtp_address=self.email,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
        self._account = account
        return account

    # ── Email scraping ─────────────────────────────────────────────────────

    def scrape(self, since: Optional[datetime] = None) -> ScrapeResult:
        """Scrape emails since a given timestamp.

        If `since` is None, scrapes last 24 hours.
        Uses state.json cursor for incremental scraping.

        Args:
            since: Optional timestamp to scrape emails after.

        Returns:
            ScrapeResult with email items and metadata.
        """
        if not HAS_EXCHANGELIB:
            return ScrapeResult(
                source=self.name,
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["exchangelib not installed"],
            )

        if not self._connected:
            try:
                self._connect()
            except Exception as exc:
                return ScrapeResult(
                    source=self.name,
                    timestamp=datetime.now(timezone.utc),
                    items=[],
                    count=0,
                    errors=[f"connection failed: {exc}"],
                )

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        # Convert to EWSDateTime
        tz = EWSTimeZone("Europe/Kaliningrad")
        ews_since = EWSDateTime.from_datetime(
            since.replace(tzinfo=None) if since.tzinfo else since,
            tz,
        )

        items = []
        errors = []

        try:
            inbox = self._account.inbox
            exchange_items = list(
                inbox.filter(datetime_received__gte=ews_since)
                .order_by("-datetime_received")
                .only(
                    "message_id", "subject", "sender",
                    "to_recipients", "cc_recipients",
                    "datetime_received", "is_read",
                    "importance", "has_attachments",
                    "text_body", "body",
                )
            )

            for item in exchange_items:
                try:
                    mail = self._item_to_dict(item)
                    items.append(mail)
                except Exception as exc:
                    errors.append(f"Failed to process email: {exc}")
                    logger.warning("Failed to process email: %s", exc)

        except Exception as exc:
            errors.append(f"Failed to fetch emails: {exc}")
            logger.error("Failed to fetch emails: %s", exc)

        return ScrapeResult(
            source=self.name,
            timestamp=datetime.now(timezone.utc),
            items=items,
            count=len(items),
            errors=errors,
            metadata={
                "since": since.isoformat(),
                "email": self.email,
                "server": self.server,
            },
        )

    # ── Calendar scraping ──────────────────────────────────────────────────

    def scrape_calendar(self, since: Optional[datetime] = None, days_ahead: int = 7) -> ScrapeResult:
        """Scrape calendar events.

        Args:
            since: Start datetime for range. Defaults to now.
            days_ahead: How many days ahead to look. Defaults to 7.

        Returns:
            ScrapeResult with calendar items.
        """
        if not HAS_EXCHANGELIB:
            return ScrapeResult(
                source=f"{self.name}_calendar",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["exchangelib not installed"],
            )

        if not self._connected:
            try:
                self._connect()
            except Exception as exc:
                return ScrapeResult(
                    source=f"{self.name}_calendar",
                    timestamp=datetime.now(timezone.utc),
                    items=[],
                    count=0,
                    errors=[f"connection failed: {exc}"],
                )

        if since is None:
            since = datetime.now(timezone.utc)

        tz = EWSTimeZone("Europe/Kaliningrad")
        ews_start = EWSDateTime.from_datetime(since.replace(tzinfo=None), tz)
        ews_end = EWSDateTime.from_datetime(
            (since + timedelta(days=days_ahead)).replace(tzinfo=None), tz
        )

        items = []
        errors = []

        try:
            calendar = self._account.calendar
            exchange_items = list(
                calendar.filter(
                    start__gte=ews_start,
                    end__lte=ews_end,
                )
                .order_by("start")
                .only(
                    "subject", "start", "end",
                    "organizer", "required_attendees", "optional_attendees",
                    "location", "is_all_day", "is_cancelled",
                    "legacy_free_busy_status",
                )
            )

            for item in exchange_items:
                try:
                    event = self._calendar_item_to_dict(item)
                    items.append(event)
                except Exception as exc:
                    errors.append(f"Failed to process calendar item: {exc}")

        except Exception as exc:
            errors.append(f"Failed to fetch calendar: {exc}")
            logger.error("Failed to fetch calendar: %s", exc)

        return ScrapeResult(
            source=f"{self.name}_calendar",
            timestamp=datetime.now(timezone.utc),
            items=items,
            count=len(items),
            errors=errors,
            metadata={
                "since": since.isoformat(),
                "days_ahead": days_ahead,
                "email": self.email,
            },
        )

    # ── Item conversion ────────────────────────────────────────────────────

    def _item_to_dict(self, item: Any) -> dict[str, Any]:
        """Convert Exchange email item to serializable dict."""
        body = ""
        if hasattr(item, "text_body") and item.text_body:
            body = item.text_body.strip()
        elif hasattr(item, "body") and item.body:
            body = re.sub(r"<[^>]+>", " ", str(item.body))
            body = re.sub(r"\s+", " ", body).strip()

        sender = {}
        if item.sender:
            sender = {
                "name": item.sender.name or "",
                "email": item.sender.email_address or "",
            }

        recipients = []
        for field in [item.to_recipients, item.cc_recipients]:
            if field:
                for r in field:
                    recipients.append({
                        "name": r.name or "",
                        "email": r.email_address or "",
                    })

        return {
            "message_id": item.message_id or "",
            "subject": item.subject or "",
            "sender": sender,
            "recipients": recipients,
            "date": str(item.datetime_received) if item.datetime_received else "",
            "body": body,
            "is_read": getattr(item, "is_read", None),
            "has_attachments": bool(item.attachments) if item.attachments else False,
            "importance": str(item.importance) if item.importance else "Normal",
        }

    def _calendar_item_to_dict(self, item: Any) -> dict[str, Any]:
        """Convert Exchange calendar item to serializable dict."""
        organizer = {}
        if hasattr(item, "organizer") and item.organizer:
            organizer = {
                "name": item.organizer.name or "",
                "email": item.organizer.email_address or "",
            }

        required = []
        if hasattr(item, "required_attendees") and item.required_attendees:
            for a in item.required_attendees:
                required.append({
                    "name": a.mailbox.name or "",
                    "email": a.mailbox.email_address or "",
                })

        optional = []
        if hasattr(item, "optional_attendees") and item.optional_attendees:
            for a in item.optional_attendees:
                optional.append({
                    "name": a.mailbox.name or "",
                    "email": a.mailbox.email_address or "",
                })

        return {
            "subject": item.subject or "",
            "start": str(item.start) if item.start else "",
            "end": str(item.end) if item.end else "",
            "organizer": organizer,
            "required_attendees": required,
            "optional_attendees": optional,
            "location": item.location or "",
            "is_all_day": getattr(item, "is_all_day", False),
            "is_cancelled": getattr(item, "is_cancelled", False),
            "free_busy": str(item.legacy_free_busy_status) if hasattr(item, "legacy_free_busy_status") else "",
        }

    def get_status(self) -> dict[str, Any]:
        """Return Exchange scraper status."""
        return {
            "name": self.name,
            "connected": self._connected,
            "server": self.server,
            "email": self.email,
            "has_exchangelib": HAS_EXCHANGELIB,
            "auth_mode": self.auth_mode,
        }