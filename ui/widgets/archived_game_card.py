from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from config.settings import BASE_DIR
from ui.widgets.animated_buttons import SimpleButton


class ArchivedGameCard(QFrame):
    """One card in ArchiveWindow's grid: cover + title, plus Restore and
    Delete Permanently actions. Visually similar to GameCard, but not
    itself clickable - the two buttons drive all interaction here."""

    restore_requested = Signal(dict)
    delete_requested = Signal(dict)

    COVER_W = 170
    COVER_H = 210

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("archivedgamecard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui(entry)

    def _build_ui(self, entry: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("archivedgamecardcover")
        self.cover_label.setFixedSize(self.COVER_W, self.COVER_H)
        self.cover_label.setAlignment(Qt.AlignCenter)

        image_path = entry.get("image_path")
        pixmap = QPixmap(image_path) if image_path else QPixmap()
        if pixmap.isNull():
            pixmap = QPixmap(str(BASE_DIR / "assets" / "gifs" / "index.png"))
        scaled = pixmap.scaled(
            self.COVER_W, self.COVER_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.cover_label.setPixmap(scaled)

        self.title_label = QLabel(entry.get("title", ""))
        self.title_label.setObjectName("archivedgamecardtitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setFixedWidth(self.COVER_W)

        self.restore_btn = SimpleButton("Restore", "animatedbutton", w=170, h=26)
        self.delete_btn = SimpleButton("Delete", "animatedbutton", w=170, h=26)

        layout.addWidget(self.cover_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.restore_btn)
        layout.addWidget(self.delete_btn)

        self.restore_btn.clicked.connect(lambda: self.restore_requested.emit(self.entry))
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.entry))