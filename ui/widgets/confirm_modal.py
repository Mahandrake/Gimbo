from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from ui.widgets.animated_buttons import SimpleButton


class ConfirmModal(QWidget):
    """Reusable styled Yes/No confirmation overlay, used anywhere a
    QMessageBox.question() would otherwise be used (deleting games,
    sessions, reviews, screenshots, etc.)."""

    confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("confirmmodal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._on_confirm_callback = None
        self._build_ui()
        self._connect_signals()
        self.hide()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 120)
        outer_layout.setAlignment(Qt.AlignCenter)
        self._outer_layout = outer_layout

        self.card = QFrame(self)
        self.card.setObjectName("confirmcard")
        self.card.setFixedWidth(440)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        self.title_label = QLabel("Are you sure?")
        self.title_label.setObjectName("confirmtitle")
        card_layout.addWidget(self.title_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("confirmmessage")
        self.message_label.setWordWrap(True)
        card_layout.addWidget(self.message_label)

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.cancel_btn = SimpleButton("Cancel", "animatedbutton", w=100, h=32)
        self.confirm_btn = SimpleButton("Delete", "startbutton", w=100, h=32)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.confirm_btn)
        card_layout.addLayout(action_row)

        outer_layout.addWidget(self.card)

    def _connect_signals(self):
        self.cancel_btn.clicked.connect(self.close_modal)
        self.confirm_btn.clicked.connect(self._on_confirm)

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close_modal()

    def _on_confirm(self):
        self.close_modal()
        callback = self._on_confirm_callback
        self._on_confirm_callback = None
        if callback is not None:
            callback()
        self.confirmed.emit()

    def open_modal(self, title: str = "Are you sure?", message: str = "",
                   confirm_text: str = "Delete", on_confirm=None) -> None:
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.confirm_btn.label.setText(confirm_text)
        self._on_confirm_callback = on_confirm

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
