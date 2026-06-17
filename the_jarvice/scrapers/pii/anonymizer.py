"""The Jarvice — PII Anonymizer.

Script-based PII pipeline: RED (originals with PII) → GREEN (anonymized with masks).
Mapping is stored in RED directory (chmod 600) — agents never access it.

Mask format: [PERSON_1], [EMAIL_2], [PHONE_3], etc.
Consistent mapping: Иванов → [PERSON_1] everywhere.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("the_jarvice.pii")

# ---------------------------------------------------------------------------
# Mask pattern for deanonymization
# ---------------------------------------------------------------------------
MASK_PATTERN = re.compile(r"\[(?:PERSON|PHONE|EMAIL|INN|SNILS|PASSPORT|CARD|ADDRESS|ORG|PII)_\d+\]")


# ---------------------------------------------------------------------------
# PII Classifier (simplified, no external deps)
# ---------------------------------------------------------------------------

# Russian phone pattern: +7 XXX XXX-XX-XX, 8 XXX XXX XX XX, etc.
_RU_PHONE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
    re.IGNORECASE,
)
# Email pattern
_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# INN pattern (10 or 12 digits)
_INN = re.compile(r"\b\d{10}\b|\b\d{12}\b")
# SNILS pattern (XXX-XXX-XXX XX)
_SNILS = re.compile(r"\b\d{3}-\d{3}-\d{3}\s\d{2}\b")


class PIIClassifier:
    """Simple regex-based PII classifier.

    Detects: Russian phone numbers, emails, INN, SNILS.
    Does NOT detect names — those are handled by force-masking sender/recipient fields.
    """

    @staticmethod
    def classify(text: str) -> list[tuple[str, str, int, int]]:
        """Classify PII entities in text.

        Returns:
            List of (type, value, start, end) tuples.
        """
        entities = []

        # Emails
        for m in _EMAIL.finditer(text):
            entities.append(("email", m.group(), m.start(), m.end()))

        # Russian phone numbers
        for m in _RU_PHONE.finditer(text):
            entities.append(("phone", m.group(), m.start(), m.end()))

        # INN (be careful not to match random 10-digit numbers)
        for m in _INN.finditer(text):
            # Simple checksum validation would go here
            entities.append(("inn", m.group(), m.start(), m.end()))

        # SNILS
        for m in _SNILS.finditer(text):
            entities.append(("snils", m.group(), m.start(), m.end()))

        # Sort by position (for replacement from end)
        entities.sort(key=lambda e: e[2], reverse=True)
        return entities

    @staticmethod
    def has_pii(text: str) -> bool:
        """Quick check if text likely contains PII."""
        return bool(_EMAIL.search(text) or _RU_PHONE.search(text) or _SNILS.search(text))


# ---------------------------------------------------------------------------
# Mapping Manager
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "person": ("persons", "PERSON"),
    "phone": ("phones", "PHONE"),
    "email": ("emails", "EMAIL"),
    "inn": ("ids", "INN"),
    "snils": ("ids", "SNILS"),
    "passport": ("ids", "PASSPORT"),
    "card": ("ids", "CARD"),
    "org": ("organizations", "ORG"),
    "address": ("addresses", "ADDRESS"),
}


class MappingManager:
    """Manages consistent PII → mask mapping.

    Stores mapping in RED directory (chmod 600).
    Ensures Иванов = [PERSON_1] consistently across all uses.
    """

    def __init__(self, mapping_path: Optional[Path] = None) -> None:
        if mapping_path is None:
            mapping_path = Path("~/.the-jarvice/data/pii/RED/mapping.json").expanduser()
        self.mapping_path = Path(mapping_path)
        self._mapping: dict = self._load()

    def _load(self) -> dict:
        """Load mapping from disk."""
        if self.mapping_path.exists():
            try:
                data = json.loads(self.mapping_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("version") == 1:
                    return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load mapping: %s — starting fresh", exc)

        return {
            "version": 1,
            "persons": {},
            "phones": {},
            "emails": {},
            "ids": {},
            "organizations": {},
            "addresses": {},
            "_reverse": {},
        }

    def save(self) -> None:
        """Persist mapping to disk with secure permissions."""
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.write_text(
            json.dumps(self._mapping, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        # Secure: owner-only read/write
        os.chmod(self.mapping_path, 0o600)
        os.chmod(self.mapping_path.parent, 0o700)
        logger.debug("Mapping saved to %s", self.mapping_path)

    def get_or_create_token(self, pii_type: str, value: str) -> str:
        """Get existing mask token or create a new one for a PII value.

        Args:
            pii_type: One of 'person', 'phone', 'email', 'inn', 'snils', etc.
            value: The original PII value to mask.

        Returns:
            Mask token like [PERSON_1], [EMAIL_2], etc.
        """
        # Normalize for lookup
        norm_value = value.strip().lower()

        # Check reverse index first
        reverse = self._mapping.setdefault("_reverse", {})
        if norm_value in reverse:
            return reverse[norm_value]

        # Determine category and prefix
        category, prefix = TYPE_MAP.get(pii_type, ("ids", "PII"))
        cat_dict = self._mapping.setdefault(category, {})

        # Check existing mappings (case-insensitive)
        for token, stored in cat_dict.items():
            if isinstance(stored, dict):
                stored_norm = stored.get("full", "").strip().lower()
                variants = [v.strip().lower() for v in stored.get("variants", [])]
                if norm_value == stored_norm or norm_value in variants:
                    reverse[norm_value] = token
                    return token
            elif isinstance(stored, str) and stored.strip().lower() == norm_value:
                reverse[norm_value] = token
                return token

        # Create new token
        idx = len(cat_dict) + 1
        token = f"[{prefix}_{idx}]"

        # Store the mapping
        if pii_type == "person":
            cat_dict[token] = {"full": value.strip(), "variants": [value.strip()]}
        else:
            cat_dict[token] = value.strip()

        reverse[norm_value] = token
        return token

    def add_variant(self, token: str, variant: str) -> None:
        """Add a spelling variant for an existing person token.

        Args:
            token: Existing mask like [PERSON_1].
            variant: Alternative spelling to associate.
        """
        persons = self._mapping.get("persons", {})
        if token in persons and isinstance(persons[token], dict):
            variants = persons[token].set("variants", [])
            if variant.strip() not in variants:
                variants.append(variant.strip())
                # Also add to reverse index
                reverse = self._mapping.setdefault("_reverse", {})
                reverse[variant.strip().lower()] = token


# ---------------------------------------------------------------------------
# Anonymizer
# ---------------------------------------------------------------------------

class Anonymizer:
    """PII anonymization pipeline.

    Flow:
      1. Load text from RED directory (originals with PII)
      2. Classify PII entities (regex-based)
      3. Replace with consistent masks using MappingManager
      4. Save anonymized text to GREEN directory
      5. Save mapping to RED/mapping.json (chmod 600)

    The mapping is NEVER accessible to LLM agents — only the GREEN
    (anonymized) text is sent to the model.
    """

    def __init__(
        self,
        red_dir: Optional[Path] = None,
        green_dir: Optional[Path] = None,
        mapping_path: Optional[Path] = None,
    ) -> None:
        self.red_dir = red_dir or Path("~/.the-jarvice/data/pii/RED").expanduser()
        self.green_dir = green_dir or Path("~/.the-jarvice/data/pii/GREEN").expanduser()
        self.mapping = MappingManager(mapping_path)
        self.classifier = PIIClassifier()

    def anonymize_text(self, text: str) -> tuple[str, bool]:
        """Anonymize PII in a text string.

        Args:
            text: Original text potentially containing PII.

        Returns:
            Tuple of (anonymized_text, has_pii).
        """
        if not text:
            return text, False

        entities = self.classifier.classify(text)
        has_pii = bool(entities)

        # Replace from end to preserve offsets
        result = text
        for pii_type, value, start, end in entities:
            token = self.mapping.get_or_create_token(pii_type, value)
            result = result[:start] + token + result[end:]

        return result, has_pii

    def anonymize_dict(self, data: dict) -> tuple[dict, bool]:
        """Anonymize PII in a dict (typically email/calendar item).

        Force-masks sender and recipient names/emails, then
        anonymizes subject and body text.

        Args:
            data: Dict with email/calendar fields.

        Returns:
            Tuple of (anonymized_dict, has_pii).
        """
        result = dict(data)
        has_pii = False

        # Force-mask sender name and email
        sender = result.get("sender", {})
        if isinstance(sender, dict):
            if sender.get("name"):
                result["sender"]["name"] = self.mapping.get_or_create_token("person", sender["name"])
                has_pii = True
            if sender.get("email"):
                result["sender"]["email"] = self.mapping.get_or_create_token("email", sender["email"])
                has_pii = True

        # Force-mask recipient names and emails
        for recipient in result.get("recipients", []):
            if isinstance(recipient, dict):
                if recipient.get("name"):
                    recipient["name"] = self.mapping.get_or_create_token("person", recipient["name"])
                    has_pii = True
                if recipient.get("email"):
                    recipient["email"] = self.mapping.get_or_create_token("email", recipient["email"])
                    has_pii = True

        # Anonymize subject
        subject = result.get("subject", "")
        if subject:
            anon_subj, subj_pii = self.anonymize_text(subject)
            result["subject"] = anon_subj
            if subj_pii:
                has_pii = True

        # Anonymize body
        body = result.get("body", "")
        if body:
            anon_body, body_pii = self.anonymize_text(body)
            result["body"] = anon_body
            if body_pii:
                has_pii = True

        # Force-mask organizer (calendar)
        organizer = result.get("organizer", {})
        if isinstance(organizer, dict):
            if organizer.get("name"):
                result["organizer"]["name"] = self.mapping.get_or_create_token("person", organizer["name"])
                has_pii = True
            if organizer.get("email"):
                result["organizer"]["email"] = self.mapping.get_or_create_token("email", organizer["email"])
                has_pii = True

        # Force-mask attendees (calendar)
        for attendee_list in ["required_attendees", "optional_attendees"]:
            for attendee in result.get(attendee_list, []):
                if isinstance(attendee, dict):
                    if attendee.get("name"):
                        attendee["name"] = self.mapping.get_or_create_token("person", attendee["name"])
                        has_pii = True
                    if attendee.get("email"):
                        attendee["email"] = self.mapping.get_or_create_token("email", attendee["email"])
                        has_pii = True

        result["has_pii"] = has_pii
        return result, has_pii

    def process_scrape_result(self, scrape_result: "ScrapeResult") -> "ScrapeResult":
        """Process a ScrapeResult through the PII pipeline.

        Saves originals to RED, anonymized to GREEN, returns anonymized result.

        Args:
            scrape_result: ScrapeResult from a scraper.

        Returns:
            New ScrapeResult with anonymized items.
        """
        from the_jarvice.core.scraper_base import ScrapeResult

        # Ensure directories exist
        self.red_dir.mkdir(parents=True, exist_ok=True)
        self.green_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.red_dir, 0o700)

        anonymized_items = []
        total_pii = 0

        for item in scrape_result.items:
            file_id = self._file_id(item)

            # Save original to RED
            red_path = self.red_dir / f"{file_id}.json"
            if not red_path.exists():
                red_path.write_text(
                    json.dumps(item, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
                os.chmod(red_path, 0o600)

            # Anonymize
            anon_item, has_pii = self.anonymize_dict(item)
            anonymized_items.append(anon_item)
            if has_pii:
                total_pii += 1

            # Save anonymized to GREEN
            green_path = self.green_dir / f"{file_id}.json"
            green_path.write_text(
                json.dumps(anon_item, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        # Save mapping
        if total_pii > 0:
            self.mapping.save()

        return ScrapeResult(
            source=f"{scrape_result.source}_anonymized",
            timestamp=scrape_result.timestamp,
            items=anonymized_items,
            count=len(anonymized_items),
            errors=scrape_result.errors.copy(),
            metadata={
                **scrape_result.metadata,
                "pii_found": total_pii,
                "pii_total": len(scrape_result.items),
            },
        )

    @staticmethod
    def _file_id(item: dict) -> str:
        """Generate stable file ID from item metadata."""
        raw = f"{item.get('message_id', '')}-{item.get('subject', '')}-{item.get('date', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Deanonymizer (for final delivery)
# ---------------------------------------------------------------------------

class Deanonymizer:
    """Replaces PII masks with real values for delivery.

    Used after LLM processing to restore real names in the
    final Telegram message.
    """

    def __init__(self, mapping_path: Optional[Path] = None) -> None:
        if mapping_path is None:
            mapping_path = Path("~/.the-jarvice/data/pii/RED/mapping.json").expanduser()
        self.mapping_path = Path(mapping_path)
        self._token_map: Optional[dict[str, str]] = None

    def _load_token_map(self) -> dict[str, str]:
        """Build token → real_value map from mapping file."""
        mapping = MappingManager(mapping_path=self.mapping_path)
        data = mapping._mapping

        token_map: dict[str, str] = {}

        for category in ["persons", "phones", "emails", "ids", "organizations", "addresses"]:
            cat_data = data.get(category, {})
            for token, value in cat_data.items():
                if isinstance(value, dict):
                    token_map[token] = value.get("full", str(value))
                else:
                    token_map[token] = str(value)

        return token_map

    @property
    def token_map(self) -> dict[str, str]:
        """Lazy-loaded token → value map."""
        if self._token_map is None:
            self._token_map = self._load_token_map()
        return self._token_map

    def has_masks(self, text: str) -> bool:
        """Check if text contains PII masks."""
        return bool(MASK_PATTERN.search(text))

    def deanonymize(self, text: str) -> str:
        """Replace all PII masks with real values.

        Args:
            text: Text with [PERSON_1] style masks.

        Returns:
            Text with masks replaced by real values.
        """
        if not self.has_masks(text):
            return text

        result = text
        for token, value in self.token_map.items():
            result = result.replace(token, value)

        return result