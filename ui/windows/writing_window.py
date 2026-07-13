from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QSpinBox, QFileDialog, QGraphicsOpacityEffect, QScrollArea, QFrame
)
from ui.widgets.animated_buttons import SimpleButton


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _ScreenshotThumb(QFrame):
    """One removable thumbnail in the session's screenshot strip."""

    remove_requested = Signal(str)

    THUMB_W = 150
    THUMB_H = 90

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self.setObjectName("sessionscreenshotthumb")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(self.THUMB_W, self.THUMB_H + 26)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.addStretch()
        self.remove_btn = _ClickableLabel("✕")
        self.remove_btn.setObjectName("sessionscreenshotremove")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setAlignment(Qt.AlignCenter)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._path))
        top_row.addWidget(self.remove_btn)
        layout.addLayout(top_row)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.THUMB_W - 8, self.THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("Image not found")
        layout.addWidget(self.image_label)


class WritingPage(QWidget):
    back_requested = Signal()
    session_saved = Signal(dict)  # emits the finished session entry

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("writingpage")
        self._current_game = None
        self._screenshot_paths: list[str] = []   # <-- now a list, unlimited

        self._build_ui()
        self._connect_signals()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.setAutoFillBackground(True)

        # --- top row: back button + game title ---
        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)

        self.game_title_label = QLabel("")
        self.game_title_label.setObjectName("writingtitle")
        top_row.addWidget(self.game_title_label)
        top_row.addStretch()

        root_layout.addLayout(top_row)

        # --- session notes ---
        notes_label = QLabel("What happened in this session?")
        notes_label.setObjectName("sectionlabel")
        root_layout.addWidget(notes_label)

        self.session_text = QTextEdit()
        self.session_text.setObjectName("sessiontext")
        self.session_text.setPlaceholderText("Write a paragraph or two about this play session...")
        self.session_text.setFixedHeight(180)
        root_layout.addWidget(self.session_text)

        # --- playtime row ---
        playtime_row = QHBoxLayout()
        playtime_label = QLabel("Play time:")
        playtime_label.setObjectName("sectionlabel")

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 999)
        self.hours_spin.setSuffix(" h")

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setSuffix(" min")

        playtime_row.addWidget(playtime_label)
        playtime_row.addWidget(self.hours_spin)
        playtime_row.addWidget(self.minutes_spin)
        playtime_row.addStretch()
        root_layout.addLayout(playtime_row)

        # --- screenshots (unlimited) ---
        screenshots_label = QLabel("Screenshots (optional)")
        screenshots_label.setObjectName("sectionlabel")
        root_layout.addWidget(screenshots_label)

        screenshot_btn_row = QHBoxLayout()
        self.add_screenshot_btn = SimpleButton("Add Screenshot(s)", "animatedbutton", w=380, h=32)
        screenshot_btn_row.addWidget(self.add_screenshot_btn)
        screenshot_btn_row.addStretch()
        root_layout.addLayout(screenshot_btn_row)

        self.screenshots_scroll = QScrollArea()
        self.screenshots_scroll.setObjectName("screenshotsscrollarea")
        self.screenshots_scroll.setAttribute(Qt.WA_StyledBackground, True)
        self.screenshots_scroll.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.screenshots_scroll.setWidgetResizable(True)
        self.screenshots_scroll.setFrameShape(QScrollArea.NoFrame)
        self.screenshots_scroll.setFixedHeight(140)
        self.screenshots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.screenshots_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.screenshots_container = QWidget()
        self.screenshots_container.setAttribute(Qt.WA_StyledBackground, True)
        self.screenshots_row_layout = QHBoxLayout(self.screenshots_container)
        self.screenshots_row_layout.setSpacing(10)
        self.screenshots_row_layout.setAlignment(Qt.AlignLeft)

        self.screenshots_scroll.setWidget(self.screenshots_container)
        root_layout.addWidget(self.screenshots_scroll)

        root_layout.addStretch()

        # --- save button, bottom-right ---
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = SimpleButton("Save Session", "animatedbutton", w=250, h=36)
        save_row.addWidget(self.save_btn)
        root_layout.addLayout(save_row)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.add_screenshot_btn.clicked.connect(self._pick_screenshots)
        self.save_btn.clicked.connect(self._save_session)

    def set_game(self, game: dict) -> None:
        """Call this before showing the page, to tell it which game the session belongs to."""
        self._current_game = game
        self.game_title_label.setText(game.get("title", ""))
        # reset fields for a fresh session entry
        self.session_text.clear()
        self.hours_spin.setValue(0)
        self.minutes_spin.setValue(0)
        self._screenshot_paths = []
        self._rebuild_screenshot_thumbnails()

    def _pick_screenshots(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Screenshot(s)", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if paths:
            self._screenshot_paths.extend(paths)
            self._rebuild_screenshot_thumbnails()

    def _remove_screenshot(self, path: str):
        if path in self._screenshot_paths:
            self._screenshot_paths.remove(path)
        self._rebuild_screenshot_thumbnails()

    def _rebuild_screenshot_thumbnails(self) -> None:
        while self.screenshots_row_layout.count():
            item = self.screenshots_row_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for path in self._screenshot_paths:
            thumb = _ScreenshotThumb(path)
            thumb.remove_requested.connect(self._remove_screenshot)
            self.screenshots_row_layout.addWidget(thumb)

    def _save_session(self):
        if self._current_game is None:
            return  # safety guard — shouldn't happen if navigation is wired correctly

        session_entry = {
            "game_id": self._current_game.get("id"),
            "text": self.session_text.toPlainText().strip(),
            "playtime_minutes": self.hours_spin.value() * 60 + self.minutes_spin.value(),
            "screenshot_paths": list(self._screenshot_paths),
        }
        self.session_saved.emit(session_entry)

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()