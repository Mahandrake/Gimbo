from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel

from config.settings import BASE_DIR


class HighlightCard(QFrame):
    """One row in HighlightWindow: cover on the left, review/rating/stats on the right."""

    COVER_W = 180
    COVER_H = 220

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setObjectName("highlightcard")
        self.setAttribute(Qt.WA_StyledBackground, True)
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

        title_label = QLabel(row["title"])
        title_label.setObjectName("highlighttitle")
        details_col.addWidget(title_label)

        rating = row["rating"]
        rating_text = f"{rating} / 10" if rating is not None else "Not rated"
        meta_label = QLabel(self._build_meta_text(row, rating_text))
        meta_label.setObjectName("highlightmeta")
        meta_label.setWordWrap(True)
        details_col.addWidget(meta_label)

        review_label = QLabel(row["body"] or "No review written.")
        review_label.setObjectName("highlightreview")
        review_label.setWordWrap(True)
        details_col.addWidget(review_label)

        details_col.addStretch()
        layout.addLayout(details_col, stretch=1)

    def _build_meta_text(self, row, rating_text) -> str:
        total_minutes = row["total_minutes"] or 0
        hours, mins = divmod(total_minutes, 60)
        session_count = row["session_count"] or 0
        platform = row["platform"] or ""

        parts = [rating_text, f"{hours}h {mins}m played", f"{session_count} session(s)"]
        if platform:
            parts.append(platform)
        return " · ".join(parts)