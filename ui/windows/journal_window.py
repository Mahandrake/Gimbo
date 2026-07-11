from PySide6.QtCore import QPropertyAnimation, Signal, Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap, QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect,
    QListView, QLabel, QFrame, QSizePolicy
)
from ui.widgets.confirm_modal import ConfirmModal
from ui.windows.archive_window import ArchiveWindow
from config.settings import BASE_DIR
from ui.widgets.animated_buttons import SimpleButton
from ui.windows.add_entry_modal import AddEntryModal
from db import (
    create_game, update_game, delete_game,
    get_journal_games, archive_game, set_game_tracked,
    get_tracked_count, game_has_review,
)


class JournalWindow(QWidget):
    back_requested = Signal()
    entry_opened = Signal(dict)
    start_requested = Signal(dict)
    finished_requested = Signal(dict)
    view_requested = Signal(dict)

    # Highlight color for tracked games in the backlog list - a single
    # named constant so it's easy to re-theme later without touching the
    # model-population logic.
    TRACKED_ITEM_COLOR = "#FF3B3B"

    MAX_TRACKED_GAMES = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("journalwindow")
        self._build_ui()
        self._connect_signals()
        self._current_entry = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        # modals are parented to `self` so they overlay this page only,
        # rather than being registered as pages in the QStackedWidget
        self.add_entry_modal = AddEntryModal(self)
        self.confirm_modal = ConfirmModal(self)
        self.archive_window = ArchiveWindow(self)
        self.add_entry_modal.entry_created.connect(self._on_entry_created)
        self.add_entry_modal.entry_updated.connect(self._on_entry_updated)
        self.archive_window.game_restored.connect(self.refresh_entries_from_db)

        self.refresh_entries_from_db()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.setAutoFillBackground(True)

        # --- top row: back button + archive list button ---
        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)
        self.archive_list_btn = SimpleButton("Archive List", "animatedbutton", w=190, h=30)
        top_row.addWidget(self.archive_list_btn)
        root_layout.addLayout(top_row)

        # --- main content row: list+buttons on left, detail box on right ---
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        # LEFT COLUMN: list + action buttons stacked vertically
        left_col = QVBoxLayout()

        self.entry_model = QStandardItemModel(self)
        self.entry_view = QListView()
        self.entry_view.setObjectName("entryview")
        self.entry_view.setModel(self.entry_model)
        self.entry_view.setSpacing(4)
        self.entry_view.setEditTriggers(QListView.NoEditTriggers)
        self.entry_view.setFixedWidth(600)
        self.entry_view.setFixedHeight(550)
        left_col.addWidget(self.entry_view)

        # button row under the list
        button_row = QHBoxLayout()
        self.add_btn = SimpleButton("Add", "animatedbutton", w=60, h=30)
        self.edit_btn = SimpleButton("Edit", "animatedbutton", w=60, h=30)
        self.delete_btn = SimpleButton("Delete", "animatedbutton", w=95, h=30)
        self.view_btn = SimpleButton("View", "startbutton", w=80, h=30)
        for btn in (self.add_btn, self.edit_btn, self.delete_btn, self.view_btn):
            button_row.addWidget(btn)
        left_col.addLayout(button_row)

        left_col.addStretch()

        # RIGHT SIDE: detail box
        self.detail_box = QFrame()
        self.detail_box.setObjectName("detailbox")
        self.detail_box.setFrameShape(QFrame.StyledPanel)
        detail_layout = QVBoxLayout(self.detail_box)
        self.detail_box.setFixedWidth(720)
        self.detail_box.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding
        )

        top_section = QHBoxLayout()
        top_section.setSpacing(16)

        cover_col = QVBoxLayout()

        self.detail_image = QLabel()
        self.detail_image.setObjectName("detailimage")
        self.detail_image.setAlignment(Qt.AlignCenter)
        self.detail_image.setFixedSize(170, 240)
        self.detail_image.setScaledContents(False)
        cover_col.addWidget(self.detail_image)

        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("detailmeta")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setAlignment(Qt.AlignTop)
        cover_col.addWidget(self.detail_meta)

        cover_col.addStretch()

        right_col = QVBoxLayout()

        self.detail_title = QLabel("Select an entry")
        self.detail_title.setObjectName("detailtitle")

        self.detail_text = QLabel("")
        self.detail_text.setObjectName("detailtext")
        self.detail_text.setWordWrap(True)
        self.detail_text.setAlignment(Qt.AlignTop)

        self.start_btn = SimpleButton("Start", "startbutton", w=100, h=36)
        self.start_btn.setVisible(False)
        self.finished_btn = SimpleButton("Finished", "startbutton", w=150, h=36)
        self.finished_btn.setVisible(False)
        self.track_btn = SimpleButton("Track", "startbutton", w=120, h=36)
        self.track_btn.setVisible(False)
        self.archive_btn = SimpleButton("Archive", "startbutton", w=130, h=36)
        self.archive_btn.setVisible(False)

        right_col.addWidget(self.detail_title)
        right_col.addWidget(self.detail_text)
        right_col.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(self.start_btn)
        bottom_row.addWidget(self.finished_btn)
        bottom_row.addWidget(self.track_btn)
        bottom_row.addWidget(self.archive_btn)

        top_section.addLayout(cover_col)
        top_section.addLayout(right_col, stretch=1)

        detail_layout.addLayout(top_section)
        detail_layout.addStretch()
        detail_layout.addLayout(bottom_row)

        content_row.addLayout(left_col, stretch=1)
        content_row.addWidget(self.detail_box, stretch=2)

        root_layout.addLayout(content_row)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.archive_list_btn.clicked.connect(self._on_archive_list_clicked)
        self.entry_view.clicked.connect(self._on_entry_clicked)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.finished_btn.clicked.connect(self._on_finished_clicked)
        self.track_btn.clicked.connect(self._on_track_clicked)
        self.archive_btn.clicked.connect(self._on_archive_clicked)
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.view_btn.clicked.connect(self._on_view_clicked)

    def _on_archive_list_clicked(self):
        self.archive_window.open_modal()

    def _on_add_clicked(self):
        self.add_entry_modal.open_modal()

    def _on_entry_created(self, entry: dict) -> None:
        """Receives the dict emitted by AddEntryModal.entry_created, persists it
        to SQLite, then adds it to the list using the real database id."""
        game_id = create_game(entry)
        entry = dict(entry)
        entry["id"] = game_id
        entry.setdefault("text", entry.get("description", ""))
        entry.setdefault("meta", entry.get("platform", ""))
        self.add_entry(entry)

    def _on_edit_clicked(self):
        if self._current_entry:
            self.add_entry_modal.open_modal(self._current_entry)

    def _on_entry_updated(self, entry: dict) -> None:
        """Receives the dict emitted by AddEntryModal.entry_updated, persists
        the change to SQLite, and refreshes the list + clears the selection."""
        game_id = entry.get("id")
        if game_id is None:
            return
        update_game(game_id, entry)
        self._clear_selection()
        self.refresh_entries_from_db()

    def _on_delete_clicked(self):
        if not self._current_entry:
            return

        title = self._current_entry.get("title", "this game")
        game_id = self._current_entry.get("id")
        self.confirm_modal.open_modal(
            title="Delete Game",
            message=f'Are you sure you want to delete "{title}"? This cannot be undone.',
            confirm_text="Delete",
            on_confirm=lambda: self._delete_game(game_id),
        )

    def _delete_game(self, game_id) -> None:
        delete_game(game_id)
        self._clear_selection()
        self.refresh_entries_from_db()

    def _on_archive_clicked(self):
        if not self._current_entry:
            return

        game_id = self._current_entry.get("id")
        self.confirm_modal.open_modal(
            title="Archive Game",
            message="Move this game to the archive?",
            confirm_text="Yes",
            on_confirm=lambda: self._archive_game(game_id),
        )

    def _archive_game(self, game_id) -> None:
        archive_game(game_id)
        self._clear_selection()
        self.refresh_entries_from_db()

    def _on_track_clicked(self):
        if not self._current_entry:
            return

        game_id = self._current_entry.get("id")
        is_tracked = bool(self._current_entry.get("is_tracked"))

        if is_tracked:
            set_game_tracked(game_id, False)
        else:
            if get_tracked_count() >= self.MAX_TRACKED_GAMES:
                self.confirm_modal.open_modal(
                    title="Track Limit Reached",
                    message=(
                        f"You can only track up to {self.MAX_TRACKED_GAMES} games at "
                        f"a time. Untrack another game first."
                    ),
                    confirm_text="OK",
                    show_cancel=False,
                )
                return
            set_game_tracked(game_id, True)

        self._clear_selection()
        self.refresh_entries_from_db()

    def _clear_selection(self) -> None:
        """Resets the detail panel back to its empty state after an edit/delete/
        archive/track action."""
        self._current_entry = None
        self.detail_title.setText("Select an entry")
        self.detail_text.setText("")
        self.detail_meta.setText("")
        self.detail_image.clear()
        self.start_btn.setVisible(False)
        self.finished_btn.setVisible(False)
        self.track_btn.setVisible(False)
        self.archive_btn.setVisible(False)

    def _on_finished_clicked(self):
        if self._current_entry:
            self.finished_requested.emit(self._current_entry)

    def _on_view_clicked(self):
        if self._current_entry:
            self.view_requested.emit(self._current_entry)

    def _on_entry_clicked(self, index):
        entry_data = index.data(Qt.UserRole)
        if entry_data:
            self._current_entry = entry_data
            self._show_entry_details(entry_data)
            self.entry_opened.emit(entry_data)

    def _on_start_clicked(self):
        if self._current_entry:
            self.start_requested.emit(self._current_entry)

    def _show_entry_details(self, entry: dict) -> None:
        self.detail_title.setText(entry.get("title", ""))
        self.detail_text.setText(entry.get("text", ""))
        self.detail_meta.setText(entry.get("meta", ""))

        self.start_btn.setVisible(True)
        self.finished_btn.setVisible(True)
        self.track_btn.setVisible(True)
        self._refresh_track_button_label(entry)

        self.archive_btn.setVisible(game_has_review(entry.get("id")))

        image_path = entry.get("image_path")
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.detail_image.width() or 400,
                    self.detail_image.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.detail_image.setPixmap(scaled)
            else:
                self.detail_image.clear()
                self.detail_image.setText("Image not found")
                image_path = str(BASE_DIR / "assets" / 'gifs' / "index.png")
                pixmap = QPixmap(image_path)
                scaled = pixmap.scaled(
                    self.detail_image.width() or 400,
                    self.detail_image.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.detail_image.setPixmap(scaled)
        else:
            self.detail_image.clear()
            image_path = str(BASE_DIR / "assets" / 'gifs' / "index.png")
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                self.detail_image.width() or 400,
                self.detail_image.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.detail_image.setPixmap(scaled)

    def _refresh_track_button_label(self, entry: dict) -> None:
        is_tracked = bool(entry.get("is_tracked"))
        self.track_btn.label.setText("Untrack" if is_tracked else "Track")

    def load_entries(self, entries: list[dict]) -> None:
        self.entry_model.clear()
        for entry in entries:
            item = QStandardItem(entry["title"])
            item.setData(entry, Qt.UserRole)
            item.setEditable(False)
            if entry.get("is_tracked"):
                item.setForeground(QBrush(QColor(self.TRACKED_ITEM_COLOR)))
            self.entry_model.appendRow(item)

    def add_entry(self, entry: dict) -> None:
        item = QStandardItem(entry["title"])
        item.setData(entry, Qt.UserRole)
        item.setEditable(False)
        if entry.get("is_tracked"):
            item.setForeground(QBrush(QColor(self.TRACKED_ITEM_COLOR)))
        self.entry_model.insertRow(0, item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for modal in (self.add_entry_modal, self.confirm_modal, self.archive_window):
            if modal.isVisible():
                modal.setGeometry(self.rect())

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self.refresh_entries_from_db()
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def refresh_entries_from_db(self) -> None:
        """Pull non-archived games from SQLite and repopulate the list."""
        rows = get_journal_games()
        entries = [self._row_to_entry(row) for row in rows]
        self.load_entries(entries)

    def _row_to_entry(self, row) -> dict:
        """Translate a sqlite3.Row from the `games` table into this page's dict shape."""
        return {
            "id": row["id"],
            "title": row["title"],
            "text": row["description"] or "",
            "image_path": row["cover_path"],
            "meta": row["platform"] or "",
            "is_tracked": row["is_tracked"],
        }