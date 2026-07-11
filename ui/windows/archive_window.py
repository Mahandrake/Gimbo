from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.archived_game_card import ArchivedGameCard
from ui.widgets.confirm_modal import ConfirmModal
from db import get_archived_games, restore_game, delete_game


class ArchiveWindow(QWidget):
    """Large modal overlay listing every archived game, following the same
    reparent-to-top-level-window pattern as AddEntryModal / PhotoFilterModal.
    Owns its own DB calls for restore/delete (same pattern as HighlightWindow
    and DiaryWindow's inline card actions), and emits game_restored so the
    JournalWindow that opened it knows to refresh its own list."""

    game_restored = Signal()

    CARD_COLUMNS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("archivewindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()
        self._connect_signals()

        self.confirm_modal = ConfirmModal(self)

        self.hide()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 60)
        outer_layout.setAlignment(Qt.AlignCenter)
        self._outer_layout = outer_layout

        self.card = QFrame(self)
        self.card.setObjectName("archivecard")
        self.card.setFixedWidth(1000)
        self.card.setFixedHeight(650)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()
        header = QLabel("Archived Games")
        header.setObjectName("archiveheader")
        top_row.addWidget(header)
        top_row.addStretch()
        self.close_btn = SimpleButton("Close", "animatedbutton", w=100, h=30)
        top_row.addWidget(self.close_btn)
        card_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("archivescrollarea")
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
            "image_path": row["cover_path"],
        }

    def _load_games(self) -> None:
        self._clear_cards()
        rows = get_archived_games()
        entries = [self._row_to_entry(row) for row in rows]

        if not entries:
            empty_label = QLabel("No archived games yet.")
            empty_label.setObjectName("archiveempty")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        for i, entry in enumerate(entries):
            card = ArchivedGameCard(entry)
            card.restore_requested.connect(self._on_restore_clicked)
            card.delete_requested.connect(self._on_delete_clicked)
            row, col = divmod(i, self.CARD_COLUMNS)
            self.grid_layout.addWidget(card, row, col)

    def _clear_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_restore_clicked(self, entry: dict) -> None:
        restore_game(entry.get("id"))
        self._load_games()
        self.game_restored.emit()

    def _on_delete_clicked(self, entry: dict) -> None:
        title = entry.get("title", "this game")
        game_id = entry.get("id")
        self.confirm_modal.open_modal(
            title="Delete Permanently",
            message=(
                f'Permanently delete "{title}"? This will remove all its sessions, '
                f'screenshots, and its review. This cannot be undone.'
            ),
            confirm_text="Delete",
            on_confirm=lambda: self._delete_permanently(game_id),
        )

    def _delete_permanently(self, game_id: int) -> None:
        delete_game(game_id)
        self._load_games()

    def open_modal(self):
        self._load_games()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.confirm_modal.isVisible():
            self.confirm_modal.setGeometry(self.rect())