import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


RAWG_BASE_URL = "https://api.rawg.io/api"

def _load_rawg_api_key() -> str:
    key = os.environ.get("RAWG_API_KEY", "")
    if key:
        return key
    local_key_file = BASE_DIR / "config" / "rawg_api_key.txt"
    if local_key_file.exists():
        return local_key_file.read_text(encoding="utf-8").strip()
    return ""

RAWG_API_KEY = _load_rawg_api_key()