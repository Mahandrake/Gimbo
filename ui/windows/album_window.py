from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QGraphicsOpacityEffect, QLabel, QApplication
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.photo_thumbnail import PhotoThumbnail
from ui.widgets.confirm_modal import ConfirmModal
from ui.windows.photo_filter_modal import PhotoFilterModal
from ui.windows.photo_viewer_modal import PhotoViewerModal
from db import get_all_screenshots, delete_screenshot


class AlbumWindow(QWidget):
    back_requested = Signal()

    CARD_COLUMNS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("albumwindow")
        self._current_filter_game_id = None
        self._build_ui()
        self._connect_signals()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        self.filter_modal = PhotoFilterModal(self)
        self.filter_modal.game_filter_selected.connect(self._on_filter_selected)

        self.viewer_modal = PhotoViewerModal(self)
        self.confirm_modal = ConfirmModal(self)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.setAutoFillBackground(True)

        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)

        title_label = QLabel("Photo Book")
        title_label.setObjectName("albumpagetitle")
        top_row.addWidget(title_label)
        top_row.addStretch()

        self.filter_btn = SimpleButton("Filter", "animatedbutton", w=140, h=30)
        top_row.addWidget(self.filter_btn)
        root_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("albumscrollarea")
        self.scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.photos_container = QWidget()
        self.photos_container.setObjectName("albumphotoscontainer")
        self.photos_container.setAttribute(Qt.WA_StyledBackground, True)
        self.grid_layout = QGridLayout(self.photos_container)
        self.grid_layout.setSpacing(30)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        self.scroll_area.setWidget(self.photos_container)
        root_layout.addWidget(self.scroll_area)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.filter_btn.clicked.connect(lambda: self.filter_modal.open_modal())

    def _on_filter_selected(self, entry) -> None:
        self._current_filter_game_id = entry.get("id") if entry else None
        self.refresh_photos_from_db()

    def refresh_photos_from_db(self) -> None:
        self._clear_photos()
        rows = get_all_screenshots(self._current_filter_game_id)

        if not rows:
            empty_label = QLabel("No screenshots yet. Add some during a session!")
            empty_label.setObjectName("albumempty")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        for i, row in enumerate(rows):
            thumb = PhotoThumbnail(
                row["screenshot_path"], deletable=True, screenshot_id=row["screenshot_id"]
            )
            thumb.clicked.connect(self.viewer_modal.open_photo)
            thumb.delete_requested.connect(self._on_delete_screenshot_requested)
            r, c = divmod(i, self.CARD_COLUMNS)
            self.grid_layout.addWidget(thumb, r, c)

    def _on_delete_screenshot_requested(self, screenshot_id: int) -> None:
        self.confirm_modal.open_modal(
            title="Delete Screenshot",
            message="Are you sure you want to delete this screenshot? This cannot be undone.",
            confirm_text="Delete",
            on_confirm=lambda: self._delete_screenshot(screenshot_id),
        )

    def _delete_screenshot(self, screenshot_id: int) -> None:
        delete_screenshot(screenshot_id)
        self.refresh_photos_from_db()

    def _clear_photos(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self.refresh_photos_from_db()
        QApplication.processEvents()
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # keep any open overlay covering the full page during a resize
        for modal in (self.filter_modal, self.viewer_modal, self.confirm_modal):
            if modal.isVisible():
                modal.setGeometry(self.rect())
