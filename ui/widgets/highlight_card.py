from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QTextEdit, QSpinBox
)

from config.settings import BASE_DIR
from ui.widgets.animated_buttons import SimpleButton


class HighlightCard(QFrame):
    """One row in HighlightWindow: cover on the left, review/rating/stats on
    the right. Supports inline editing of the review and delete, same pattern
    as the review cards in DiaryWindow."""

    review_updated = Signal(int, dict)   # review_id, {rating, body}
    delete_requested = Signal(int)       # review_id

    COVER_W = 180
    COVER_H = 220

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setObjectName("highlightcard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._row = row
        self._build_ui(row)

    def _build_ui(self, row):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(24)

        # --- cover (left) ---
        cover_label = QLabel()
        cover_label.setObjectName("highlightcover")
        cover_label.setFixedSize(self.COVER_W, self.COVER_H)
        cover_label.setAlignment(Qt.AlignCenter)

        cover_path = row["cover_path"]
        pixmap = QPixmap(cover_path) if cover_path else QPixmap()
        if pixmap.isNull():
            pixmap = QPixmap(str(BASE_DIR / "assets" / "gifs" / "index.png"))
        scaled = pixmap.scaled(
            self.COVER_W, self.COVER_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        cover_label.setPixmap(scaled)
        layout.addWidget(cover_label)

        # --- details (right) ---
        details_col = QVBoxLayout()
        details_col.setSpacing(6)

        header_row = QHBoxLayout()
        title_label = QLabel(row["title"])
        title_label.setObjectName("highlighttitle")
        header_row.addWidget(title_label)
        header_row.addStretch()
        self.edit_btn = SimpleButton("Edit", "animatedbutton", w=80, h=26)
        self.delete_btn = SimpleButton("Delete", "animatedbutton", w=90, h=26)
        header_row.addWidget(self.edit_btn)
        header_row.addWidget(self.delete_btn)
        details_col.addLayout(header_row)

        rating = row["rating"]
        rating_text = f"{rating} / 10" if rating is not None else "Not rated"
        self.meta_label = QLabel(self._build_meta_text(row, rating_text))
        self.meta_label.setObjectName("highlightmeta")
        self.meta_label.setWordWrap(True)
        details_col.addWidget(self.meta_label)

        self.review_label = QLabel(row["body"] or "No review written.")
        self.review_label.setObjectName("highlightreview")
        self.review_label.setWordWrap(True)
        details_col.addWidget(self.review_label)

        # --- edit widgets (hidden until Edit is clicked) ---
        rating_row = QHBoxLayout()
        rating_row_label = QLabel("Rating:")
        rating_row_label.setObjectName("sectionlabel")
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 10)
        self.rating_spin.setSuffix(" / 10")
        self.rating_spin.setValue(rating or 1)
        rating_row.addWidget(rating_row_label)
        rating_row.addWidget(self.rating_spin)
        rating_row.addStretch()

        self.body_edit = QTextEdit()
        self.body_edit.setObjectName("sessiontext")
        self.body_edit.setPlainText(row["body"] or "")
        self.body_edit.setFixedHeight(120)

        edit_action_row = QHBoxLayout()
        edit_action_row.addStretch()
        self.save_btn = SimpleButton("Save", "startbutton", w=90, h=28)
        self.cancel_btn = SimpleButton("Cancel", "animatedbutton", w=90, h=28)
        edit_action_row.addWidget(self.cancel_btn)
        edit_action_row.addWidget(self.save_btn)

        details_col.addLayout(rating_row)
        details_col.addWidget(self.body_edit)
        details_col.addLayout(edit_action_row)

        self._edit_widgets = [
            rating_row_label, self.rating_spin, self.body_edit, self.save_btn, self.cancel_btn
        ]
        for w in self._edit_widgets:
            w.setVisible(False)

        details_col.addStretch()
        layout.addLayout(details_col, stretch=1)

        self._display_widgets = [title_label, self.edit_btn, self.delete_btn, self.review_label]

        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(row["review_id"]))

    def _build_meta_text(self, row, rating_text) -> str:
        total_minutes = row["total_minutes"] or 0
        hours, mins = divmod(total_minutes, 60)
        session_count = row["session_count"] or 0
        platform = row["platform"] or ""

        parts = [rating_text, f"{hours}h {mins}m played", f"{session_count} session(s)"]
        if platform:
            parts.append(platform)
        return " · ".join(parts)

    def _set_edit_mode(self, on: bool):
        for w in self._display_widgets:
            w.setVisible(not on)
        for w in self._edit_widgets:
            w.setVisible(on)

    def _on_edit_clicked(self):
        self.rating_spin.setValue(self._row["rating"] or 1)
        self.body_edit.setPlainText(self._row["body"] or "")
        self._set_edit_mode(True)

    def _on_cancel_clicked(self):
        self._set_edit_mode(False)

    def _on_save_clicked(self):
        self.review_updated.emit(self._row["review_id"], {
            "rating": self.rating_spin.value(),
            "body": self.body_edit.toPlainText().strip(),
        })