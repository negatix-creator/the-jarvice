"""The Jarvice — PII anonymization package.

Stage 1 enhancements:
  - NER via qwen3:14b (local) for extracting ФИО from text body
  - Telegram ID regex pattern
  - MappingManager variants for partial matches (Иванов → Иванова Вика)
"""

from the_jarvice.scrapers.pii.anonymizer import (
    Anonymizer,
    Deanonymizer,
    PIIClassifier,
    MappingManager,
    ner_extract_persons,
    _roots_match,
    _find_name_occurrences,
    MASK_PATTERN,
)

__all__ = [
    "Anonymizer",
    "Deanonymizer",
    "PIIClassifier",
    "MappingManager",
    "ner_extract_persons",
    "_roots_match",
    "_find_name_occurrences",
    "MASK_PATTERN",
]