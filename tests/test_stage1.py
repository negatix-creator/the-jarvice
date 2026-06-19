#!/usr/bin/env python3
"""PII Anonymizer — Stage 1 Integration Test.

Tests the three Stage 1 enhancements:
1. NER via qwen3:14b (local) for person name extraction
2. Telegram ID regex
3. MappingManager variants for partial matches

Usage:
    python3 test_stage1.py [--ner] [--verbose]

    --ner      Enable NER (slow, ~60-90 seconds per text)
    --verbose  Show detailed entity matches
"""

import json
import sys
import time
from pathlib import Path

# Direct module import to avoid package dependency chain
import importlib.util
_mod_path = Path(__file__).parent.parent / "the_jarvice" / "scrapers" / "pii" / "anonymizer.py"
_spec = importlib.util.spec_from_file_location("anonymizer", str(_mod_path))
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

PIIClassifier = mod.PIIClassifier
MappingManager = mod.MappingManager
Anonymizer = mod.Anonymizer
Deanonymizer = mod.Deanonymizer
_roots_match = mod._roots_match
_find_name_occurrences = mod._find_name_occurrences


# ── Test Data ──────────────────────────────────────────────────────────────

TEST_TEXTS = {
    "russian_email": """
    Добрый день, Иванов Алексей Петрович!
    Ваш номер телефона: +7 916 123-45-67
    Email: ivanov@fsk.ru
    ИНН: 770708389312
    СНИЛС: 123-456-789 01
    Прошу согласовать бюджет с Петровым Сергеем.
    Копию направьте Иванову А.П.
    """,
    "telegram_ids": """
    Пишите в Telegram: @ivanov_vp
    Также доступен по ссылке t.me/ivanov_vp
    Telegram ID: 123456789
    Связь через @support_bot
    """,
    "calendar_item": {
        "subject": "Встреча с Ивановым А.П.",
        "body": "Обсуждение бюджета с Крыльцовым Дмитрием. Телефон: +7 903 222-33-44",
        "sender": {"name": "Петров Сергей", "email": "petrov@fsk.ru"},
        "recipients": [
            {"name": "Иванов А.П.", "email": "ivanov@fsk.ru"},
            {"name": "Крыльцов Дмитрий", "email": "kryltsov@fsk.ru"},
        ],
    },
}


# ── Root Matching Tests ────────────────────────────────────────────────────

def test_roots_match():
    """Test Russian morphological root matching."""
    cases = [
        ("Иванов", "Иванова", True),
        ("Иванов", "Ивановым", True),
        ("Иванов", "Иванову", True),
        ("Петров", "Петровым", True),
        ("Крыльцов", "Крыльцову", True),
        ("Иванов", "Петров", False),
        ("Вика", "Вике", True),
        ("Сидоров", "Сидоровна", True),
        ("Сергей", "Сергеем", True),
        ("Дмитрий", "Дмитрию", True),
        ("Алексей", "Алексеем", True),
        ("Сергей", "Сергеевич", True),
        ("Москва", "Москве", True),
    ]

    passed = 0
    failed = 0
    for w1, w2, expected in cases:
        result = _roots_match(w1, w2)
        if result == expected:
            passed += 1
            print(f"  ✓ _roots_match('{w1}', '{w2}') = {result}")
        else:
            failed += 1
            print(f"  ✗ _roots_match('{w1}', '{w2}') = {result} (expected {expected})")

    print(f"\nRoot matching: {passed} passed, {failed} failed")
    return failed == 0


# ── Variant Matching Tests ─────────────────────────────────────────────────

def test_variant_matching():
    """Test MappingManager variant matching for Russian names."""
    import tempfile, os
    mapping_path = Path(tempfile.mktemp(suffix=".json"))

    mgr = MappingManager(mapping_path=mapping_path)

    # Create full name first
    p1 = mgr.get_or_create_token("person", "Иванов Алексей Петрович")
    cases = [
        ("Иванов А.П.", p1, "Initials match"),
        ("Иванов", p1, "Surname match"),
        ("Иванову А.П.", p1, "Declined initials"),
    ]

    # Create another person
    p2 = mgr.get_or_create_token("person", "Крыльцов Дмитрий")
    cases.extend([
        ("Крыльцову Дмитрию", p2, "Declined full name"),
        ("Крыльцов", p2, "Surname only"),
    ])

    # Declined first, then nominative
    p3 = mgr.get_or_create_token("person", "Петровым Сергеем")
    cases.extend([
        ("Петров Сергей", p3, "Nominative after declined"),
    ])

    passed = 0
    failed = 0
    for name, expected_token, desc in cases:
        result = mgr.get_or_create_token("person", name)
        if result == expected_token:
            passed += 1
            print(f"  ✓ {desc}: '{name}' → {result}")
        else:
            failed += 1
            print(f"  ✗ {desc}: '{name}' → {result} (expected {expected_token})")

    # Clean up
    try:
        os.unlink(mapping_path)
    except OSError:
        pass

    print(f"\nVariant matching: {passed} passed, {failed} failed")
    return failed == 0


# ── Telegram ID Tests ─────────────────────────────────────────────────────

def test_telegram_ids():
    """Test Telegram ID regex patterns."""
    classifier = PIIClassifier()

    text = TEST_TEXTS["telegram_ids"]
    entities = classifier.classify(text)

    tg_entities = [(t, v) for t, v, s, e in entities if t == "tgid"]

    # Expected: @ivanov_vp, @ivanov_vp (from t.me link), 123456789
    # @support_bot might or might not be excluded
    print(f"  Found {len(tg_entities)} Telegram entities:")
    for t, v in tg_entities:
        print(f"    [{t}] {v}")

    # Check we found at least the main ones
    found_usernames = [v for t, v in tg_entities if v.startswith("@")]
    found_numeric = [v for t, v in tg_entities if v.isdigit()]

    passed = 0
    failed = 0

    if any("ivanov" in v.lower() for v in found_usernames):
        passed += 1
        print(f"  ✓ Found @ivanov_vp")
    else:
        failed += 1
        print(f"  ✗ Missing @ivanov_vp")

    if found_numeric:
        passed += 1
        print(f"  ✓ Found numeric TG ID: {found_numeric}")
    else:
        failed += 1
        print(f"  ✗ Missing numeric TG ID")

    print(f"\nTelegram IDs: {passed} passed, {failed} failed")
    return failed == 0


# ── Regex Classification Tests ─────────────────────────────────────────────

def test_regex_classification():
    """Test regex-based PII detection."""
    classifier = PIIClassifier()

    text = TEST_TEXTS["russian_email"]
    entities = classifier.classify(text)

    types_found = {}
    for pii_type, value, start, end in entities:
        types_found.setdefault(pii_type, []).append(value)

    print("  Entities found by type:")
    for pii_type, values in sorted(types_found.items()):
        for v in values:
            print(f"    [{pii_type}] {v}")

    passed = 0
    failed = 0

    # Check expected types
    for expected_type in ["phone", "email", "inn", "snils"]:
        if expected_type in types_found:
            passed += 1
            print(f"  ✓ Found {expected_type}")
        else:
            failed += 1
            print(f"  ✗ Missing {expected_type}")

    print(f"\nRegex classification: {passed} passed, {failed} failed")
    return failed == 0


# ── Anonymization Round-Trip Test ──────────────────────────────────────────

def test_anonymization_roundtrip():
    """Test full anonymize → deanonymize round-trip."""
    import tempfile, os
    mapping_path = Path(tempfile.mktemp(suffix=".json"))

    anonymizer = Anonymizer(ner_enabled=False, mapping_path=mapping_path)
    text = TEST_TEXTS["russian_email"]

    # Anonymize
    anon_text, has_pii = anonymizer.anonymize_text(text)
    print(f"  has_pii: {has_pii}")

    # Check that PII is replaced with masks
    passed = 0
    failed = 0

    if "+7" not in anon_text:
        passed += 1
        print(f"  ✓ Phone masked")
    else:
        failed += 1
        print(f"  ✗ Phone NOT masked")

    if "ivanov@fsk.ru" not in anon_text:
        passed += 1
        print(f"  ✓ Email masked")
    else:
        failed += 1
        print(f"  ✗ Email NOT masked")

    if "[PERSON_" in anon_text or "[PHONE_" in anon_text or "[EMAIL_" in anon_text:
        passed += 1
        print(f"  ✓ Masks present in output")
    else:
        failed += 1
        print(f"  ✗ No masks in output")

    # Deanonymize
    anonymizer.mapping.save()
    deanon = Deanonymizer(mapping_path=mapping_path)
    restored = deanon.deanonymize(anon_text)

    # Check that real values are restored
    if "+7 916 123-45-67" in restored:
        passed += 1
        print(f"  ✓ Phone restored")
    else:
        failed += 1
        print(f"  ✗ Phone NOT restored")

    if "ivanov@fsk.ru" in restored:
        passed += 1
        print(f"  ✓ Email restored")
    else:
        failed += 1
        print(f"  ✗ Email NOT restored")

    # Clean up
    try:
        os.unlink(mapping_path)
    except OSError:
        pass

    print(f"\nRound-trip: {passed} passed, {failed} failed")
    return failed == 0


# ── NER Test (optional, slow) ──────────────────────────────────────────────

def test_ner():
    """Test NER via local qwen3:14b (slow!)."""
    print("\n  ⏳ Running NER (qwen3:14b, ~60-90 seconds)...")

    start = time.time()
    names = mod.ner_extract_persons(TEST_TEXTS["russian_email"])
    elapsed = time.time() - start

    print(f"  NER took {elapsed:.1f}s")
    print(f"  Names found: {names}")

    # Check that key names are found
    passed = 0
    failed = 0

    # At least some names should be found
    if len(names) > 0:
        passed += 1
        print(f"  ✓ Found {len(names)} names")
    else:
        failed += 1
        print(f"  ✗ No names found")

    # Check for "Иванов" in some form
    if any("Иванов" in n or "иванов" in n.lower() for n in names):
        passed += 1
        print(f"  ✓ Found 'Иванов' variant")
    else:
        failed += 1
        print(f"  ✗ Missing 'Иванов' variant")

    print(f"\nNER: {passed} passed, {failed} failed")
    return failed == 0


# ── Dict Anonymization Test ────────────────────────────────────────────────

def test_dict_anonymization():
    """Test anonymization of email/calendar dict items."""
    import tempfile, os
    mapping_path = Path(tempfile.mktemp(suffix=".json"))

    anonymizer = Anonymizer(ner_enabled=False, mapping_path=mapping_path)
    item = TEST_TEXTS["calendar_item"]

    anon_item, has_pii = anonymizer.anonymize_dict(item)

    print(f"  has_pii: {has_pii}")
    print(f"  Sender name: {anon_item.get('sender', {}).get('name')}")
    print(f"  Recipient[0] name: {anon_item.get('recipients', [{}])[0].get('name')}")

    passed = 0
    failed = 0

    # Check that sender/recipient names are masked
    if "PERSON_" in str(anon_item.get("sender", {}).get("name", "")):
        passed += 1
        print(f"  ✓ Sender name masked")
    else:
        failed += 1
        print(f"  ✗ Sender name NOT masked: {anon_item.get('sender', {}).get('name')}")

    # Check that body has masked phone
    if "PHONE_" in anon_item.get("body", ""):
        passed += 1
        print(f"  ✓ Phone in body masked")
    else:
        failed += 1
        print(f"  ✗ Phone in body NOT masked")

    # Clean up
    try:
        os.unlink(mapping_path)
    except OSError:
        pass

    print(f"\nDict anonymization: {passed} passed, {failed} failed")
    return failed == 0


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    enable_ner = "--ner" in args
    verbose = "--verbose" in args

    print("=" * 60)
    print("PII Anonymizer — Stage 1 Integration Test")
    print("=" * 60)
    print(f"NER enabled: {enable_ner}")
    print()

    results = {}

    print("─" * 40)
    print("1. Root matching tests")
    print("─" * 40)
    results["roots"] = test_roots_match()

    print()
    print("─" * 40)
    print("2. Variant matching tests")
    print("─" * 40)
    results["variants"] = test_variant_matching()

    print()
    print("─" * 40)
    print("3. Telegram ID tests")
    print("─" * 40)
    results["tgid"] = test_telegram_ids()

    print()
    print("─" * 40)
    print("4. Regex classification tests")
    print("─" * 40)
    results["regex"] = test_regex_classification()

    print()
    print("─" * 40)
    print("5. Anonymization round-trip test")
    print("─" * 40)
    results["roundtrip"] = test_anonymization_roundtrip()

    print()
    print("─" * 40)
    print("6. Dict anonymization test")
    print("─" * 40)
    results["dict"] = test_dict_anonymization()

    if enable_ner:
        print()
        print("─" * 40)
        print("7. NER test (qwen3:14b)")
        print("─" * 40)
        results["ner"] = test_ner()

    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()