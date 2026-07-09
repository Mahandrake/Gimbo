from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.game_card import GameCard
from db import get_all_games


class PhotoFilterModal(QWidget):
    """Clickable grid of game covers (same visual language as IndexWindow).
    Picking a cover filters the album to that game; picking 'All Photos'
    clears the filter."""

    game_filter_selected = Signal(object)  # emits an entry dict, or None for "all"

    CARD_COLUMNS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("photofiltermodal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()
        self._connect_signals()
        self.hide()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 80)
        outer_layout.setAlignment(Qt.AlignCenter)
        self._outer_layout = outer_layout

        self.card = QFrame(self)
        self.card.setObjectName("photofiltercard")
        self.card.setFixedWidth(820)
        self.card.setFixedHeight(450)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(10)

        top_row = QHBoxLayout()
        header = QLabel("Filter by Game")
        header.setObjectName("photofilterheader")
        top_row.addWidget(header)
        top_row.addStretch()
        self.close_btn = SimpleButton("Close", "animatedbutton", w=100, h=30)
        top_row.addWidget(self.close_btn)
        card_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("photofilterscrollarea")
        self.scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.cards_container = QWidget()
        self.cards_container.setAttribute(Qt.WA_StyledBackground, True)
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.cards_container)
        card_layout.addWidget(self.scroll_area)

        outer_layout.addWidget(self.card)

    def _connect_signals(self):
        self.close_btn.clicked.connect(self.close_modal)

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close_modal()

    def _row_to_entry(self, row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "text": row["description"] or "",
            "image_path": row["cover_path"],
            "meta": row["platform"] or "",
        }

    def _load_games(self) -> None:
        self._clear_cards()

        all_entry = {"id": None, "title": "All Photos", "text": "", "image_path": None, "meta": ""}
        entries = [all_entry] + [self._row_to_entry(row) for row in get_all_games()]

        for i, entry in enumerate(entries):
            card = GameCard(entry)
            card.clicked.connect(self._on_card_clicked)
            row, col = divmod(i, self.CARD_COLUMNS)
            self.grid_layout.addWidget(card, row, col)

    def _clear_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_card_clicked(self, entry: dict) -> None:
        selected = None if entry.get("id") is None else entry
        self.game_filter_selected.emit(selected)
        self.close_modal()

    def open_modal(self):
        self._load_games()

        top_level = self.window()
        if top_level is not None:
            self.setParent(top_level)
            self.setGeometry(top_level.rect())

            titlebar = getattr(top_level, "titlebar", None)
            titlebar_height = titlebar.height() if titlebar is not None else 0
            self._outer_layout.setContentsMargins(0, titlebar_height, 0, 80)

        self.show()
        self.raise_()

    def close_modal(self):
        self.hide()