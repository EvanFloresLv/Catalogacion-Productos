# -----------------------------------------------------------------
# Config — Logging Bootstrap
# -----------------------------------------------------------------
"""
Configures the Python logging system using LoggingSettings.

Call ``setup_logging()`` once at application startup (before any
domain logic runs) so that every logger in the process respects
the configured level and format.
"""
from __future__ import annotations

import logging
import sys

from config.settings import logging_settings


def setup_logging() -> None:
    """
    Apply LoggingSettings to the root logger.

    - Sets the root level from ``logging_settings.level`` (default INFO).
    - Adds a StreamHandler writing to *stderr* so log output never
      mixes with normal program ``print()`` output.
    - Applies per-module levels defined in ``logging_settings.module_levels``.
    """
    level = getattr(logging, logging_settings.level.upper(), logging.INFO)

    # ── Root logger ─────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers on repeated calls
    if not root.handlers:
        fmt = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
            datefmt=logging_settings.date_format,
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(fmt)
        root.addHandler(handler)

    # ── Per-module overrides ────────────────────────────────────
    for module, mod_level_str in logging_settings.module_levels.items():
        mod_level = getattr(logging, mod_level_str.upper(), level)
        logging.getLogger(module).setLevel(mod_level)

    # Quiet noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "google", "grpc"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

setup_logging()