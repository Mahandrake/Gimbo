import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from ui.windows.main_window import MainWindow
from config.settings import BASE_DIR
from db import init_db


def load_fonts():
    font_path = BASE_DIR / "assets" / "fonts" / "ByteBounce.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        print(f"[fonts] Failed to load font at {font_path}")
        return
    families = QFontDatabase.applicationFontFamilies(font_id)
    print(f"[fonts] Loaded '{font_path.name}' as family: {families}")


def load_stylesheet(app: QApplication):
    styles_dir = BASE_DIR / "ui" / "styles"
    with open(styles_dir / "mainwindow.qss", "r", encoding="utf-8") as file:
        app.setStyleSheet(file.read())


init_db()


def main():
    app = QApplication(sys.argv)
    load_fonts()          # <-- must happen before setStyleSheet
    load_stylesheet(app)
    window = MainWindow()
    window.showFullScreen()
    window.show_with_fade()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()