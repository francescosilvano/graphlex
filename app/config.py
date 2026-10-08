"""
Configuration file for Complex Systems Network Analysis (packaged)
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import json

# Load environment variables from .env file (project root)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # dotenv is optional at runtime
    pass

# --- USER SETTINGS ---
bundled_settings_path = Path(__file__).parent / "settings.json"
project_settings_path = bundled_settings_path.parent.parent / "settings.json"
configured_settings_path = os.getenv("GRAPHLEX_SETTINGS_FILE")
if configured_settings_path:
    settings_path = Path(configured_settings_path).expanduser()
elif project_settings_path.exists():
    settings_path = project_settings_path
else:
    settings_path = bundled_settings_path

try:
    with open(settings_path, "r", encoding="utf-8") as f:
        user_settings = json.load(f)
except OSError as exc:
    raise RuntimeError(
        f"Unable to read settings file '{settings_path}'."
    ) from exc
except json.JSONDecodeError as exc:
    raise ValueError(
        f"Settings file '{settings_path}' contains invalid JSON."
    ) from exc


def _keyword_group(name):
    values = user_settings.get(name, [])
    if not isinstance(values, list):
        raise ValueError(
            f"Keyword group '{name}' in '{settings_path}' must be a JSON array."
        )
    cleaned = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Keyword group '{name}' in '{settings_path}' contains "
                "an empty or non-string keyword."
            )
        keyword = value.strip()
        if keyword.casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(keyword)
    return cleaned

FIRST_GROUP = _keyword_group("1ST_GROUP")
SECOND_GROUP = _keyword_group("2ND_GROUP")
THIRD_GROUP = _keyword_group("3RD_GROUP")

ANALYSIS_CONFIGS = [
    {
        "name": "1st_group",
        "keywords": FIRST_GROUP,
        "description": "First keyword group"
    },
    {
        "name": "1st_plus_2nd_group",
        "keywords": FIRST_GROUP + SECOND_GROUP,
        "description": "First and second keyword groups"
    },
    {
        "name": "all_groups",
        "keywords": FIRST_GROUP + SECOND_GROUP + THIRD_GROUP,
        "description": "All keyword groups"
    }
]

# Full keyword set used for collection.
KEYWORDS = FIRST_GROUP + SECOND_GROUP + THIRD_GROUP

# --- FILE PATHS ---
INPUT_FILE = user_settings.get("INPUT_FILE", "../exports/bluesky_posts_complex.csv")
OUTPUT_DIR = user_settings.get("OUTPUT_DIR", "../exports")

# --- ARCHIVE SETTINGS ---
ARCHIVE_ENABLED = user_settings.get("ARCHIVE_ENABLED", True)
ARCHIVE_DIR = user_settings.get("ARCHIVE_DIR", "../exports/runs")

# --- GRAPH ANALYSIS SETTINGS ---
MIN_CO_OCCURRENCES = user_settings.get("MIN_CO_OCCURRENCES", 1)

# --- BLUESKY API SETTINGS ---
HANDLE = os.getenv("BLUESKY_HANDLE")
PASSWORD = os.getenv("BLUESKY_PASSWORD")

# --- DATA COLLECTION FILTERS ---
LOCATION_KEYWORDS = user_settings.get("LOCATION_KEYWORDS", [])

# --- DATE RANGE ---
try:
    DATE_START = datetime.fromisoformat(
        user_settings.get("DATE_START", "2023-01-01")
    ).replace(tzinfo=timezone.utc)
    DATE_END = datetime.fromisoformat(
        user_settings.get("DATE_END", "2025-11-25")
    ).replace(tzinfo=timezone.utc)
except (TypeError, ValueError) as exc:
    raise ValueError(
        f"DATE_START and DATE_END in '{settings_path}' must use YYYY-MM-DD."
    ) from exc
