from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGraphicsOpacityEffect, QApplication
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.highlight_card import HighlightCard
from db import get_highlight_entries


class HighlightWindow(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("highlightwindow")
        self._build_ui()
        self._connect_signals()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.setAutoFillBackground(True)

        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)

        title_label = QLabel("Highlights")
        title_label.setObjectName("highlightpagetitle")
        top_row.addWidget(title_label)
        top_row.addStretch()
        root_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("highlightscrollarea")
        self.scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.entries_container = QWidget()
        self.entries_container.setObjectName("highlightentriescontainer")
        self.entries_container.setAttribute(Qt.WA_StyledBackground, True)
        self.entries_layout = QVBoxLayout(self.entries_container)
        self.entries_layout.setSpacing(16)
        self.entries_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.entries_container)
        root_layout.addWidget(self.scroll_area)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)

    def refresh_entries_from_db(self) -> None:
        self._clear_entries()
        rows = get_highlight_entries()

        if not rows:
            empty_label = QLabel("No finished games with reviews yet.")
            empty_label.setObjectName("highlightempty")
            empty_label.setAlignment(Qt.AlignCenter)
            self.entries_layout.addWidget(empty_label)
            return

        for row in rows:
            card = HighlightCard(row)
            self.entries_layout.addWidget(card)

    def _clear_entries(self) -> None:
        while self.entries_layout.count():
            item = self.entries_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self.refresh_entries_from_db()
        QApplication.processEvents()   # let the new cards' layout activate first, same as Index/Diary
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()