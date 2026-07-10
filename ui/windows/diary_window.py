from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGraphicsOpacityEffect, QApplication
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.photo_thumbnail import PhotoThumbnail
from ui.windows.photo_viewer_modal import PhotoViewerModal
from db import get_sessions_for_game, get_reviews_for_game, get_screenshots_for_session


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

        # same convention as AlbumWindow: parented to self, reparented to
        # the top-level window when a screenshot is actually opened
        self.viewer_modal = PhotoViewerModal(self)

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
        outer_layout = QVBoxLayout(card)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # gather screenshots: new multi-screenshot table first, fall back
        # to the legacy single screenshot_path column for old sessions
        screenshots = get_screenshots_for_session(row["id"])
        paths = [s["screenshot_path"] for s in screenshots]
        if not paths and row["screenshot_path"]:
            paths = [row["screenshot_path"]]

        # --- upper section: context (same look as before) ---
        upper = QWidget()
        upper.setObjectName("diarycardupper" if paths else "diarycardupperfull")
        upper.setAttribute(Qt.WA_StyledBackground, True)
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(24, 24, 24, 24)
        upper_layout.setSpacing(6)

        header = QLabel(f"Session · {row['created_at']}")
        header.setObjectName("diarycardheader")
        upper_layout.addWidget(header)

        minutes = row["duration_minutes"] or 0
        hours, mins = divmod(minutes, 60)
        playtime_label = QLabel(f"Played {hours}h {mins}m")
        playtime_label.setObjectName("diarycardmeta")
        upper_layout.addWidget(playtime_label)

        notes_label = QLabel(row["notes"] or "")
        notes_label.setObjectName("diarycardtext")
        notes_label.setWordWrap(True)
        upper_layout.addWidget(notes_label)

        outer_layout.addWidget(upper)

        # --- lower section: screenshots, dark blueish, horizontal scroll ---
        if paths:
            lower = QFrame()
            lower.setObjectName("diarycardlower")
            lower.setAttribute(Qt.WA_StyledBackground, True)
            lower_layout = QVBoxLayout(lower)
            lower_layout.setContentsMargins(16, 16, 16, 16)

            shots_scroll = QScrollArea()
            shots_scroll.setObjectName("diarycardshotsscroll")
            shots_scroll.setAttribute(Qt.WA_StyledBackground, True)
            shots_scroll.viewport().setAttribute(Qt.WA_StyledBackground, True)
            shots_scroll.setWidgetResizable(True)
            shots_scroll.setFrameShape(QScrollArea.NoFrame)
            shots_scroll.setFixedHeight(200)
            shots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            shots_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            shots_container = QWidget()
            shots_container.setAttribute(Qt.WA_StyledBackground, True)
            shots_row_layout = QHBoxLayout(shots_container)
            shots_row_layout.setSpacing(12)
            shots_row_layout.setAlignment(Qt.AlignLeft)

            for path in paths:
                thumb = PhotoThumbnail(path)
                thumb.clicked.connect(self.viewer_modal.open_photo)
                shots_row_layout.addWidget(thumb)

            shots_scroll.setWidget(shots_container)
            lower_layout.addWidget(shots_scroll)

            outer_layout.addWidget(lower)

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