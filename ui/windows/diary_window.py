from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGraphicsOpacityEffect, QApplication,
    QTextEdit, QSpinBox, QFileDialog
)

from ui.widgets.animated_buttons import SimpleButton
from ui.widgets.photo_thumbnail import PhotoThumbnail
from ui.widgets.confirm_modal import ConfirmModal
from ui.windows.photo_viewer_modal import PhotoViewerModal
from db import (
    get_sessions_for_game, get_reviews_for_game, get_screenshots_for_session,
    update_session, delete_session, update_review, delete_review,
    add_screenshot_to_session, delete_screenshot,
)


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

        self.viewer_modal = PhotoViewerModal(self)
        self.confirm_modal = ConfirmModal(self)

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

    # ------------------------------------------------------------------
    # Session cards (edit notes/playtime + manage screenshots + delete)
    # ------------------------------------------------------------------

    def _build_session_card(self, row) -> QFrame:
        card = QFrame()
        card.setObjectName("diarycard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        outer_layout = QVBoxLayout(card)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        initial_screenshots = get_screenshots_for_session(row["id"])
        has_initial_screenshots = bool(initial_screenshots)

        upper = QWidget()
        upper.setObjectName("diarycardupper" if has_initial_screenshots else "diarycardupperfull")
        upper.setAttribute(Qt.WA_StyledBackground, True)
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(24, 24, 24, 24)
        upper_layout.setSpacing(6)

        # --- header row: title + edit/delete buttons ---
        header_row = QHBoxLayout()
        header = QLabel(f"Session · {row['created_at']}")
        header.setObjectName("diarycardheader")
        header_row.addWidget(header)
        header_row.addStretch()
        edit_btn = SimpleButton("Edit", "animatedbutton", w=80, h=26)
        delete_btn = SimpleButton("Delete", "animatedbutton", w=90, h=26)
        header_row.addWidget(edit_btn)
        header_row.addWidget(delete_btn)
        upper_layout.addLayout(header_row)

        # --- display widgets ---
        minutes = row["duration_minutes"] or 0
        hours, mins = divmod(minutes, 60)
        playtime_label = QLabel(f"Played {hours}h {mins}m")
        playtime_label.setObjectName("diarycardmeta")
        upper_layout.addWidget(playtime_label)

        notes_label = QLabel(row["notes"] or "")
        notes_label.setObjectName("diarycardtext")
        notes_label.setWordWrap(True)
        upper_layout.addWidget(notes_label)

        # --- edit widgets for notes/playtime (hidden until Edit is clicked) ---
        edit_playtime_row = QHBoxLayout()
        edit_playtime_label = QLabel("Play time:")
        edit_playtime_label.setObjectName("sectionlabel")
        hours_spin = QSpinBox()
        hours_spin.setRange(0, 999)
        hours_spin.setSuffix(" h")
        minutes_spin = QSpinBox()
        minutes_spin.setRange(0, 59)
        minutes_spin.setSuffix(" min")
        edit_playtime_row.addWidget(edit_playtime_label)
        edit_playtime_row.addWidget(hours_spin)
        edit_playtime_row.addWidget(minutes_spin)
        edit_playtime_row.addStretch()

        notes_edit = QTextEdit()
        notes_edit.setObjectName("sessiontext")
        notes_edit.setFixedHeight(120)

        edit_action_row = QHBoxLayout()
        edit_action_row.addStretch()
        save_btn = SimpleButton("Save", "startbutton", w=90, h=28)
        cancel_btn = SimpleButton("Cancel", "animatedbutton", w=90, h=28)
        edit_action_row.addWidget(cancel_btn)
        edit_action_row.addWidget(save_btn)

        upper_layout.addLayout(edit_playtime_row)
        upper_layout.addWidget(notes_edit)
        upper_layout.addLayout(edit_action_row)

        def _set_row_layout_visible(row_layout, visible: bool):
            for i in range(row_layout.count()):
                w = row_layout.itemAt(i).widget()
                if w:
                    w.setVisible(visible)

        notes_edit.setVisible(False)
        _set_row_layout_visible(edit_playtime_row, False)
        _set_row_layout_visible(edit_action_row, False)

        outer_layout.addWidget(upper)

        # --- lower section: screenshots (view-only, or manage mode when editing) ---
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
        shots_scroll.setWidget(shots_container)

        lower_layout.addWidget(shots_scroll)
        outer_layout.addWidget(lower)

        add_shot_btn = SimpleButton("Add Screenshot(s)", "animatedbutton", w=180, h=90)

        def clear_shots_row():
            while shots_row_layout.count():
                item = shots_row_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        def on_delete_screenshot_clicked(screenshot_id: int):
            def _confirm():
                delete_screenshot(screenshot_id)
                rebuild_shots_row(True)
            self.confirm_modal.open_modal(
                title="Delete Screenshot",
                message="Are you sure you want to delete this screenshot? This cannot be undone.",
                confirm_text="Delete",
                on_confirm=_confirm,
            )

        def rebuild_shots_row(editing: bool):
            clear_shots_row()
            current_screenshots = get_screenshots_for_session(row["id"])
            for s in current_screenshots:
                thumb = PhotoThumbnail(
                    s["screenshot_path"],
                    deletable=editing,
                    screenshot_id=s["id"] if editing else None,
                )
                thumb.clicked.connect(self.viewer_modal.open_photo)
                if editing:
                    thumb.delete_requested.connect(on_delete_screenshot_clicked)
                shots_row_layout.addWidget(thumb)

            if editing:
                shots_row_layout.addWidget(add_shot_btn)

            lower.setVisible(bool(current_screenshots) or editing)

        def on_add_screenshot_clicked():
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Screenshot(s)", "", "Images (*.png *.jpg *.jpeg *.webp)"
            )
            for path in paths:
                add_screenshot_to_session(row["id"], path)
            if paths:
                rebuild_shots_row(True)

        add_shot_btn.clicked.connect(on_add_screenshot_clicked)
        rebuild_shots_row(False)  # initial view-only render

        def set_edit_mode(on: bool):
            header.setVisible(not on)
            edit_btn.setVisible(not on)
            delete_btn.setVisible(not on)
            playtime_label.setVisible(not on)
            notes_label.setVisible(not on)

            notes_edit.setVisible(on)
            _set_row_layout_visible(edit_playtime_row, on)
            _set_row_layout_visible(edit_action_row, on)

            rebuild_shots_row(on)

        def on_edit_clicked():
            hours_spin.setValue(hours)
            minutes_spin.setValue(mins)
            notes_edit.setPlainText(row["notes"] or "")
            set_edit_mode(True)

        def on_cancel_clicked():
            set_edit_mode(False)

        def on_save_clicked():
            update_session(row["id"], {
                "text": notes_edit.toPlainText().strip(),
                "playtime_minutes": hours_spin.value() * 60 + minutes_spin.value(),
            })
            self.refresh_entries_from_db()

        def on_delete_clicked():
            self.confirm_modal.open_modal(
                title="Delete Session",
                message="Are you sure you want to delete this session? This cannot be undone.",
                confirm_text="Delete",
                on_confirm=lambda: self._delete_session(row["id"]),
            )

        edit_btn.clicked.connect(on_edit_clicked)
        cancel_btn.clicked.connect(on_cancel_clicked)
        save_btn.clicked.connect(on_save_clicked)
        delete_btn.clicked.connect(on_delete_clicked)

        return card

    def _delete_session(self, session_id: int) -> None:
        delete_session(session_id)
        self.refresh_entries_from_db()

    # ------------------------------------------------------------------
    # Review cards (edit rating/body + delete)
    # ------------------------------------------------------------------

    def _build_review_card(self, row) -> QFrame:
        card = QFrame()
        card.setObjectName("diaryreviewcard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        rating = row["rating"]
        header = QLabel(f"Review · {row['created_at']} · {rating}/10" if rating is not None else f"Review · {row['created_at']}")
        header.setObjectName("diarycardheader")
        header_row.addWidget(header)
        header_row.addStretch()
        edit_btn = SimpleButton("Edit", "animatedbutton", w=80, h=26)
        delete_btn = SimpleButton("Delete", "animatedbutton", w=90, h=26)
        header_row.addWidget(edit_btn)
        header_row.addWidget(delete_btn)
        layout.addLayout(header_row)

        body_label = QLabel(row["body"] or "")
        body_label.setObjectName("diarycardtext")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        rating_row = QHBoxLayout()
        rating_label = QLabel("Rating:")
        rating_label.setObjectName("sectionlabel")
        rating_spin = QSpinBox()
        rating_spin.setRange(1, 10)
        rating_spin.setSuffix(" / 10")
        rating_spin.setValue(rating or 1)
        rating_row.addWidget(rating_label)
        rating_row.addWidget(rating_spin)
        rating_row.addStretch()

        body_edit = QTextEdit()
        body_edit.setObjectName("sessiontext")
        body_edit.setPlainText(row["body"] or "")
        body_edit.setFixedHeight(120)

        edit_action_row = QHBoxLayout()
        edit_action_row.addStretch()
        save_btn = SimpleButton("Save", "startbutton", w=90, h=28)
        cancel_btn = SimpleButton("Cancel", "animatedbutton", w=90, h=28)
        edit_action_row.addWidget(cancel_btn)
        edit_action_row.addWidget(save_btn)

        layout.addLayout(rating_row)
        layout.addWidget(body_edit)
        layout.addLayout(edit_action_row)

        rating_label.setVisible(False)
        rating_spin.setVisible(False)
        body_edit.setVisible(False)
        save_btn.setVisible(False)
        cancel_btn.setVisible(False)

        def set_edit_mode(on: bool):
            header.setVisible(not on)
            edit_btn.setVisible(not on)
            delete_btn.setVisible(not on)
            body_label.setVisible(not on)

            rating_label.setVisible(on)
            rating_spin.setVisible(on)
            body_edit.setVisible(on)
            save_btn.setVisible(on)
            cancel_btn.setVisible(on)

        def on_edit_clicked():
            rating_spin.setValue(rating or 1)
            body_edit.setPlainText(row["body"] or "")
            set_edit_mode(True)

        def on_cancel_clicked():
            set_edit_mode(False)

        def on_save_clicked():
            update_review(row["id"], {
                "rating": rating_spin.value(),
                "body": body_edit.toPlainText().strip(),
            })
            self.refresh_entries_from_db()

        def on_delete_clicked():
            self.confirm_modal.open_modal(
                title="Delete Review",
                message="Are you sure you want to delete this review? This cannot be undone.",
                confirm_text="Delete",
                on_confirm=lambda: self._delete_review(row["id"]),
            )

        edit_btn.clicked.connect(on_edit_clicked)
        cancel_btn.clicked.connect(on_cancel_clicked)
        save_btn.clicked.connect(on_save_clicked)
        delete_btn.clicked.connect(on_delete_clicked)

        return card

    def _delete_review(self, review_id: int) -> None:
        delete_review(review_id)
        self.refresh_entries_from_db()

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self.refresh_entries_from_db()
        QApplication.processEvents()
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for modal in (self.viewer_modal, self.confirm_modal):
            if modal.isVisible():
                modal.setGeometry(self.rect())