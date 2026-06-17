"""Context scrubbing for cloud model safety.

Even with PII anonymization ([PERSON_N], [EMAIL_N] tokens),
contextual re-identification is possible when job titles,
organization names, and unique project names appear together.

This module provides a scrubbing pass that removes or generalizes
re-identification vectors before sending GREEN data to cloud APIs.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class ScrubLevel(str, Enum):
    """Scrubbing intensity levels.

    - standard: Remove obvious re-identification vectors
      (job title + org combinations, unique project names)
    - strict: Remove all specific details, keep only general theme
      (for highly sensitive content)
    """

    STANDARD = "standard"
    STRICT = "strict"


# ── Patterns that enable re-identification ──────────────────────────────────

# Job titles combined with organization context
# e.g., "CFO of [ORG_1]" or "Директор ИТ [ORG_1]"
_JOB_TITLE_PATTERNS = [
    re.compile(
        r"(?:(?:CFO|CEO|CTO|CIO|COO|VP|Директор|Заместитель|Руководитель|Начальник|Заведующий|Глава)\s+)"
        r"(?:(?:отдела|департамента|управления|службы|направления|сектора)?\s*)?"
        r"(?:\[ORG_\d+\]|\[ORGANIZATION_\d+\])",
        re.IGNORECASE | re.UNICODE,
    ),
    # "директор по ИТ [ORG_1]" patterns
    re.compile(
        r"(?:(?:директор|руководитель|начальник|заведующий|глава)\s+по\s+\S+\s+)"
        r"(?:\[ORG_\d+\]|\[ORGANIZATION_\d+\])",
        re.IGNORECASE | re.UNICODE,
    ),
]

# Specific budget figures (strict mode only)
_BUDGET_PATTERN = re.compile(
    r"\b(\d[\d\s]*(?:млн|млрд|тыс|миллион|миллиард|тысяч)\s*(?:рублей|руб\.|₽|\$|USD|EUR))\b",
    re.IGNORECASE | re.UNICODE,
)

# Meeting room names / internal codes
_ROOM_PATTERN = re.compile(
    r"\b(?:комната|переговорка|зал|кабинет|помещение)\s+[A-Z0-9\-]+\b",
    re.IGNORECASE | re.UNICODE,
)

# Small team references (3 or fewer people)
_SMALL_TEAM_PATTERN = re.compile(
    r"(?:команда|группа|подразделение)\s+(?:из\s+)?(?:[123]\s*(?:человек|людей|участников|специалистов))",
    re.IGNORECASE | re.UNICODE,
)


def scrub_for_cloud(
    green_text: str,
    level: ScrubLevel = ScrubLevel.STANDARD,
    custom_patterns: Optional[list[re.Pattern]] = None,
) -> str:
    """Remove re-identification vectors from anonymized text.

    This pass is applied AFTER PII anonymization ([PERSON_N], [EMAIL_N])
    but BEFORE sending text to a cloud API. It removes contextual clues
    that could enable re-identification even with PII masked.

    Args:
        green_text: Anonymized text (GREEN data, already PII-masked).
        level: Scrubbing intensity.
        custom_patterns: Additional regex patterns to remove.

    Returns:
        Scrubbed text safe for cloud API submission.
    """
    result = green_text

    # 1. Remove job title + org combinations
    for pattern in _JOB_TITLE_PATTERNS:
        result = pattern.sub("[ROLE] в [ORG]", result)

    # 2. Remove meeting room names / internal codes
    result = _ROOM_PATTERN.sub("[МЕСТО]", result)

    # 3. Remove small team references
    result = _SMALL_TEAM_PATTERN.sub("[МАЛАЯ_ГРУППА]", result)

    if level == ScrubLevel.STRICT:
        # 4. Remove specific budget figures
        result = _BUDGET_PATTERN.sub("[СУММА]", result)

        # 5. Generalize remaining specific details
        # Remove specific dates (keep month/year only)
        result = re.sub(
            r"\b(\d{1,2})\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b",
            r"[ДАТА]",
            result,
            flags=re.IGNORECASE | re.UNICODE,
        )

        # Remove specific time references
        result = re.sub(
            r"\b\d{1,2}:\d{2}\b",
            "[ВРЕМЯ]",
            result,
        )

    # 6. Apply custom patterns
    if custom_patterns:
        for pattern in custom_patterns:
            result = pattern.sub("[УДАЛЕНО]", result)

    return result


def estimate_reidentification_risk(text: str) -> dict[str, int]:
    """Estimate re-identification risk of anonymized text.

    Returns a dict with counts of potential risk vectors:
    - job_title_org: job title + org combinations
    - budget_figures: specific budget amounts
    - room_names: meeting room codes
    - small_teams: references to teams of 3 or fewer
    """
    risks: dict[str, int] = {
        "job_title_org": sum(len(p.findall(text)) for p in _JOB_TITLE_PATTERNS),
        "budget_figures": len(_BUDGET_PATTERN.findall(text)),
        "room_names": len(_ROOM_PATTERN.findall(text)),
        "small_teams": len(_SMALL_TEAM_PATTERN.findall(text)),
    }
    return risks