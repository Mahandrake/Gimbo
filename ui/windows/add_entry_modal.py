from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QFileDialog, QFrame
)
from ui.widgets.animated_buttons import SimpleButton


class AddEntryModal(QWidget):
    entry_created = Signal(dict)  # emits {title, platform, description, image_path}
    entry_updated = Signal(dict)  # emits {id, title, platform, description, image_path}

    PLATFORMS = ["PC", "PlayStation", "Xbox", "Switch", "Mobile", "Other"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("addentrymodal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._cover_path = None
        self._editing_id = None   # <-- new: None means "add" mode, an id means "edit" mode

        self._build_ui()
        self._connect_signals()

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
                        self.cover_preview.width(),
                        self.cover_preview.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.cover_preview.setPixmap(scaled)
                    self.cover_preview.setVisible(True)
                    self.remove_cover_btn.setVisible(True)

        # --- existing reparent-to-top-level logic stays exactly the same ---
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