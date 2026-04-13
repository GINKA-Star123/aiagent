"""Project path definitions placeholder."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
CHARACTER_DIR = DATA_DIR / "characters"