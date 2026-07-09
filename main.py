import sys
from PySide6.QtWidgets import QApplication
from ui.windows.main_window import MainWindow
from config.settings import BASE_DIR
from db import init_db




def load_stylesheet(app : QApplication):
    styles_dir = BASE_DIR / "ui" / "styles"
    with open(styles_dir/"mainwindow.qss","r",encoding="utf-8") as file:
        app.setStyleSheet(file.read())

init_db()

def main():
    app = QApplication(sys.argv)
    load_stylesheet(app)
    window = MainWindow()
    window.showFullScreen()
    window.show_with_fade()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()