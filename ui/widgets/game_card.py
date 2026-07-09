from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame

from config.settings import BASE_DIR


class GameCard(QFrame):
    """Clickable card showing a game's cover + title. Used by IndexWindow.

    Not built on SimpleButton/AnimatedButton because those are fixed-caption
    button widgets - this needs an image + title stacked, and to carry the
    game's dict payload along with the click.
    """

    clicked = Signal(dict)

    COVER_W = 170
    COVER_H = 240

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("gamecard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self._build_ui(entry)

    def _build_ui(self, entry: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("gamecardcover")
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
        self.title_label.setObjectName("gamecardtitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setFixedWidth(self.COVER_W)

        layout.addWidget(self.cover_label)
        layout.addWidget(self.title_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.entry)
        super().mousePressEvent(event)