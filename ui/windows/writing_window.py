from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QSpinBox, QFileDialog, QGraphicsOpacityEffect
)
from ui.widgets.animated_buttons import SimpleButton


class WritingPage(QWidget):
    back_requested = Signal()
    session_saved = Signal(dict)  # emits the finished session entry

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("writingpage")
        self._current_game = None       # holds the selected game's dict
        self._screenshot_path = None    # optional, set via file picker

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

        # --- screenshot row (optional) ---
        screenshot_row = QHBoxLayout()
        self.add_screenshot_btn = SimpleButton("Add Screenshot", "animatedbutton", w=250, h=32)
        self.remove_screenshot_btn = SimpleButton("Remove", "animatedbutton", w=100, h=32)
        self.remove_screenshot_btn.setVisible(False)

        self.screenshot_preview = QLabel()
        self.screenshot_preview.setObjectName("screenshotpreview")
        self.screenshot_preview.setFixedSize(160, 90)
        self.screenshot_preview.setAlignment(Qt.AlignCenter)
        self.screenshot_preview.setVisible(False)

        screenshot_row.addWidget(self.add_screenshot_btn)
        screenshot_row.addWidget(self.remove_screenshot_btn)
        screenshot_row.addWidget(self.screenshot_preview)
        screenshot_row.addStretch()
        root_layout.addLayout(screenshot_row)

        root_layout.addStretch()

        # --- save button, bottom-right ---
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = SimpleButton("Save Session", "animatedbutton", w=250, h=36)
        save_row.addWidget(self.save_btn)
        root_layout.addLayout(save_row)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.add_screenshot_btn.clicked.connect(self._pick_screenshot)
        self.remove_screenshot_btn.clicked.connect(self._clear_screenshot)
        self.save_btn.clicked.connect(self._save_session)

    def set_game(self, game: dict) -> None:
        """Call this before showing the page, to tell it which game the session belongs to."""
        self._current_game = game
        self.game_title_label.setText(game.get("title", ""))
        # reset fields for a fresh session entry
        self.session_text.clear()
        self.hours_spin.setValue(0)
        self.minutes_spin.setValue(0)
        self._clear_screenshot()

    def _pick_screenshot(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Screenshot", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._screenshot_path = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.screenshot_preview.width(),
                    self.screenshot_preview.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.screenshot_preview.setPixmap(scaled)
                self.screenshot_preview.setVisible(True)
                self.remove_screenshot_btn.setVisible(True)

    def _clear_screenshot(self):
        self._screenshot_path = None
        self.screenshot_preview.clear()
        self.screenshot_preview.setVisible(False)
        self.remove_screenshot_btn.setVisible(False)

    def _save_session(self):
        if self._current_game is None:
            return  # safety guard — shouldn't happen if navigation is wired correctly

        session_entry = {
            "game_id": self._current_game.get("id"),
            "text": self.session_text.toPlainText().strip(),
            "playtime_minutes": self.hours_spin.value() * 60 + self.minutes_spin.value(),
            "screenshot_path": self._screenshot_path,
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