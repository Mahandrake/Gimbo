from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class PhotoThumbnail(QFrame):
    """One cell in the AlbumWindow grid. Clicking it opens PhotoViewerModal."""

    clicked = Signal(str)  # emits the screenshot's file path

    THUMB_W = 220
    THUMB_H = 140

    def __init__(self, screenshot_path: str, parent=None):
        super().__init__(parent)
        self._path = screenshot_path
        self.setObjectName("photothumbnail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.image_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(self._path) if self._path else QPixmap()
        if pixmap.isNull():
            self.image_label.setText("Image not found")
        else:
            scaled = pixmap.scaled(
                self.THUMB_W, self.THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

        layout.addWidget(self.image_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._path:
            self.clicked.emit(self._path)
        super().mousePressEvent(event)