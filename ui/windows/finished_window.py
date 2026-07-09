from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QSpinBox, QGraphicsOpacityEffect
)
from ui.widgets.animated_buttons import SimpleButton


class FinishedPage(QWidget):
    back_requested = Signal()
    review_saved = Signal(dict)  # emits the finished game's overall review

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("writingpage")
        self._current_game = None

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

        # --- rating ---
        rating_row = QHBoxLayout()
        rating_label = QLabel("Rating:")
        rating_label.setObjectName("sectionlabel")

        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 10)
        self.rating_spin.setSuffix(" / 10")
        self.rating_spin.setObjectName("ratingspin")

        rating_row.addWidget(rating_label)
        rating_row.addWidget(self.rating_spin)
        rating_row.addStretch()
        root_layout.addLayout(rating_row)

        # --- overall thoughts ---
        thoughts_label = QLabel("Overall thoughts:")
        thoughts_label.setObjectName("sectionlabel")
        root_layout.addWidget(thoughts_label)

        self.thoughts_text = QTextEdit()
        self.thoughts_text.setObjectName("sessiontext")
        self.thoughts_text.setPlaceholderText("What did you think of the game overall?")
        self.thoughts_text.setFixedHeight(200)
        root_layout.addWidget(self.thoughts_text)

        root_layout.addStretch()

        # --- save button, bottom-right ---
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = SimpleButton("Save Review", "animatedbutton", w=200, h=36)
        save_row.addWidget(self.save_btn)
        root_layout.addLayout(save_row)

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.save_btn.clicked.connect(self._save_review)

    def set_game(self, game: dict) -> None:
        """Call this before showing the page, to tell it which game is being reviewed."""
        self._current_game = game
        self.game_title_label.setText(game.get("title", ""))
        self.rating_spin.setValue(1)
        self.thoughts_text.clear()

    def _save_review(self):
        if self._current_game is None:
            return

        review_entry = {
            "game_id": self._current_game.get("id"),
            "rating": self.rating_spin.value(),
            "text": self.thoughts_text.toPlainText().strip(),
        }
        self.review_saved.emit(review_entry)

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self._opacity_effect.setOpacity(0.0)
        QTimer.singleShot(0, lambda: self._start_fade(duration_ms))

    def _start_fade(self, duration_ms: int) -> None:
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()