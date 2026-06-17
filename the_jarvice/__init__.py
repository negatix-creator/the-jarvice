"""The Jarvice — Local-first AI assistant for corporate data summaries."""

from importlib.metadata import version as _version

try:
    __version__ = _version("the-jarvice")
except Exception:
    __version__ = "0.2.0"