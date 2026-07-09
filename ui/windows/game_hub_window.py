# ui/pages/game_hub_window.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, Signal
from ui.factories import UiFactory
from ui.widgets.animated_buttons import AnimatedButton, SimpleButton
from config.settings import BASE_DIR


class GameHubWindow(QWidget):
    back_requested = Signal()
    journal_requested = Signal()
    index_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gamehub")
        self._build_ui()
        self._connect_signals()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)

        # top row: back button only
        top_row = QHBoxLayout()
        self.back_btn = SimpleButton("← Back", "animatedbutton", w=120, h=30)
        top_row.addWidget(self.back_btn)
        top_row.addStretch()  # pushes back button to the left

        root_layout.addLayout(top_row)

        # game buttons row
        btn_row = QHBoxLayout()
        self.journal_btn = AnimatedButton("Journal", str(BASE_DIR / "assets" / "gifs" / "journal.png"),
                                          "animatedbutton",
                                          225, 240)
        self.index_btn = AnimatedButton("Index", str(BASE_DIR / "assets" / "gifs" / "index.png"), "animatedbutton", 225,
                                        240)  # <-- was a local var, now self.index_btn
        highlight_btn = AnimatedButton("Highlight", str(BASE_DIR / "assets" / "gifs" / "highlight.png"),
                                       "animatedbutton", 225, 240)
        photobook_btn = AnimatedButton("Photo Book", str(BASE_DIR / "assets" / "gifs" / "photobook.png"),
                                       "animatedbutton", 225, 240)

        btn_row.addWidget(self.journal_btn)
        btn_row.addWidget(self.index_btn)
        btn_row.addWidget(highlight_btn)
        btn_row.addWidget(photobook_btn)

        root_layout.addStretch()
        root_layout.addLayout(btn_row)
        root_layout.addStretch()

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.journal_btn.clicked.connect(self.journal_requested.emit)
        self.index_btn.clicked.connect(self.index_requested.emit)

    def show_with_fade(self, duration_ms: int = 400) -> None:
        self._opacity_effect.setOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
