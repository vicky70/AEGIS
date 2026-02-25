"""AEGIS Desktop Monitor — App classifier.

Loads app_categories from config.yaml and provides a single lookup function.
"""

import os
import sys
import yaml

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
# Build a reverse lookup: lowercase app_name -> category
_lookup: dict[str, str] = {}


def _load() -> None:
    """Parse config.yaml and populate the lookup table."""
    global _lookup
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    categories = config.get("app_categories", {})
    for category, apps in categories.items():
        for app in apps:
            _lookup[app.lower()] = category


# Load on import
_load()


def classify(app_name: str) -> str:
    """Return the category for *app_name* (case-insensitive).

    Returns ``"neutral"`` when the app is not listed in any category.
    """
    return _lookup.get(app_name.lower(), "neutral")
