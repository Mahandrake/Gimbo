from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QFileDialog, QFrame, QCompleter
)
from PySide6.QtCore import QStringListModel
from ui.widgets.animated_buttons import SimpleButton
from services.rawg_client import RawgClient


class AddEntryModal(QWidget):
    entry_created = Signal(dict)  # emits {title, platform, description, image_path}
    entry_updated = Signal(dict)  # emits {id, title, platform, description, image_path}

    PLATFORMS = ["PC", "PlayStation", "Xbox", "Switch", "Mobile", "Other"]

    RAWG_KEYS = ["rawg_id", "rawg_rating", "rawg_metacritic", "rawg_playtime", "rawg_released", "rawg_genres"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("addentrymodal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._cover_path = None
        self._editing_id = None

        self._pending_rawg = {k: None for k in self.RAWG_KEYS}
        self._suggestion_map: dict[str, dict] = {}

        self.rawg_client = RawgClient(self)
        self.rawg_client.suggestions_ready.connect(self._on_suggestions_ready)
        self.rawg_client.details_ready.connect(self._on_details_ready)
        self.rawg_client.cover_ready.connect(self._on_cover_ready)
        self.rawg_client.error.connect(self._on_rawg_error)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)  # debounce - don't hit RAWG on every keystroke
        self._search_timer.timeout.connect(self._trigger_search)

        self._build_ui()
        self._connect_signals()
        self._setup_title_completer()

        self.hide()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        # Asymmetric margins bias where "center" lands: reserving more space
        # at the bottom than the top shifts the centered card upward.
        # Top margin gets adjusted dynamically in open_modal() to account
        # for the titlebar, since the backdrop now covers the whole window.
        outer_layout.setContentsMargins(0, 0, 0, 120)
        outer_layout.setAlignment(Qt.AlignCenter)
        self._outer_layout = outer_layout

        # the card is the visible form; the rest of `self` acts as the dimmed backdrop
        self.card = QFrame(self)
        self.card.setObjectName("addentrycard")
        self.card.setFixedWidth(520)
        self.card.setFixedHeight(690)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(10)

        header = QLabel("Add to Backlog")
        header.setObjectName("addentryheader")
        card_layout.addWidget(header)
        self.header_label = header

        # --- title (required) ---
        title_label = QLabel("Title")
        title_label.setObjectName("sectionlabel")
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("addentryfield")
        self.title_edit.setPlaceholderText("Game title")
        card_layout.addWidget(title_label)
        card_layout.addWidget(self.title_edit)

        # --- platform ---
        platform_label = QLabel("Platform")
        platform_label.setObjectName("sectionlabel")
        self.platform_combo = QComboBox()
        self.platform_combo.setObjectName("addentryfield")
        self.platform_combo.addItem("Select platform...")
        self.platform_combo.addItems(self.PLATFORMS)
        card_layout.addWidget(platform_label)
        card_layout.addWidget(self.platform_combo)

        # --- cover (optional) ---
        cover_label = QLabel("Cover (optional)")
        cover_label.setObjectName("sectionlabel")
        card_layout.addWidget(cover_label)

        cover_row = QHBoxLayout()
        self.cover_preview = QLabel()
        self.cover_preview.setObjectName("addentrycoverpreview")
        self.cover_preview.setFixedSize(170, 200)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setVisible(False)

        cover_btn_col = QVBoxLayout()
        self.add_cover_btn = SimpleButton("Add Cover", "animatedbutton", w=170, h=30)
        self.remove_cover_btn = SimpleButton("Remove", "animatedbutton", w=140, h=30)
        self.remove_cover_btn.setVisible(False)
        cover_btn_col.addWidget(self.add_cover_btn)
        cover_btn_col.addWidget(self.remove_cover_btn)
        cover_btn_col.addStretch()

        cover_row.addWidget(self.cover_preview)
        cover_row.addLayout(cover_btn_col)
        cover_row.addStretch()
        card_layout.addLayout(cover_row)

        self.rawg_status_label = QLabel("")
        self.rawg_status_label.setObjectName("rawgstatuslabel")
        self.rawg_status_label.setVisible(False)
        card_layout.addWidget(self.rawg_status_label)

        # --- description (optional) ---
        desc_label = QLabel("Description (optional)")
        desc_label.setObjectName("sectionlabel")
        self.description_text = QTextEdit()
        self.description_text.setObjectName("addentrydescription")
        self.description_text.setPlaceholderText("A short blurb about the game...")
        self.description_text.setFixedHeight(100)
        card_layout.addWidget(desc_label)
        card_layout.addWidget(self.description_text)

        # --- actions ---
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.cancel_btn = SimpleButton("Cancel", "animatedbutton", w=100, h=32)
        self.save_btn = SimpleButton("Save", "startbutton", w=100, h=32)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.save_btn)
        card_layout.addLayout(action_row)

        outer_layout.addWidget(self.card)

    def _setup_title_completer(self):
        self._completer_model = QStringListModel(self)
        self.title_completer = QCompleter(self._completer_model, self)
        self.title_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.title_completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.title_completer.popup().setObjectName("rawgsuggestionpopup")
        self.title_edit.setCompleter(self.title_completer)
        self.title_completer.activated[str].connect(self._on_suggestion_activated)
        self.title_edit.textEdited.connect(self._on_title_text_edited)

    def _connect_signals(self):
        self.add_cover_btn.clicked.connect(self._pick_cover)
        self.remove_cover_btn.clicked.connect(self._clear_cover)
        self.cancel_btn.clicked.connect(self.close_modal)
        self.save_btn.clicked.connect(self._save_entry)

    def mousePressEvent(self, event):
        # clicking the dimmed backdrop (i.e. outside the card) cancels the modal —
        # this also acts as a safety net: if the card is ever invisible for any
        # reason (e.g. missing QSS), you can still click anywhere to escape it
        # instead of getting stuck with an unresponsive, invisible overlay.
        if not self.card.geometry().contains(event.pos()):
            self.close_modal()

    def _on_title_text_edited(self, _text: str):
        self._search_timer.start()

    def _trigger_search(self):
        self.rawg_client.search_games(self.title_edit.text())

    def _on_suggestions_ready(self, results: list[dict]):
        self._suggestion_map.clear()
        display_strings = []
        for game in results:
            year = (game.get("released") or "")[:4]
            label = f"{game['name']} ({year})" if year else game["name"]
            # de-dupe in the unlikely case RAWG returns two identical labels
            if label in self._suggestion_map:
                label = f"{label} #{game['id']}"
            self._suggestion_map[label] = game
            display_strings.append(label)
        self._completer_model.setStringList(display_strings)

    def _on_suggestion_activated(self, label: str):
        game = self._suggestion_map.get(label)
        if not game:
            return
        self.title_edit.setText(game["name"])
        self.rawg_client.get_game_details(game["id"])

    def _on_details_ready(self, details: dict):
        self._pending_rawg = {
            "rawg_id": details.get("rawg_id"),
            "rawg_rating": details.get("rating"),
            "rawg_metacritic": details.get("metacritic"),
            "rawg_playtime": details.get("playtime"),
            "rawg_released": details.get("released"),
            "rawg_genres": details.get("genres"),
        }
        self.rawg_status_label.setText("✓ Linked via RAWG")
        self.rawg_status_label.setVisible(True)

        # Only fill the description if the user hasn't already written one -
        # never clobber their own words with RAWG's blurb.
        if not self.description_text.toPlainText().strip():
            description = (details.get("description") or "").strip()
            if description:
                self.description_text.setPlainText(description[:600])

        self.rawg_client.fetch_cover(details.get("rawg_id"), details.get("background_image"))

    def _on_cover_ready(self, _image_url: str, local_path: str):
        self._cover_path = local_path
        pixmap = QPixmap(local_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.cover_preview.width(), self.cover_preview.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cover_preview.setPixmap(scaled)
            self.cover_preview.setVisible(True)
            self.remove_cover_btn.setVisible(True)

    def _on_rawg_error(self, message: str):
        # Non-blocking - autocomplete failing shouldn't stop manual entry.
        print(f"[rawg] {message}")

    def _pick_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._cover_path = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.cover_preview.width(),
                    self.cover_preview.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.cover_preview.setPixmap(scaled)
                self.cover_preview.setVisible(True)
                self.remove_cover_btn.setVisible(True)

    def _clear_cover(self):
        self._cover_path = None
        self.cover_preview.clear()
        self.cover_preview.setVisible(False)
        self.remove_cover_btn.setVisible(False)

    def _reset_form(self):
        self.title_edit.clear()
        self.platform_combo.setCurrentIndex(0)
        self.description_text.clear()
        self._clear_cover()
        self._editing_id = None
        self.header_label.setText("Add to Backlog")
        self._pending_rawg = {k: None for k in self.RAWG_KEYS}
        self.rawg_status_label.setVisible(False)

    def _save_entry(self):
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return

        platform = (
            self.platform_combo.currentText().strip()
            if self.platform_combo.currentIndex() > 0
            else ""
        )

        entry = {
            "title": title,
            "platform": platform,
            "description": self.description_text.toPlainText().strip(),
            "image_path": self._cover_path,
            **self._pending_rawg,
        }

        if self._editing_id is not None:
            entry["id"] = self._editing_id
            self.entry_updated.emit(entry)
        else:
            self.entry_created.emit(entry)

        self.close_modal()

    # --- open/close (public API used by JournalWindow) ---

    def open_modal(self, entry: dict = None):
        self._reset_form()

        if entry:
            self._editing_id = entry.get("id")
            self.header_label.setText("Edit Game")
            self.title_edit.setText(entry.get("title", ""))

            platform = entry.get("meta") or entry.get("platform", "")
            idx = self.platform_combo.findText(platform)
            if idx > 0:
                self.platform_combo.setCurrentIndex(idx)

            self.description_text.setPlainText(entry.get("text") or entry.get("description", ""))

            image_path = entry.get("image_path")
            if image_path:
                self._cover_path = image_path
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.cover_preview.width(), self.cover_preview.height(),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.cover_preview.setPixmap(scaled)
                    self.cover_preview.setVisible(True)
                    self.remove_cover_btn.setVisible(True)

            # preserve any existing RAWG linkage until/unless the user re-picks
            if entry.get("rawg_id"):
                self._pending_rawg = {k: entry.get(k) for k in self.RAWG_KEYS}
                self.rawg_status_label.setText("✓ Linked via RAWG")
                self.rawg_status_label.setVisible(True)

        top_level = self.window()
        if top_level is not None:
            self.setParent(top_level)
            self.setGeometry(top_level.rect())
            titlebar = getattr(top_level, "titlebar", None)
            titlebar_height = titlebar.height() if titlebar is not None else 0
            self._outer_layout.setContentsMargins(0, titlebar_height, 0, 120)

        self.show()
        self.raise_()

    def close_modal(self):
        self.hide()