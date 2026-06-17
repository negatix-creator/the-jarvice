# Contributing to The Jarvice

Thanks for your interest! Here's how to get started.

## Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/your-org/the-jarvice.git
cd the-jarvice

# Create venv and install
python3 -m venv ~/.the-jarvice/venv
source ~/.the-jarvice/venv/bin/activate
pip install -e ".[dev]"

# Run the diagnostic suite
the-jarvice doctor

# Run tests
pytest tests/ -v

# Quick setup
bash setup.sh --check
```

## Code Style

- **Formatter:** `ruff format` (Black-compatible)
- **Linter:** `ruff check`
- **Type hints:** `mypy --strict` (optional but encouraged)

```bash
# Format and lint
ruff format .
ruff check .
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific sprint
pytest tests/test_sprint001.py -v

# With coverage
pytest tests/ --cov=the_jarvice --cov-report=term-missing
```

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Add tests for your changes
4. Ensure all tests pass: `pytest tests/`
5. Run linter: `ruff check .`
6. Submit PR with a clear description

## Reporting Issues

- Use GitHub Issues
- Include: OS, Python version, `the-jarvice doctor` output
- For security issues: see SECURITY.md (do not publicize vulnerabilities)

## Architecture

```
the_jarvice/
├── cli/main.py          # Typer CLI entry point
├── core/
│   ├── config.py        # Pydantic v2 config models
│   ├── state.py         # StateManager (cursors, error tracking)
│   ├── doctor.py        # 12 diagnostic checks
│   ├── providers.py     # LLM provider abstraction (Ollama, OpenAI, Anthropic)
│   ├── context_scrubber.py  # PII context scrubbing (standard/strict)
│   ├── log_utils.py     # Log sanitization
│   └── keyring_utils.py # Keychain/keyring + env var fallback
├── scrapers/
│   ├── base.py          # BaseScraper ABC
│   ├── exchange/        # Exchange EWS scraper
│   ├── teams/            # Teams IC3 scraper
│   └── pii/              # RED/GREEN anonymization pipeline
└── VERSION               # Single source of truth for version
```

## Adding a Scraper

1. Create `the_jarvice/scrapers/my_scraper/`
2. Extend `BaseScraper` with `scrape()` and `test_connection()`
3. Add config model in `core/config.py`
4. Add tests in `tests/test_sprintXXX.py`
5. Register in `cli/main.py` `run()` command

## License

MIT — see [LICENSE](LICENSE)