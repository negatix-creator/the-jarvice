"""The Jarvice — PII Anonymizer.

Script-based PII pipeline: RED (originals with PII) → GREEN (anonymized with masks).
Mapping is stored in RED directory (chmod 600) — agents never access it.

Mask format: [PERSON_1], [EMAIL_2], [PHONE_3], [TGID_4], etc.
Consistent mapping: Иванов → [PERSON_1] everywhere.

Stage 1 enhancements:
  - NER via qwen3:14b (local, NOT cloud) for extracting ФИО from text body
  - Telegram ID regex pattern
  - MappingManager variants for partial matches (Иванов → Иванова Вика)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("the_jarvice.pii")

# ---------------------------------------------------------------------------
# Mask pattern for deanonymization
# ---------------------------------------------------------------------------
MASK_PATTERN = re.compile(
    r"\[(?:PERSON|PHONE|EMAIL|INN|SNILS|PASSPORT|CARD|ADDRESS|TGID|ORG|PII)_\d+\]"
)


# ---------------------------------------------------------------------------
# PII Classifier (regex + NER via Ollama/qwen3:14b)
# ---------------------------------------------------------------------------

# Russian phone pattern: +7 XXX XXX-XX-XX, 8 XXX XXX XX XX, etc.
_RU_PHONE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
    re.IGNORECASE,
)
# Email pattern
_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# Patterns that look like email but are NOT PII (Exchange Message-IDs, CID)
_MESSAGE_ID_HEX = re.compile(r"[0-9a-f]{16,}@[a-zA-Z0-9.\-]+", re.IGNORECASE)
_MESSAGE_ID_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@", re.IGNORECASE)
_CID_PATTERN = re.compile(r"cid:[^\s\]]+", re.IGNORECASE)
# INN pattern (10 or 12 digits, with word-boundary checks)
_INN_10 = re.compile(r"\b\d{10}\b")
_INN_12 = re.compile(r"\b\d{12}\b")
# SNILS pattern (XXX-XXX-XXX XX or XXXXXX XXXX)
_SNILS = re.compile(r"\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}\b")
# Telegram ID pattern: @username or numeric ID with context
_TG_USERNAME = re.compile(r"(?<!\w)@([a-zA-Z]\w{3,31})(?!\w)")
_TG_NUMERIC = re.compile(
    r"(?:Telegram\s*(?:ID|id|айди|айди)|tg\s*(?:id|ID))\s*[:#=]\s*(\d{5,10})",
    re.IGNORECASE,
)
# Telegram link pattern: t.me/username
_TG_LINK = re.compile(r"t\.me/([a-zA-Z]\w{3,31})", re.IGNORECASE)

# NER model config
_NER_MODEL = "qwen3:14b"  # LOCAL ONLY — ПДн не уходят в облако. 89% recall, 140s — медленнее но безопасно
_NER_MODEL_FALLBACK = None  # no cloud fallback for NER — PII must stay local
_NER_TIMEOUT = 120  # seconds
_NER_ENABLED = True  # can be disabled for testing

# Known non-person exclusions (common false positives)
_STATIC_EXCLUSIONS: set[str] = {
    # Companies/orgs
    "фск", "фск девелопмент", "мсу", "1дск", "каскад", "цод",
    "антропик", "anthropic", "openclaw", "telegram", "apple",
    # Departments
    "дит", "блок ит", "ит", "hr", "дпо",
    # Common false positives from NER
    "коллеги", "уважением", "директор", "менеджер",
    "руководитель", "начальник", "заместитель",
    # Roles/titles
    "cpo", "cto", "cio", "po", "qa",
    # Single-char or too short
    "рф", "сша",
}


class PIIClassifier:
    """Regex + NER-based PII classifier.

    Detects: Russian phone numbers, emails, INN, SNILS, Telegram IDs,
    and ФИО via local qwen3:14b NER.
    """

    @staticmethod
    def classify(text: str) -> list[tuple[str, str, int, int]]:
        """Classify PII entities in text.

        Returns:
            List of (type, value, start, end) tuples sorted by position.
        """
        entities: list[tuple[str, str, int, int]] = []

        # --- Regex-based detection ---

        # Emails (before phones to avoid overlap) — skip Exchange Message-IDs and CID
        for m in _EMAIL.finditer(text):
            value = m.group()
            # Skip Exchange Message-IDs (hex@..., UUID@...) and CID references
            if _MESSAGE_ID_HEX.match(value) or _MESSAGE_ID_UUID.match(value):
                continue
            if _CID_PATTERN.search(text[max(0, m.start()-10):m.end()+10]):
                continue
            entities.append(("email", value, m.start(), m.end()))

        # Russian phone numbers
        for m in _RU_PHONE.finditer(text):
            entities.append(("phone", m.group(), m.start(), m.end()))

        # INN (10 digits = company, 12 digits = individual)
        for m in _INN_12.finditer(text):
            entities.append(("inn", m.group(), m.start(), m.end()))
        for m in _INN_10.finditer(text):
            # Skip if it overlaps with a 12-digit INN
            if not any(m.start() >= e[2] and m.start() < e[3] and e[0] == "inn" for e in entities):
                entities.append(("inn", m.group(), m.start(), m.end()))

        # SNILS
        for m in _SNILS.finditer(text):
            entities.append(("snils", m.group(), m.start(), m.end()))

        # Telegram IDs — usernames
        for m in _TG_USERNAME.finditer(text):
            username = m.group(1)
            # Skip common non-person usernames
            if username.lower() not in _STATIC_EXCLUSIONS:
                entities.append(("tgid", f"@{username}", m.start(), m.end()))

        # Telegram IDs — numeric with context
        for m in _TG_NUMERIC.finditer(text):
            entities.append(("tgid", m.group(1), m.start(), m.end()))

        # Telegram IDs — t.me links
        for m in _TG_LINK.finditer(text):
            username = m.group(1)
            if username.lower() not in _STATIC_EXCLUSIONS:
                entities.append(("tgid", f"@{username}", m.start(), m.end()))

        # --- NER-based person detection via local qwen3:14b ---
        if _NER_ENABLED:
            try:
                ner_names = ner_extract_persons(text)
                for name in ner_names:
                    # Skip exclusions
                    if name.lower().strip() in _STATIC_EXCLUSIONS:
                        continue
                    if len(name.strip()) <= 2:
                        continue
                    # Find all occurrences in text
                    for occ in _find_name_occurrences(text, name):
                        entities.append(("person", occ[0], occ[1], occ[2]))
            except Exception as exc:
                logger.warning("NER extraction failed: %s — falling back to regex-only", exc)

        # Remove overlaps (keep longer/higher-priority match)
        entities = _remove_overlaps(entities)

        # Sort by position (for replacement from end)
        entities.sort(key=lambda e: e[2], reverse=True)
        return entities

    @staticmethod
    def has_pii(text: str) -> bool:
        """Quick check if text likely contains PII."""
        # Check regex patterns first (fast)
        if _EMAIL.search(text) or _RU_PHONE.search(text) or _SNILS.search(text):
            return True
        if _TG_USERNAME.search(text) or _TG_NUMERIC.search(text) or _TG_LINK.search(text):
            return True
        # For NER, we assume text over ~50 chars might have names
        # (actual check happens in classify)
        return False


def _find_name_occurrences(text: str, name: str) -> list[tuple[str, int, int]]:
    """Find all occurrences of a person name in text.

    Handles declined forms (Russian morphology) by fuzzy matching.
    Returns list of (matched_text, start, end) tuples.
    """
    results = []
    # Try exact match first
    base = name.strip()
    for m in re.finditer(re.escape(base), text):
        results.append((base, m.start(), m.end()))

    # Try case-insensitive match for partial coverage
    if base not in text:
        for m in re.finditer(re.escape(base), text, re.IGNORECASE):
            results.append((base, m.start(), m.end()))

    return results


def _remove_overlaps(
    entities: list[tuple[str, str, int, int]]
) -> list[tuple[str, str, int, int]]:
    """Remove overlapping entities, keeping the longest/highest-priority match."""
    if not entities:
        return entities

    # Sort by start position, then by length (longest first)
    entities_sorted = sorted(entities, key=lambda e: (e[2], -(e[3] - e[2])))

    result = []
    last_end = -1
    for ent in entities_sorted:
        if ent[2] >= last_end:
            result.append(ent)
            last_end = ent[3]
    return result


# ---------------------------------------------------------------------------
# NER via local Ollama (qwen3:14b)
# ---------------------------------------------------------------------------

def ner_extract_persons(text: str, model: str = _NER_MODEL) -> list[str]:
    """Extract person names from text using local qwen3:14b via Ollama.

    The model returns a JSON list of names. We then locate them in the
    original text ourselves (LLM offsets are unreliable).

    Args:
        text: Input text to extract names from.
        model: Ollama model name (default: qwen3:14b).

    Returns:
        List of person name strings found in the text.
    """
    # Truncate very long texts to avoid excessive processing time
    max_chars = 8000
    truncated = text[:max_chars] if len(text) > max_chars else text

    prompt = (
        "Извлеки все ФИО и имена людей из текста. "
        "Верни ТОЛЬКО JSON-массив строк с именами. "
        "Формы: Фамилия Имя Отчество, Фамилия И., Имя Фамилия. "
        "НЕ включай названия компаний, отделов, должностей. "
        "НЕ включай имена, которые являются частью названий продуктов.\n\n"
        f"Текст:\n{truncated}"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ты NER-экстрактор. Извлекай только ФИО людей. Отвечай ТОЛЬКО JSON-массивом строк."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2048,
        },
    }

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(_NER_TIMEOUT),
             "http://localhost:11434/api/chat",
             "-d", json.dumps(payload, ensure_ascii=False)],
            capture_output=True,
            text=True,
            timeout=_NER_TIMEOUT + 10,
        )

        if result.returncode != 0:
            logger.warning("NER curl failed: %s", result.stderr[:500])
            return []

        response = json.loads(result.stdout)
        content = response.get("message", {}).get("content", "").strip()

        if not content:
            logger.debug("NER returned empty content")
            return []

        # Try to parse JSON from response
        # Model might wrap in markdown code blocks
        json_str = content
        json_match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()

        # Try direct JSON parse
        try:
            names = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to find array in the response
            arr_match = re.search(r"\[.*\]", json_str, re.DOTALL)
            if arr_match:
                names = json.loads(arr_match.group(0))
            else:
                logger.warning("NER: could not parse JSON from response: %s", content[:200])
                return []

        if not isinstance(names, list):
            logger.warning("NER: expected list, got %s", type(names).__name__)
            return []

        # Clean up names
        cleaned = []
        for name in names:
            if isinstance(name, str):
                name = name.strip()
                if name and len(name) > 2 and name.lower() not in _STATIC_EXCLUSIONS:
                    cleaned.append(name)
            elif isinstance(name, dict) and "name" in name:
                n = name["name"].strip()
                if n and len(n) > 2 and n.lower() not in _STATIC_EXCLUSIONS:
                    cleaned.append(n)

        return cleaned

    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as exc:
        logger.warning("NER extraction error: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Mapping Manager (with variants support)
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "person": ("persons", "PERSON"),
    "phone": ("phones", "PHONE"),
    "email": ("emails", "EMAIL"),
    "inn": ("ids", "INN"),
    "snils": ("ids", "SNILS"),
    "passport": ("ids", "PASSPORT"),
    "card": ("ids", "CARD"),
    "tgid": ("ids", "TGID"),
    "org": ("organizations", "ORG"),
    "address": ("addresses", "ADDRESS"),
}


class MappingManager:
    """Manages consistent PII → mask mapping with variant support.

    Stores mapping in RED directory (chmod 600).
    Ensures Иванов = [PERSON_1] consistently across all uses.
    Supports partial matches: "Иванов" → [PERSON_1] (maps to "Иванова Вика").
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
                if isinstance(data, dict) and data.get("version") in (1, 2):
                    # Ensure _reverse and variants exist
                    data.setdefault("_reverse", {})
                    self._rebuild_reverse(data)
                    return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load mapping: %s — starting fresh", exc)

        return {
            "version": 2,
            "persons": {},
            "phones": {},
            "emails": {},
            "ids": {},
            "organizations": {},
            "addresses": {},
            "_reverse": {},
        }

    def _rebuild_reverse(self, mapping: dict) -> None:
        """Rebuild reverse index from all categories."""
        reverse = mapping.setdefault("_reverse", {})
        reverse.clear()

        # Rebuild from persons (with variants)
        for token, data in mapping.get("persons", {}).items():
            if isinstance(data, dict):
                full = data.get("full", "")
                if full:
                    reverse[full.strip().lower()] = token
                for v in data.get("variants", []):
                    reverse[v.strip().lower()] = token

        # Rebuild from other categories
        for cat in ["phones", "emails", "ids", "organizations", "addresses"]:
            for token, value in mapping.get(cat, {}).items():
                if isinstance(value, dict):
                    reverse[value.get("full", str(value)).strip().lower()] = token
                elif isinstance(value, str):
                    reverse[value.strip().lower()] = token

    def save(self) -> None:
        """Persist mapping to disk with secure permissions."""
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.write_text(
            json.dumps(self._mapping, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        # Secure: owner-only read/write
        try:
            os.chmod(self.mapping_path, 0o600)
        except OSError:
            pass  # e.g. /tmp on macOS
        try:
            os.chmod(self.mapping_path.parent, 0o700)
        except OSError:
            pass
        logger.debug("Mapping saved to %s", self.mapping_path)

    def get_or_create_token(self, pii_type: str, value: str) -> str:
        """Get existing mask token or create a new one for a PII value.

        For persons, also checks partial/variant matches:
        - "Иванов" matches "Иванова Вика" (variant lookup)
        - "Иванов А.П." matches "Иванов Алексей Петрович" (variant)

        Args:
            pii_type: One of 'person', 'phone', 'email', 'inn', 'snils', 'tgid', etc.
            value: The original PII value to mask.

        Returns:
            Mask token like [PERSON_1], [EMAIL_2], etc.
        """
        # Normalize for lookup
        norm_value = value.strip().lower()

        # Check reverse index first (exact match)
        reverse = self._mapping.setdefault("_reverse", {})
        if norm_value in reverse:
            return reverse[norm_value]

        # For persons, try partial/fuzzy matching via variants
        if pii_type == "person":
            token = self._find_person_variant(value)
            if token:
                # Add this variant to the existing mapping
                self.add_variant(token, value)
                return token

        # Determine category and prefix
        category, prefix = TYPE_MAP.get(pii_type, ("ids", "PII"))
        cat_dict = self._mapping.setdefault(category, {})

        # Check existing mappings (case-insensitive) — for non-person types
        if pii_type != "person":
            for token, stored in cat_dict.items():
                stored_norm = (stored if isinstance(stored, str) else str(stored)).strip().lower()
                if norm_value == stored_norm:
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

    def _find_person_variant(self, name: str) -> Optional[str]:
        """Find a matching person token via partial name matching.

        Handles Russian morphology:
        - "Иванов" matches "Иванова Вика" (surname root match)
        - "Иванов А.П." matches "Иванов Алексей Петрович" (initials match)
        - "Вика" matches "Иванова Вика" (first name match)

        Args:
            name: Name to look up (may be partial/declined).

        Returns:
            Existing token if a match is found, None otherwise.
        """
        norm = name.strip().lower()
        persons = self._mapping.get("persons", {})

        if not persons:
            return None

        # Split input name into parts
        name_parts = norm.split()

        for token, data in persons.items():
            if not isinstance(data, dict):
                continue

            full = data.get("full", "").strip().lower()
            variants = [v.strip().lower() for v in data.get("variants", [])]

            # Exact match on full or variant
            if norm == full or norm in variants:
                return token

            # Check if input is a prefix/suffix of the full name
            # "Иванов" is part of "Иванов Алексей Петрович"
            full_parts = full.split()
            if len(name_parts) == 1:
                # Single word input — check if it matches any part of full name
                for fp in full_parts:
                    # Russian root matching: Иванов ~ Иванова (remove typical endings)
                    if _roots_match(name_parts[0], fp):
                        return token

            # Check initials match: "Иванов А.П." vs "Иванов Алексей Петрович"
            if len(name_parts) >= 2:
                surname = name_parts[0]
                # Extract initials from parts like "А.П." or "А.П" or "А."
                # A single part with dots contains multiple initials: "А.П." → ["А", "П"]
                input_initials = []
                for part in name_parts[1:]:
                    cleaned = part.rstrip(".")
                    if "." in part:
                        # Split on dots: "а.п" → ["а", "п"], "а." → ["а"]
                        for ch in cleaned.split("."):
                            ch = ch.strip()
                            if ch and len(ch) == 1:
                                input_initials.append(ch[0].upper())
                    elif len(cleaned) <= 3:
                        # Single initial without dot: short word
                        input_initials.append(cleaned[0].upper())

                if _roots_match(surname, full_parts[0] if full_parts else ""):
                    # Surname root matches — check initials against full name
                    full_initials = []
                    for part in full_parts[1:]:
                        if part:
                            full_initials.append(part[0].upper())

                    if input_initials and full_initials:
                        # Check if input initials match start of full initials
                        # "Иванов А.П." → initials [А, П] vs "Иванов Алексей Петрович" → [А, П]
                        if input_initials == full_initials[:len(input_initials)]:
                            return token

                # Multi-part declined name: "Testovu Dmitry" vs "Krylov Дмитрий"
                # Each part matches via root matching
                if len(name_parts) == len(full_parts) and len(name_parts) >= 2:
                    surname = name_parts[0]
                    if _roots_match(surname, full_parts[0]):
                        all_match = True
                        for np, fp in zip(name_parts[1:], full_parts[1:]):
                            if not _roots_match(np, fp):
                                all_match = False
                                break
                        if all_match:
                            return token

        return None

    def add_variant(self, token: str, variant: str) -> None:
        """Add a spelling variant for an existing person token.

        Also updates the reverse index so this variant can be looked up.

        Args:
            token: Existing mask like [PERSON_1].
            variant: Alternative spelling to associate.
        """
        persons = self._mapping.get("persons", {})
        if token in persons and isinstance(persons[token], dict):
            variants = persons[token].setdefault("variants", [])
            if variant.strip() not in variants:
                variants.append(variant.strip())
                # Also add to reverse index
                reverse = self._mapping.setdefault("_reverse", {})
                reverse[variant.strip().lower()] = token
                logger.debug("Added variant '%s' for token %s", variant.strip(), token)

    def lookup_name_to_mask(self, name: str) -> Optional[str]:
        """Look up a person name to find its mask token.

        Handles partial matches via variants. Used for user queries:
        "Иванов" → [PERSON_47]

        Args:
            name: Name or partial name to look up.

        Returns:
            Mask token like [PERSON_47] or None if not found.
        """
        norm = name.strip().lower()
        reverse = self._mapping.get("_reverse", {})

        # Direct reverse lookup
        if norm in reverse:
            return reverse[norm]

        # Try variant matching
        return self._find_person_variant(name)


def _roots_match(word1: str, word2: str) -> bool:
    """Check if two Russian words share the same morphological root.

    Simple heuristic: strip common Russian endings and compare stems.
    This is NOT a full morphological analyzer — just enough for PII matching.

    Examples:
        Иванов ~ Иванова (root: иванов)
        Петров ~ Петровым (root: петров)
        Вика ~ Вике (root: вик)
        Сергей ~ Сергеем (root: серг)
    """
    if not word1 or not word2:
        return False

    # Direct match
    if word1 == word2:
        return True

    # Strip common Russian endings to get root
    endings = [
        # Long endings first
        "овича", "евича", "овной", "евной", "овским", "евским",  # declined patronymic/adjective
        "овской", "евской", "овского", "евского",                     # declined adjective
        "овым", "евым", "ова", "ева", "ову", "еву", "ове", "еве",  # -ов/-ev surname
        "иной", "ина", "ину", "ине",                                  # -ин surname
        "ский", "ского", "ской", "скому",                            # -ский
        "енко", "евская", "овская",                                    # common suffixes
        "ович", "евич", "овна", "евна", "ична",                       # patronymic
        "овым", "ому", "ой", "ая", "ый", "ий", "ое", "ые", "ие", # adjective
        "ем", "им", "ам", "ях", "ов", "ев", "ин", "ый", "ий",  # case endings
        "ом", "ем", "ой", "ая", "ую", "юю", "ее", "ие",        # more case
        "ет", "ют", "ат", "ят", "л", "ла", "ло", "ли",        # verb endings
        "е", "у", "ю", "а", "я", "и", "ы", "ь",                  # short
    ]

    # Sort by length descending to strip longest first
    endings_sorted = sorted(endings, key=len, reverse=True)

    def stem(word: str) -> str:
        w = word.lower().strip()
        for ending in endings_sorted:
            if len(ending) < len(w) and w.endswith(ending):
                return w[: -len(ending)]
        return w

    stem1 = stem(word1)
    stem2 = stem(word2)

    # If stems match exactly
    if stem1 == stem2:
        return True
    # One contains the other (after stemming, some overlap remains)
    if len(stem1) >= 3 and len(stem2) >= 3:
        if stem1 in stem2 or stem2 in stem1:
            return True
        # 4+ character common prefix — strong signal
        if stem1[:4] == stem2[:4] and len(stem1) >= 4 and len(stem2) >= 4:
            return True

    return False


# ---------------------------------------------------------------------------
# Anonymizer
# ---------------------------------------------------------------------------

class Anonymizer:
    """PII anonymization pipeline.

    Flow:
      1. Load text from RED directory (originals with PII)
      2. Classify PII entities (regex + NER qwen3:14b)
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
        ner_enabled: bool = True,
    ) -> None:
        self.red_dir = red_dir or Path("~/.the-jarvice/data/pii/RED").expanduser()
        self.green_dir = green_dir or Path("~/.the-jarvice/data/pii/GREEN").expanduser()
        self.mapping = MappingManager(mapping_path)
        self.classifier = PIIClassifier()
        self.ner_enabled = ner_enabled
        global _NER_ENABLED
        _NER_ENABLED = ner_enabled

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

        Force-masks sender, recipient, organizer, and attendee names/emails,
        then anonymizes subject and body text.

        Technical fields (message_id, chat_id) are preserved as-is — they
        are not PII even if they look like email addresses.

        Args:
            data: Dict with email/calendar fields.

        Returns:
            Tuple of (anonymized_dict, has_pii).
        """
        result = dict(data)
        has_pii = False

        # Regex to detect if a name field is actually an email address
        _email_re = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        # Skip technical fields that look like PII (message_id is NOT an email)
        # These are preserved as-is
        skip_keys = {"message_id", "chat_id", "id", "has_attachments",
                      "is_read", "importance", "is_all_day", "is_cancelled",
                      "free_busy", "type", "has_transcript", "has_recording"}

        # Force-mask sender name and email
        # If name looks like an email, mask as email type
        sender = result.get("sender", {})
        if isinstance(sender, dict):
            if sender.get("name"):
                name_val = sender["name"]
                if _email_re.match(name_val):
                    result["sender"]["name"] = self.mapping.get_or_create_token("email", name_val)
                else:
                    result["sender"]["name"] = self.mapping.get_or_create_token("person", name_val)
                has_pii = True
            if sender.get("email"):
                result["sender"]["email"] = self.mapping.get_or_create_token("email", sender["email"])
                has_pii = True

        # Force-mask recipient names and emails
        # If name looks like an email (Exchange sometimes puts email in name field),
        # mask it as email type, not person
        for recipient in result.get("recipients", []):
            if isinstance(recipient, dict):
                if recipient.get("name"):
                    name_val = recipient["name"]
                    if _email_re.match(name_val):
                        # Name is actually an email address — mask as email
                        recipient["name"] = self.mapping.get_or_create_token("email", name_val)
                    else:
                        recipient["name"] = self.mapping.get_or_create_token("person", name_val)
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
                name_val = organizer["name"]
                if _email_re.match(name_val):
                    result["organizer"]["name"] = self.mapping.get_or_create_token("email", name_val)
                else:
                    result["organizer"]["name"] = self.mapping.get_or_create_token("person", name_val)
                has_pii = True
            if organizer.get("email"):
                result["organizer"]["email"] = self.mapping.get_or_create_token("email", organizer["email"])
                has_pii = True

        # Force-mask attendees (calendar)
        for attendee_list in ["required_attendees", "optional_attendees"]:
            for attendee in result.get(attendee_list, []):
                if isinstance(attendee, dict):
                    if attendee.get("name"):
                        name_val = attendee["name"]
                        if _email_re.match(name_val):
                            attendee["name"] = self.mapping.get_or_create_token("email", name_val)
                        else:
                            attendee["name"] = self.mapping.get_or_create_token("person", name_val)
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

    ALWAYS runs locally — ПДн never leave the machine.
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
        # Sort by longest token first to avoid partial replacements
        for token, value in sorted(self.token_map.items(), key=lambda x: len(x[0]), reverse=True):
            result = result.replace(token, value)

        return result

    def lookup_mask_to_name(self, mask: str) -> Optional[str]:
        """Look up a mask token to find its real value.

        Args:
            mask: Mask like [PERSON_47].

        Returns:
            Real value or None.
        """
        return self.token_map.get(mask)

    def refresh(self) -> None:
        """Force reload of mapping on next access."""
        self._token_map = None


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Quick test without NER (too slow for basic test)
    _NER_ENABLED = False

    test_text = """
    Добрый день, Иванов Алексей Петрович!
    Ваш номер телефона: +7 916 123-45-67
    Email: ivanov@example.com
    ИНН: 770708389312
    СНИЛС: 123-456-789 01
    Telegram: @ivanov_vp
    Прошу согласовать бюджет с Петровым Сергеем.
    Копию направьте Иванову А.П.
    Связаться можно через t.me/ivanov_vp
    """

    mgr = MappingManager(mapping_path=Path("/tmp/test_mapping.json"))

    # Test get_or_create_token with variants
    p1 = mgr.get_or_create_token("person", "Иванов Алексей Петрович")
    p2 = mgr.get_or_create_token("person", "Иванов А.П.")
    p3 = mgr.get_or_create_token("person", "Иванов")

    print(f"Full:  {p1} → Иванов Алексей Петрович")
    print(f"Short: {p2} → should be same as {p1}: {p2 == p1}")
    print(f"Surname: {p3} → should be same as {p1}: {p3 == p1}")

    # Test TGID regex
    classifier = PIIClassifier()
    entities = classifier.classify(test_text)
    print("\n=== Entities found ===")
    for pii_type, value, start, end in sorted(entities, key=lambda e: e[2]):
        print(f"  [{pii_type}] '{value}' at {start}:{end}")

    # Test anonymization
    anonymizer = Anonymizer(ner_enabled=False)
    anon_text, has_pii = anonymizer.anonymize_text(test_text)
    print(f"\n=== Anonymized (has_pii={has_pii}) ===")
    print(anon_text)

    # Test deanonymization
    mgr.save()
    deanonymizer = Deanonymizer(mapping_path=Path("/tmp/test_mapping.json"))
    restored = deanonymizer.deanonymize(anon_text)
    print(f"\n=== Deanonymized ===")
    print(restored)

    # Test _roots_match
    print("\n=== Root matching ===")
    tests = [
        ("Иванов", "Иванова", True),
        ("Петров", "Петровым", True),
        ("Krylov", "Krylovу", True),
        ("Иванов", "Петров", False),
        ("Вика", "Вике", True),
        ("Сидоров", "Сидоровна", True),
    ]
    for w1, w2, expected in tests:
        result = _roots_match(w1, w2)
        status = "✓" if result == expected else "✗"
        print(f"  {status} _roots_match('{w1}', '{w2}') = {result} (expected {expected})")

    # Test NER if enabled
    if _NER_ENABLED:
        print("\n=== NER Test (qwen3:14b) ===")
        names = ner_extract_persons(test_text)
        print(f"  Names found: {names}")