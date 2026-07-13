from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _CenteredImageLabel(QLabel):
    """Paints its pixmap manually, computing the centered (x, y) position
    itself instead of relying on QLabel's built-in setPixmap()/setAlignment()
    centering - which was rendering some images slightly off-center in a way
    that depended on the image (aspect ratio / DPI metadata), not on our
    layout math. Manually drawing removes that dependency entirely."""

    def __init__(self, w: int, h: int, parent=None):
        super().__init__(parent)
        self._w = w
        self._h = h
        self.setFixedSize(w, h)
        self.setAlignment(Qt.AlignCenter)  # still used for the "Image not found" text fallback
        self._scaled_pixmap = None

    def set_image(self, pixmap: QPixmap) -> None:
        self._scaled_pixmap = pixmap.scaled(
            self._w, self._h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.update()

    def paintEvent(self, event):
        if self._scaled_pixmap is None or self._scaled_pixmap.isNull():
            super().paintEvent(event)  # normal QLabel text painting for "Image not found"
            return

        painter = QPainter(self)
        x = (self.width() - self._scaled_pixmap.width()) // 2
        y = (self.height() - self._scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, self._scaled_pixmap)


class PhotoThumbnail(QFrame):
    """One cell in the AlbumWindow grid (also reused read-only in DiaryWindow's
    session cards). Clicking the image opens PhotoViewerModal. If deletable=True
    and a screenshot_id is given, a small remove button is shown too."""

    clicked = Signal(str)  # emits the screenshot's file path
    delete_requested = Signal(int)  # emits the screenshot's db id

    THUMB_W = 220
    THUMB_H = 140

    def __init__(self, screenshot_path: str, parent=None, deletable: bool = False, screenshot_id: int = None):
        super().__init__(parent)
        self._path = screenshot_path
        self._screenshot_id = screenshot_id
        self.setObjectName("photothumbnail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui(deletable)

        margins = 12
        extra_top_row_height = 24 if deletable else 0
        self.setFixedSize(
            self.THUMB_W + margins,
            self.THUMB_H + margins + extra_top_row_height,
        )

    def _build_ui(self, deletable: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignHCenter)

        if deletable:
            top_row = QHBoxLayout()
            top_row.addStretch()
            self.remove_btn = _ClickableLabel("✕")
            self.remove_btn.setObjectName("sessionscreenshotremove")
            self.remove_btn.setCursor(Qt.PointingHandCursor)
            self.remove_btn.setFixedSize(20, 20)
            self.remove_btn.setAlignment(Qt.AlignCenter)
            self.remove_btn.setAttribute(Qt.WA_NoMousePropagation, True)
            self.remove_btn.clicked.connect(self._on_remove_clicked)
            top_row.addWidget(self.remove_btn)
            layout.addLayout(top_row)

        self.image_label = _CenteredImageLabel(self.THUMB_W, self.THUMB_H)

        pixmap = QPixmap(self._path) if self._path else QPixmap()
        if pixmap.isNull():
            self.image_label.setText("Image not found")
        else:
            self.image_label.set_image(pixmap)

        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

    def _on_remove_clicked(self):
        if self._screenshot_id is not None:
            self.delete_requested.emit(self._screenshot_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._path:
            self.clicked.emit(self._path)
        super().mousePressEvent(event)