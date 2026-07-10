from PySide6.QtCore import QPropertyAnimation, Signal, Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect,
    QListView, QLabel, QFrame, QSizePolicy
)
from ui.widgets.confirm_modal import ConfirmModal
from config.settings import BASE_DIR
from ui.widgets.animated_buttons import SimpleButton
from ui.windows.add_entry_modal import AddEntryModal
from db import create_game, get_all_games, update_game, delete_game


class JournalWindow(QWidget):
    back_requested = Signal()
    entry_opened = Signal(dict)
    start_requested = Signal(dict)
    finished_requested = Signal(dict)
    view_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("journalwindow")
        self._build_ui()
        self._connect_signals()
        self._current_entry = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        # modal is parented to `self` so it overlays this page only,
        # rather than being registered as a page in the QStackedWidget
        self.add_entry_modal = AddEntryModal(self)
        self.confirm_modal = ConfirmModal(self)
        self.add_entry_modal.entry_created.connect(self._on_entry_created)
        self.add_entry_modal.entry_updated.connect(self._on_entry_updated)

        self.refresh_entries_from_db()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.setAutoFillBackground(True)

        # --- top row: back button ---
        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)
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
        self.entry_view.setFixedWidth(600)  # <- controls list width directly
        self.entry_view.setFixedHeight(550)  # <- controls list height directly
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

        left_col.addStretch()  # pushes list+buttons to the top if there's extra vertical space

        # RIGHT SIDE: detail box
        self.detail_box = QFrame()
        self.detail_box.setObjectName("detailbox")
        self.detail_box.setFrameShape(QFrame.StyledPanel)
        detail_layout = QVBoxLayout(self.detail_box)
        self.detail_box.setFixedWidth(720)  # keep width locked
        self.detail_box.setSizePolicy(
            QSizePolicy.Fixed,  # horizontal — stays at fixed width
            QSizePolicy.Expanding  # vertical — grows to fill available height
        )

        # --- top section: image+meta on the left, title+text on the right ---
        top_section = QHBoxLayout()
        top_section.setSpacing(16)

        # LEFT: cover image, with meta info stacked underneath it
        cover_col = QVBoxLayout()

        self.detail_image = QLabel()
        self.detail_image.setObjectName("detailimage")
        self.detail_image.setAlignment(Qt.AlignCenter)
        self.detail_image.setFixedSize(170, 240)  # fixed box, keeps layout stable
        self.detail_image.setScaledContents(False)
        cover_col.addWidget(self.detail_image)

        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("detailmeta")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setAlignment(Qt.AlignTop)
        cover_col.addWidget(self.detail_meta)

        cover_col.addStretch()  # keeps image+meta pinned to the top of the column

        # RIGHT: title + text
        right_col = QVBoxLayout()

        self.detail_title = QLabel("Select an entry")
        self.detail_title.setObjectName("detailtitle")

        self.detail_text = QLabel("")
        self.detail_text.setObjectName("detailtext")
        self.detail_text.setWordWrap(True)
        self.detail_text.setAlignment(Qt.AlignTop)

        self.start_btn = SimpleButton("Start", "startbutton", w=100, h=36)
        self.start_btn.setVisible(False)  # hidden until an entry is selected
        self.finished_btn = SimpleButton("Finished", "startbutton", w=150, h=36)
        self.finished_btn.setVisible(False)

        right_col.addWidget(self.detail_title)
        right_col.addWidget(self.detail_text)
        right_col.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()  # pushes everything after it to the right
        bottom_row.addWidget(self.start_btn)
        bottom_row.addWidget(self.finished_btn)

        top_section.addLayout(cover_col)
        top_section.addLayout(right_col, stretch=1)

        detail_layout.addLayout(top_section)
        detail_layout.addStretch()
        detail_layout.addLayout(bottom_row)

        # assemble: left column takes less space, detail box takes more
        content_row.addLayout(left_col, stretch=1)
        content_row.addWidget(self.detail_box, stretch=2)

        root_layout.addLayout(content_row)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.entry_view.clicked.connect(self._on_entry_clicked)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.finished_btn.clicked.connect(self._on_finished_clicked)
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.view_btn.clicked.connect(self._on_view_clicked)

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

    def _clear_selection(self) -> None:
        """Resets the detail panel back to its empty state after an edit/delete."""
        self._current_entry = None
        self.detail_title.setText("Select an entry")
        self.detail_text.setText("")
        self.detail_meta.setText("")
        self.detail_image.clear()
        self.start_btn.setVisible(False)
        self.finished_btn.setVisible(False)

    def _on_finished_clicked(self):
        if self._current_entry:
            self.finished_requested.emit(self._current_entry)

    def _on_view_clicked(self):
        if self._current_entry:
            self.view_requested.emit(self._current_entry)

    def _on_entry_clicked(self, index):
        entry_data = index.data(Qt.UserRole)
        if entry_data:
            self._current_entry = entry_data  # <-- remember selection
            self._show_entry_details(entry_data)
            self.entry_opened.emit(entry_data)

    def _on_start_clicked(self):
        if self._current_entry:
            self.start_requested.emit(self._current_entry)

    def _show_entry_details(self, entry: dict) -> None:
        self.detail_title.setText(entry.get("title", ""))
        self.detail_text.setText(entry.get("text", ""))
        self.detail_meta.setText(entry.get("meta", ""))

        self.start_btn.setVisible(True)  # reveal now that something is selected
        self.finished_btn.setVisible(True)

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
            image_path = str(BASE_DIR/"assets"/'gifs'/"index.png")
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                self.detail_image.width() or 400,
                self.detail_image.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.detail_image.setPixmap(scaled)

    def load_entries(self, entries: list[dict]) -> None:
        self.entry_model.clear()
        for entry in entries:
            item = QStandardItem(entry["title"])
            item.setData(entry, Qt.UserRole)
            item.setEditable(False)
            self.entry_model.appendRow(item)

    def add_entry(self, entry: dict) -> None:
        item = QStandardItem(entry["title"])
        item.setData(entry, Qt.UserRole)
        item.setEditable(False)
        self.entry_model.insertRow(0, item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for modal in (self.add_entry_modal, self.confirm_modal):
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
        """Pull all games from SQLite and repopulate the list."""
        rows = get_all_games()
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
        }