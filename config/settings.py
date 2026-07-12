import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


RAWG_PROXY_BASE_URL = "https://gimbo-rawg-proxy.mahandaryagard01.workers.dev"