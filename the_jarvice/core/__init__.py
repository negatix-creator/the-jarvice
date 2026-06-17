"""The Jarvice — core modules."""

from .config import JarviceConfig, load_config, save_config, generate_openclaw_config
from .state import StateManager
from .scraper_base import BaseScraper, ScrapeResult

__all__ = [
    "JarviceConfig",
    "load_config",
    "save_config",
    "generate_openclaw_config",
    "StateManager",
    "BaseScraper",
    "ScrapeResult",
]