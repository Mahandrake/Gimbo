from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from ui.widgets.animated_buttons import SimpleButton


class PhotoViewerModal(QWidget):
    """Big (not fullscreen) preview of a single screenshot."""

    MAX_W = 900
    MAX_H = 650

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("photoviewermodal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()
        self.hide()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 60)
        outer_layout.setAlignment(Qt.AlignCenter)
        self._outer_layout = outer_layout

        self.card = QFrame(self)
        self.card.setObjectName("photoviewercard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.addStretch()
        self.close_btn = SimpleButton("Close", "animatedbutton", w=100, h=30)
        self.close_btn.clicked.connect(self.close_modal)
        top_row.addWidget(self.close_btn)
        card_layout.addLayout(top_row)

        self.image_label = QLabel()
        self.image_label.setObjectName("photoviewerimage")
        self.image_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.image_label)

        outer_layout.addWidget(self.card)

    def mousePressEvent(self, event):
        # click the dimmed backdrop (outside the card) to close, same as AddEntryModal
        if not self.card.geometry().contains(event.pos()):
            self.close_modal()

    def open_photo(self, screenshot_path: str) -> None:
        pixmap = QPixmap(screenshot_path)
        if pixmap.isNull():
            self.image_label.setText("Image not found")
            self.card.setFixedSize(400, 200)
        else:
            scaled = pixmap.scaled(
                self.MAX_W, self.MAX_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            # card hugs the image size (+ padding/close row) instead of a fixed box
            self.card.setFixedSize(scaled.width() + 32, scaled.height() + 65)

        top_level = self.window()
        if top_level is not None:
            self.setParent(top_level)
            self.setGeometry(top_level.rect())

            titlebar = getattr(top_level, "titlebar", None)
            titlebar_height = titlebar.height() if titlebar is not None else 0
            self._outer_layout.setContentsMargins(0, titlebar_height, 0, 60)

        self.show()
        self.raise_()

    def close_modal(self):
        self.hide()