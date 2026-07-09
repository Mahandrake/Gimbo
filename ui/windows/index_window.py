from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QGraphicsOpacityEffect, QLabel, QApplication
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.game_card import GameCard
from db import get_all_games


class IndexWindow(QWidget):
    back_requested = Signal()
    game_selected = Signal(dict)

    CARD_COLUMNS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("indexwindow")
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
        top_row.addStretch()
        root_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("indexscrollarea")
        self.scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("indexcardscontainer")
        self.cards_container.setAttribute(Qt.WA_StyledBackground, True)
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setSpacing(24)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)

    def refresh_entries_from_db(self) -> None:
        """Pull all games from SQLite and rebuild the card grid."""
        rows = get_all_games()
        entries = [self._row_to_entry(row) for row in rows]
        self.load_entries(entries)

    def _row_to_entry(self, row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "text": row["description"] or "",
            "image_path": row["cover_path"],
            "meta": row["platform"] or "",
        }

    def load_entries(self, entries: list[dict]) -> None:
        self._clear_cards()

        if not entries:
            empty_label = QLabel("No games journaled yet.")
            empty_label.setObjectName("indexempty")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        for i, entry in enumerate(entries):
            card = GameCard(entry)
            card.clicked.connect(self.game_selected.emit)
            row, col = divmod(i, self.CARD_COLUMNS)
            self.grid_layout.addWidget(card, row, col)

    def _clear_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self.refresh_entries_from_db()
        QApplication.processEvents()   # let the new cards' layout activate first
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()