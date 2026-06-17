# Sprint 004 — Configure Wizard & Enhanced Mode

## Цель
Progressive Disclosure Configure Wizard + Cloud Model Support (Enhanced Mode)

## Статус: 🔵 В разработке

## Задачи

### P0 — Критические
- [ ] Configure Wizard Progressive Disclosure (3 уровня: basic/models/advanced)
- [ ] Multi-provider Model Support (Ollama/OpenAI/Anthropic)
- [ ] Provider Abstraction (`core/providers.py`)
- [ ] Context Scrubbing Pass (GREEN→CLOUD)

### P1 — Важные
- [ ] Privacy UX (dry-run, data flow labels, `[LOCAL]`/`[CLOUD]` markers)
- [ ] Cloud Model Fallback (auto-degradation на локальную)
- [ ] API Key → Keychain (не config.yaml)
- [ ] `the-jarvice model switch` команда
- [ ] `the-jarvice summarize --dry-run`

### P2 — Желательные
- [ ] Audit Log (что отправлено куда и когда)
- [ ] `the-jarvice privacy audit` команда

## Из предыдущих спринтов (Architecture Council fixes)
- [ ] W-03: Extract бизнес-логики из main.py в core/summarizer.py, core/delivery.py
- [ ] W-02: Prompt injection defense — input truncation, output PII check
- [ ] state.json file locking + atomic writes

## Версия
0.1.2 → 0.1.3

## Решения Product Council
- 3 тира: Private Mode → Enhanced Mode → Knowledge Mode
- Облако = "Enhanced Mode", не "Cloud Mode"
- The Brain = Phase 2 (Sprint 005)
- dry-run обязателен перед отправкой в облако
- Fallback на локальную модель автоматический