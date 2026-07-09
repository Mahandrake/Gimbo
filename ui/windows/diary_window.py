from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGraphicsOpacityEffect, QApplication
)

from ui.widgets.animated_buttons import SimpleButton
from db import get_sessions_for_game, get_reviews_for_game


class DiaryWindow(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("diarywindow")
        self._current_game = None
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

        self.game_title_label = QLabel("")
        self.game_title_label.setObjectName("diarytitle")
        top_row.addWidget(self.game_title_label)
        top_row.addStretch()
        root_layout.addLayout(top_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("diaryscrollarea")
        self.scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.entries_container = QWidget()
        self.entries_container.setObjectName("diaryentriescontainer")
        self.entries_container.setAttribute(Qt.WA_StyledBackground, True)
        self.entries_layout = QVBoxLayout(self.entries_container)
        self.entries_layout.setSpacing(16)
        self.entries_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.entries_container)
        root_layout.addWidget(self.scroll_area)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)

    def set_game(self, game: dict) -> None:
        """Call before showing the page - tells DiaryWindow which game to read."""
        self._current_game = game
        self.game_title_label.setText(game.get("title", ""))
        self.refresh_entries_from_db()

    def refresh_entries_from_db(self) -> None:
        if self._current_game is None:
            return

        self._clear_entries()
        game_id = self._current_game.get("id")

        sessions = get_sessions_for_game(game_id)
        reviews = get_reviews_for_game(game_id)

        combined = [("session", row) for row in sessions] + [("review", row) for row in reviews]
        combined.sort(key=lambda pair: pair[1]["created_at"], reverse=True)

        if not combined:
            empty_label = QLabel("Nothing written yet. Start a session or leave a review!")
            empty_label.setObjectName("diaryempty")
            empty_label.setAlignment(Qt.AlignCenter)
            self.entries_layout.addWidget(empty_label)
            return

        for kind, row in combined:
            card = self._build_session_card(row) if kind == "session" else self._build_review_card(row)
            self.entries_layout.addWidget(card)

    def _clear_entries(self) -> None:
        while self.entries_layout.count():
            item = self.entries_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_session_card(self, row) -> QFrame:
        card = QFrame()
        card.setObjectName("diarycard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        # card.setMinimumHeight(400)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)  # was 16,16,16,16
        layout.setSpacing(24)  # was 16

        text_col = QVBoxLayout()
        header = QLabel(f"Session · {row['created_at']}")
        header.setObjectName("diarycardheader")
        text_col.addWidget(header)

        minutes = row["duration_minutes"] or 0
        hours, mins = divmod(minutes, 60)
        playtime_label = QLabel(f"Played {hours}h {mins}m")
        playtime_label.setObjectName("diarycardmeta")
        text_col.addWidget(playtime_label)

        notes_label = QLabel(row["notes"] or "")
        notes_label.setObjectName("diarycardtext")
        notes_label.setWordWrap(True)
        text_col.addWidget(notes_label)
        text_col.addStretch()

        layout.addLayout(text_col, stretch=1)

        screenshot_path = row["screenshot_path"]
        if screenshot_path:
            screenshot_label = QLabel()
            screenshot_label.setObjectName("diarycardscreenshot")
            screenshot_label.setFixedSize(220, 140)
            screenshot_label.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(screenshot_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                screenshot_label.setPixmap(scaled)
            else:
                screenshot_label.setText("Image not found")
            layout.addWidget(screenshot_label)

        return card

    def _build_review_card(self, row) -> QFrame:
        card = QFrame()
        card.setObjectName("diaryreviewcard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        rating = row["rating"]
        header = QLabel(f"Review · {row['created_at']} · {rating}/10" if rating is not None else f"Review · {row['created_at']}")
        header.setObjectName("diarycardheader")
        layout.addWidget(header)

        body_label = QLabel(row["body"] or "")
        body_label.setObjectName("diarycardtext")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        return card

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