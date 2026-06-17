# Sprint 004 — Configure Wizard & Enhanced Mode

**Версия:** 0.1.3  
**Дата:** 2026-05-21  
**Цель:** Progressive Disclosure Configure Wizard + Cloud Model Support (Enhanced Mode)

---

## Приоритеты

| # | Задача | Приоритет | Оценка |
|---|--------|----------|--------|
| 1 | Configure Wizard Progressive Disclosure | P0 | 3 дня |
| 2 | Multi-provider Model Support (Enhanced Mode) | P0 | 5-8 дней |
| 3 | Provider Abstraction (Ollama/OpenAI/Anthropic) | P0 | 3 дня |
| 4 | Context Scrubbing Pass (GREEN→CLOUD) | P0 | 2 дня |
| 5 | Privacy UX (dry-run, data flow labels) | P1 | 2 дня |
| 6 | Cloud Model Fallback (auto-degradation) | P1 | 1 день |
| 7 | API Key → Keychain (не config.yaml) | P1 | 1 день |
| 8 | Audit Log (что отправлено куда) | P2 | 1 день |
| 9 | `the-jarvice model switch` команда | P1 | 1 день |
| 10 | `the-jarvice summarize --dry-run` | P1 | 1 день |

---

## 1. Configure Wizard — Progressive Disclosure

### Уровни конфигурации

**Level 0 — Минимальный (по умолчанию):**
```bash
the-jarvice configure
```
3 обязательных поля:
1. Exchange email (автодетект сервера)
2. Exchange password → Keychain
3. Telegram bot token → Keychain

Остальное автодетект: Ollama (localhost:11434), chat_id (getUpdates), model (qwen3:14b)

**Level 1 — Models:**
```bash
the-jarvice configure --models
```
Выбор: Ollama (local) / Claude (Anthropic) / GPT (OpenAI)
Если cloud → API key → Keychain + privacy confirmation

**Level 2 — Advanced:**
```bash
the-jarvice configure --advanced
```
Temperature, max_tokens, custom endpoints, PII settings

### Privacy Confirmation Screen

```
⚠ Переключение на Claude (Anthropic API)

Что происходит с вашими данными:
  ✅ Персональные данные (имена, email) → остаются локально (RED директория)
  ✅ Обезличенный контент (GREEN) → отправляется в Anthropic API
  ✅ Сводки → генерируются удалённо, хранятся локально

Продолжить? [y/N]
```

### Реализация

- Переписать `configure()` в `cli/main.py`
- Новая функция `_configure_basic()`, `_configure_models()`, `_configure_advanced()`
- `autodetect_chat_id()` и `detect_exchange_server()` — подключить в wizard
- Typer Rich panels для каждого шага

---

## 2. Multi-Provider Model Support (Enhanced Mode)

### ModelsConfig расширение

```yaml
models:
  provider: ollama  # ollama | openai | anthropic | google
  primary: qwen3:14b
  fallbacks:
    - qwen2.5:7b
  system_prompt: "Ты помощник-аналитик..."
  
  # Cloud provider settings (optional)
  openai:
    api_key_service: "the-jarvice.openai"  # Keychain service name
    model: gpt-4o
  anthropic:
    api_key_service: "the-jarvice.anthropic"
    model: claude-sonnet-4-20250514
```

### Provider Abstraction

Новый модуль `core/providers.py`:

```python
class ModelProvider(ABC):
    @abstractmethod
    def summarize(self, text: str, system_prompt: str) -> str: ...
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, str]: ...

class OllamaProvider(ModelProvider): ...
class OpenAIProvider(ModelProvider): ...
class AnthropicProvider(ModelProvider): ...
```

Каждый провайдер:
- Обрабатывает свой API формат
- Retry с exponential backoff (особенно 429 для cloud)
- Fallback на следующий провайдер в цепочке
- Логирует вызовы в audit log

### Auto-degradation

```python
# В _generate_summary():
try:
    result = provider.summarize(text, system_prompt)
except (ProviderUnavailableError, RateLimitError):
    logger.warning(f"Provider {provider.name} unavailable, falling back to {fallback.name}")
    result = fallback.summarize(text, system_prompt)
```

---

## 3. Context Scrubbing Pass

Перед отправкой GREEN данных в cloud:

```python
def scrub_for_cloud(green_text: str, context_level: str = "standard") -> str:
    """Remove re-identification vectors from anonymized text.
    
    Even with [PERSON_N] masking, job title + org + context
    can identify individuals. This pass removes:
    - Job titles combined with organization names
    - Unique project names (< 5 team members)
    - Specific budget figures
    - Meeting room names / internal codes
    """
```

Уровни:
- `standard` — убирает комбинации title+org
- `strict` — убирает все специфичные детали, оставляет только общую тему

---

## 4. Audit Log

Новый `~/.the-jarvice/audit.log`:

```json
{"ts": "2026-05-21T14:30:00Z", "action": "summarize", "provider": "anthropic", "model": "claude-sonnet-4-20250514", "items": 5, "tokens_in": 1200, "tokens_out": 300, "green_path": "~/.the-jarvice/data/pii/GREEN/2026-05-21.json"}
```

---

## 5. CLI команды

```bash
the-jarvice configure              # Level 0: email + password + bot token
the-jarvice configure --models     # Level 1: model provider selection
the-jarvice configure --advanced   # Level 2: full config
the-jarvice model switch           # Interactive model switcher
the-jarvice model list             # Show available models
the-jarvice summarize --dry-run   # Show what would be sent where
the-jarvice privacy audit          # Show data flow and active providers
```

---

## Тесты

- `test_sprint004.py`: Provider abstraction, context scrubbing, configure wizard, audit log, dry-run
- Цель: 270+ тестов (238 текущущих + 32+ новых)

---

## Не в этом спринте

- Knowledge Mode (The Brain) → Sprint 005
- Монетизация / оплата
- Web dashboard / TUI
- Per-domain trust levels
- Streaming responses