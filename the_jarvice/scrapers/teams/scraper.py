"""The Jarvice — Teams Scraper (IC3 + Graph API stub).

Connects to Microsoft Teams via IC3 token (extracted from browser DevTools)
or Graph API (stub, not yet implemented).

IC3 token flow:
  1. User opens browser DevTools → Network → filter teams.microsoft.com
  2. Find Authorization: Bearer <token> header
  3. Copy token, store in Keychain via `the-jarvice configure --reauth teams`
  4. Token expires in 8-24 hours; scraper checks before each request

Graph API mode returns a clear error directing users to IC3 or waiting for v0.3.0.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from the_jarvice.core.scraper_base import BaseScraper, ScrapeResult

logger = logging.getLogger("the_jarvice.scraper.teams")

# ---------------------------------------------------------------------------
# Optional httpx import
# ---------------------------------------------------------------------------
try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    logger.debug("httpx not installed — Teams IC3 scraper will not work")

# ---------------------------------------------------------------------------
# IC3 API endpoints
# ---------------------------------------------------------------------------
IC3_CHAT_LIST_URL = (
    "https://teams.microsoft.com/api/csa/api/v1/teams/users/me/conversations"
)
IC3_CHAT_MESSAGES_URL = (
    "https://teams.microsoft.com/api/csa/api/v1/teams/users/me"
    "/conversations/{chat_id}/messages"
)
IC3_MEETINGS_URL = (
    "https://teams.microsoft.com/api/csa/api/v1/teams/users/me/meetings"
)

# Token validation endpoint (lightweight)
IC3_TOKEN_VALIDATE_URL = (
    "https://teams.microsoft.com/api/csa/api/v1/teams/users/me"
)


# ---------------------------------------------------------------------------
# Token utilities
# ---------------------------------------------------------------------------

def _is_token_expired(token: str) -> bool:
    """Check if a JWT token is expired.

    Decodes the payload (without verification) and checks the 'exp' claim.
    Returns True if the token is expired or cannot be decoded.
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return True

        # Decode payload (middle part), add padding if needed
        import base64

        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))

        exp = decoded.get("exp")
        if exp is None:
            return True

        # Add 60s buffer so we don't use a token that's about to expire
        return time.time() > (exp - 60)
    except Exception as exc:
        logger.warning("Failed to decode token for expiry check: %s", exc)
        return True


class _SenderIndex:
    """Deterministic per-sender pseudonymization.

    Assigns consistent [SENDER_1], [SENDER_2], etc. labels
    within a single scrape run so that the same person always
    gets the same mask, preserving conversation context.
    """
    def __init__(self) -> None:
        self._map: dict[str, str] = {}
        self._counter = 0

    def mask(self, name: str) -> str:
        """Return a consistent [SENDER_N] for the given name."""
        if not name or name.strip() == "":
            return "[SENDER_UNKNOWN]"
        key = name.strip().lower()
        if key not in self._map:
            self._counter += 1
            self._map[key] = f"[SENDER_{self._counter}]"
        return self._map[key]


# Module-level sender index for per-run consistency
_sender_index = _SenderIndex()


def _mask_sender_name(name: str) -> str:
    """Force-mask a sender display name for PII.

    Uses a per-run deterministic index so the same sender
    always gets the same [SENDER_N] label, preserving
    conversation context. The PII pipeline will later
    remap these to [PERSON_N] tokens.
    """
    return _sender_index.mask(name)


# ---------------------------------------------------------------------------
# Teams Scraper
# ---------------------------------------------------------------------------

class TeamsScraper(BaseScraper):
    """Microsoft Teams scraper using IC3 token authentication.

    Auth mode: ic3_token — uses a browser-extracted Bearer token
    for Teams IC3 API. Token expires in 8-24h. Requires httpx.
    """

    name = "teams"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.auth_mode = "ic3_token"  # Only IC3 token auth is supported
        if config.get("auth_mode", "ic3_token") == "graph_api":
            logger.error("Graph API auth mode is not yet implemented. Use ic3_token.")
            logger.info("Graph API will be available in a future release.")
        self.keychain_service = config.get("keychain_service", "the-jarvice.teams")
        self.scrape_interval_hours = config.get("scrape_interval_hours", 4)
        self.max_messages = config.get("max_messages", 200)
        self.include_transcripts = config.get("include_transcripts", True)
        self.request_delay_ms = config.get("request_delay_ms", 200)  # Delay between API calls
        self._token: Optional[str] = None
        self._connected = False
        self._last_scrape: Optional[datetime] = None

    # ── Token lifecycle ──────────────────────────────────────────────────

    def set_token_timestamp(self, state: "StateManager") -> None:
        """Record when the IC3 token was last set/refreshed."""
        state.set_scraper_meta("teams", "token_set_at", datetime.now(timezone.utc).isoformat())

    def get_token_age_hours(self, state: "StateManager") -> Optional[float]:
        """Get hours since token was last set, or None if unknown."""
        ts = state.get_scraper_meta("teams", "token_set_at")
        if ts is None:
            return None
        try:
            set_at = datetime.fromisoformat(ts)
            return (datetime.now(timezone.utc) - set_at).total_seconds() / 3600
        except (ValueError, TypeError):
            return None

    # ── Credential resolution ──────────────────────────────────────────────

    def _get_token(self) -> Optional[str]:
        """Resolve Teams IC3 token from keyring or env var."""
        # 1. Try keyring
        try:
            from the_jarvice.core.keyring_utils import get_credential

            token = get_credential(self.keychain_service, "ic3_token")
            if token:
                logger.debug("IC3 token retrieved from keyring")
                return token
        except Exception:
            pass

        # 2. Try environment variable
        import os

        env_token = os.environ.get("JARVICE_TEAMS_PASSWORD")
        if env_token:
            logger.debug("IC3 token retrieved from environment variable")
            return env_token

        return None

    # ── Connection ────────────────────────────────────────────────────────

    def configure(self) -> bool:
        """Validate Teams configuration and credentials.

        Checks token presence and expiry for IC3 mode.

        Returns:
            True if configuration is valid and connection possible.
        """
        if not HAS_HTTPX:
            logger.error("httpx not installed. Install with: pip install the-jarvice[teams]")
            return False

        token = self._get_token()
        if not token:
            logger.error("No IC3 token found. Run: the-jarvice configure --reauth teams")
            return False

        if _is_token_expired(token):
            logger.error("IC3 token is expired. Re-extract from browser DevTools.")
            return False

        self._token = token
        return True

    def test_connection(self) -> tuple[bool, str]:
        """Test Teams connectivity.

        Validates token by calling a lightweight API endpoint.

        Returns:
            Tuple of (success, message).
        """
        if not HAS_HTTPX:
            return False, "httpx not installed. Install with: pip install the-jarvice[teams]"

        token = self._get_token()
        if not token:
            return False, "No IC3 token found. Run: the-jarvice configure --reauth teams"

        if _is_token_expired(token):
            return False, "IC3 token expired. Re-extract from browser DevTools."

        # Test token by calling a lightweight endpoint
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    IC3_TOKEN_VALIDATE_URL,
                    headers=self._auth_headers(token),
                )
                if resp.status_code == 200:
                    self._connected = True
                    self._token = token
                    return True, "Teams connected (IC3 token valid)"
                elif resp.status_code == 401:
                    return False, "IC3 token rejected (expired or invalid). Re-extract from browser."
                elif resp.status_code == 429:
                    return True, "Teams API reachable (rate limited, but token valid)"
                else:
                    return False, f"Teams API returned status {resp.status_code}"
        except httpx.ConnectError:
            return False, "Cannot reach Teams API (network error)"
        except httpx.TimeoutException:
            return False, "Teams API timeout"
        except Exception as exc:
            return False, f"Teams connection error: {exc}"

    def _auth_headers(self, token: str) -> dict[str, str]:
        """Build authorization headers for IC3 API calls."""
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Teams/1.0",
            "Accept": "application/json",
        }

    # ── Scraping ──────────────────────────────────────────────────────────

    def scrape(self, since: Optional[datetime] = None) -> ScrapeResult:
        """Scrape Teams messages since last cursor.

        Fetches recent chats and messages via IC3 API.

        Args:
            since: Optional timestamp to scrape messages after.

        Returns:
            ScrapeResult with chat messages and/or meeting transcripts.
        """
        if not HAS_HTTPX:
            return ScrapeResult(
                source=self.name,
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["httpx not installed. Install with: pip install the-jarvice[teams]"],
            )

        token = self._token or self._get_token()
        if not token:
            return ScrapeResult(
                source=self.name,
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["No IC3 token found. Run: the-jarvice configure --reauth teams"],
            )

        if _is_token_expired(token):
            return ScrapeResult(
                source=self.name,
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["IC3 token expired. Re-extract from browser DevTools."],
            )

        self._token = token

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=self.scrape_interval_hours)

        all_items: list[dict[str, Any]] = []
        all_errors: list[str] = []

        # Scrape chats
        try:
            chat_result = self.scrape_chats(since=since)
            all_items.extend(chat_result.items)
            all_errors.extend(chat_result.errors)
        except Exception as exc:
            all_errors.append(f"Chat scraping failed: {exc}")
            logger.error("Chat scraping failed: %s", exc)

        # Scrape meetings
        if self.include_transcripts:
            try:
                meeting_result = self.scrape_meetings(since=since)
                all_items.extend(meeting_result.items)
                all_errors.extend(meeting_result.errors)
            except Exception as exc:
                all_errors.append(f"Meeting scraping failed: {exc}")
                logger.error("Meeting scraping failed: %s", exc)

        self._last_scrape = datetime.now(timezone.utc)
        self._connected = True

        return ScrapeResult(
            source=self.name,
            timestamp=datetime.now(timezone.utc),
            items=all_items,
            count=len(all_items),
            errors=all_errors,
            metadata={
                "since": since.isoformat(),
                "auth_mode": self.auth_mode,
                "chats_count": sum(1 for i in all_items if i.get("type") == "chat_message"),
                "meetings_count": sum(1 for i in all_items if i.get("type") == "meeting"),
            },
        )

    def scrape_chats(self, since: Optional[datetime] = None) -> ScrapeResult:
        """Scrape 1:1 and group chat messages.

        Args:
            since: Optional timestamp to filter messages after.

        Returns:
            ScrapeResult with chat message items.
        """
        if not HAS_HTTPX:
            return ScrapeResult(
                source=f"{self.name}_chats",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["httpx not installed"],
            )

        token = self._token or self._get_token()
        if not token or _is_token_expired(token):
            return ScrapeResult(
                source=f"{self.name}_chats",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["No valid IC3 token"],
            )

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=self.scrape_interval_hours)

        items: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            with httpx.Client(timeout=30.0) as client:
                # Step 1: Get chat list
                resp = self._request_with_retry(
                    client, "GET", IC3_CHAT_LIST_URL, token
                )
                if resp is None:
                    return ScrapeResult(
                        source=f"{self.name}_chats",
                        timestamp=datetime.now(timezone.utc),
                        items=[],
                        count=0,
                        errors=["Failed to fetch chat list (retries exhausted)"],
                    )

                if resp.status_code != 200:
                    errors.append(f"Chat list API returned {resp.status_code}")
                    return ScrapeResult(
                        source=f"{self.name}_chats",
                        timestamp=datetime.now(timezone.utc),
                        items=[],
                        count=0,
                        errors=errors,
                    )

                data = resp.json()
                chats = data if isinstance(data, list) else data.get("conversations", data.get("value", []))

                if not chats:
                    # Empty chat list is fine
                    return ScrapeResult(
                        source=f"{self.name}_chats",
                        timestamp=datetime.now(timezone.utc),
                        items=[],
                        count=0,
                        errors=[],
                        metadata={"chats_found": 0},
                    )

                # Step 2: Fetch messages from each chat (limit to avoid rate limits)
                max_chats = min(len(chats), 20)  # Safety limit
                message_count = 0

                for chat in chats[:max_chats]:
                    chat_id = chat.get("id") or chat.get("conversationId") or chat.get("chatId")
                    if not chat_id:
                        continue

                    chat_messages = self._fetch_chat_messages(client, token, chat_id, since)
                    if isinstance(chat_messages, list):
                        items.extend(chat_messages)
                        message_count += len(chat_messages)
                    elif isinstance(chat_messages, str):
                        errors.append(chat_messages)

                    # Rate limiting: delay between chat fetches
                    if self.request_delay_ms > 0:
                        time.sleep(self.request_delay_ms / 1000.0)

                    # Respect max_messages limit
                    if message_count >= self.max_messages:
                        break

        except httpx.ConnectError as exc:
            errors.append(f"Network error: {exc}")
        except httpx.TimeoutException as exc:
            errors.append(f"Timeout: {exc}")
        except Exception as exc:
            errors.append(f"Unexpected error: {exc}")
            logger.error("Chat scraping error: %s", exc)

        return ScrapeResult(
            source=f"{self.name}_chats",
            timestamp=datetime.now(timezone.utc),
            items=items[:self.max_messages],
            count=min(len(items), self.max_messages),
            errors=errors,
            metadata={"since": since.isoformat(), "chats_found": len(chats) if isinstance(chats, list) else 0},
        )

    def scrape_meetings(self, since: Optional[datetime] = None) -> ScrapeResult:
        """Scrape meeting transcripts and recordings.

        Args:
            since: Optional timestamp to filter meetings after.

        Returns:
            ScrapeResult with meeting items.
        """
        if not HAS_HTTPX:
            return ScrapeResult(
                source=f"{self.name}_meetings",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["httpx not installed"],
            )

        token = self._token or self._get_token()
        if not token or _is_token_expired(token):
            return ScrapeResult(
                source=f"{self.name}_meetings",
                timestamp=datetime.now(timezone.utc),
                items=[],
                count=0,
                errors=["No valid IC3 token"],
            )

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=self.scrape_interval_hours)

        items: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = self._request_with_retry(
                    client, "GET", IC3_MEETINGS_URL, token
                )

                if resp is None:
                    errors.append("Failed to fetch meetings (retries exhausted)")
                elif resp.status_code == 200:
                    data = resp.json()
                    meetings = data if isinstance(data, list) else data.get("value", [])

                    for meeting in meetings:
                        item = self._meeting_to_dict(meeting)
                        if item:
                            items.append(item)
                elif resp.status_code == 404:
                    # Meetings endpoint may not exist for all tenants
                    logger.debug("Meetings endpoint not available (404)")
                else:
                    errors.append(f"Meetings API returned {resp.status_code}")

        except httpx.ConnectError as exc:
            errors.append(f"Network error: {exc}")
        except httpx.TimeoutException as exc:
            errors.append(f"Timeout: {exc}")
        except Exception as exc:
            errors.append(f"Unexpected error: {exc}")
            logger.error("Meeting scraping error: %s", exc)

        return ScrapeResult(
            source=f"{self.name}_meetings",
            timestamp=datetime.now(timezone.utc),
            items=items,
            count=len(items),
            errors=errors,
            metadata={"since": since.isoformat()},
        )

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _request_with_retry(
        self,
        client: "httpx.Client",
        method: str,
        url: str,
        token: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Optional["httpx.Response"]:
        """Make an HTTP request with exponential backoff retry.

        Args:
            client: httpx Client instance.
            method: HTTP method (GET, POST).
            url: Request URL.
            token: Bearer token.
            max_retries: Maximum number of retry attempts.
            **kwargs: Additional kwargs passed to client.request().

        Returns:
            Response object or None if all retries failed.
        """
        headers = self._auth_headers(token)

        for attempt in range(max_retries):
            try:
                resp = client.request(method, url, headers=headers, **kwargs)

                if resp.status_code == 429:
                    # Rate limited — back off
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    wait = min(retry_after * (2 ** attempt), 60)
                    logger.warning("Rate limited by Teams API, waiting %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                    import time as _time
                    _time.sleep(wait)
                    continue

                if resp.status_code == 401:
                    # Token rejected — no point retrying
                    logger.error("Teams API rejected token (401)")
                    return resp

                return resp

            except httpx.ConnectError as exc:
                logger.warning("Connection error (attempt %d/%d): %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                continue
            except httpx.TimeoutException as exc:
                logger.warning("Timeout (attempt %d/%d): %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(2 ** attempt)
                continue

        logger.error("All %d retries exhausted for %s %s", max_retries, method, url)
        return None

    def _fetch_chat_messages(
        self,
        client: "httpx.Client",
        token: str,
        chat_id: str,
        since: datetime,
    ) -> list[dict[str, Any]] | str:
        """Fetch messages for a single chat.

        Args:
            client: httpx Client instance.
            token: Bearer token.
            chat_id: Teams chat/conversation ID.
            since: Only fetch messages after this timestamp.

        Returns:
            List of message dicts, or error string.
        """
        url = IC3_CHAT_MESSAGES_URL.format(chat_id=chat_id)
        params = {"$top": min(self.max_messages, 50)}

        resp = self._request_with_retry(client, "GET", url, token, params=params)
        if resp is None:
            return f"Failed to fetch messages for chat {chat_id}"

        if resp.status_code != 200:
            return f"Messages API returned {resp.status_code} for chat {chat_id}"

        try:
            data = resp.json()
        except json.JSONDecodeError:
            return f"Invalid JSON response for chat {chat_id}"

        messages_data = data if isinstance(data, list) else data.get("value", data.get("messages", []))
        items: list[dict[str, Any]] = []

        for msg in messages_data:
            try:
                item = self._chat_message_to_dict(msg)
                if item:
                    items.append(item)
            except Exception as exc:
                logger.debug("Failed to parse chat message: %s", exc)

        return items

    # ── Item conversion ────────────────────────────────────────────────────

    def _chat_message_to_dict(self, msg: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Convert a Teams chat message dict to a standardized dict.

        Force-masks sender names for PII, same as Exchange scraper pattern.
        """
        if not isinstance(msg, dict):
            return None

        # Extract sender info and force-mask
        sender = msg.get("sender", {}) or msg.get("from", {}) or {}
        if isinstance(sender, dict):
            sender_name = _mask_sender_name(sender.get("displayName", "") or sender.get("name", ""))
            sender_email = sender.get("email", "") or sender.get("userPrincipalName", "")
        elif isinstance(sender, str):
            sender_name = _mask_sender_name(sender)
            sender_email = ""
        else:
            sender_name = "[REDACTED]"
            sender_email = ""

        # Extract message body
        body = ""
        content = msg.get("content", "") or msg.get("body", {})
        if isinstance(content, dict):
            body = content.get("content", "") or content.get("text", "")
        elif isinstance(content, str):
            body = content

        # Strip HTML tags from body
        import re

        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()

        # Extract timestamp
        timestamp = msg.get("timestamp", "") or msg.get("createdDateTime", "") or msg.get("composedTime", "")

        return {
            "message_id": msg.get("id", "") or msg.get("messageId", ""),
            "type": "chat_message",
            "subject": msg.get("subject", "") or msg.get("topic", "") or "",
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "date": timestamp,
            "body": body,
            "chat_id": msg.get("conversationId", "") or msg.get("chatId", ""),
            "has_attachments": bool(msg.get("attachments")),
            "importance": msg.get("importance", "normal"),
        }

    def _meeting_to_dict(self, meeting: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Convert a Teams meeting dict to a standardized dict.

        Force-masks organizer and attendee names for PII.
        """
        if not isinstance(meeting, dict):
            return None

        # Mask organizer
        organizer = meeting.get("organizer", {}) or {}
        if isinstance(organizer, dict):
            organizer_name = _mask_sender_name(organizer.get("displayName", "") or organizer.get("name", ""))
            organizer_email = organizer.get("email", "") or organizer.get("userPrincipalName", "")
        else:
            organizer_name = "[REDACTED]"
            organizer_email = ""

        # Mask attendees
        attendees = []
        for attendee in meeting.get("attendees", []):
            if isinstance(attendee, dict):
                attendees.append({
                    "name": _mask_sender_name(attendee.get("displayName", "") or attendee.get("name", "")),
                    "email": attendee.get("email", "") or attendee.get("userPrincipalName", ""),
                })

        return {
            "message_id": meeting.get("id", ""),
            "type": "meeting",
            "subject": meeting.get("subject", ""),
            "organizer": {
                "name": organizer_name,
                "email": organizer_email,
            },
            "attendees": attendees,
            "start": meeting.get("start", {}) or meeting.get("startDateTime", ""),
            "end": meeting.get("end", {}) or meeting.get("endDateTime", ""),
            "location": meeting.get("location", {}),
            "is_all_day": meeting.get("isAllDay", False),
            "is_cancelled": meeting.get("isCancelled", False),
            "has_transcript": meeting.get("hasTranscript", False),
            "has_recording": meeting.get("hasRecording", False),
        }

    # ── Status ────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return Teams scraper status.

        Returns:
            Dict with name, auth_mode, connected, last_scrape, token_status.
        """
        token = self._token or self._get_token()
        token_status = "none"
        if token:
            token_status = "expired" if _is_token_expired(token) else "valid"

        return {
            "name": self.name,
            "auth_mode": self.auth_mode,
            "connected": self._connected,
            "last_scrape": self._last_scrape.isoformat() if self._last_scrape else None,
            "token_status": token_status,
            "has_httpx": HAS_HTTPX,
        }