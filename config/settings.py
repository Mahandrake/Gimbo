import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built executable: bundled files (assets/,
    # schema.sql, etc.) live in the temp/onedir extraction folder that
    # PyInstaller exposes as sys._MEIPASS, NOT next to this .py file.
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent