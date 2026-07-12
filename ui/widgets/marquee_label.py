from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QLabel


class MarqueeLabel(QLabel):
    """A QLabel that scrolls its text smoothly right-to-left ONLY when the
    text is wider than the label's current width - otherwise it behaves
    exactly like a normal static QLabel. Used for the Journal detail
    panel's title, since long game titles would otherwise be clipped by
    the fixed-width detail box.

    Text color/font come from the widget's own font()/palette() (set via
    QSS on this label's objectName as usual) - this widget only changes
    HOW the text is drawn when it overflows, not its styling.
    """

    SPEED_PX_PER_TICK = 1
    TICK_MS = 30
    PAUSE_MS = 1200   # pause before a scroll cycle starts, so short-overflow titles aren't jittery
    GAP_PX = 40       # blank gap between the end of one loop and the start of the next

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text or ""
        self._offset = 0
        self._text_width = 0

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(self.TICK_MS)
        self._scroll_timer.timeout.connect(self._advance)

        self._pause_timer = QTimer(self)
        self._pause_timer.setSingleShot(True)
        self._pause_timer.timeout.connect(self._scroll_timer.start)

        self.setWordWrap(False)

    def text(self) -> str:
        return self._full_text

    def setText(self, text: str) -> None:
        # Resets scroll state on every call - covers "reset animation when
        # a new game is selected" for free, since _show_entry_details just
        # calls setText() like it always did.
        self._full_text = text or ""
        self._offset = 0
        self._scroll_timer.stop()
        self._pause_timer.stop()
        super().setText(self._full_text)
        self._check_overflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_overflow()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._scroll_timer.stop()
        self._pause_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._check_overflow()

    def _check_overflow(self):
        metrics = QFontMetrics(self.font())
        self._text_width = metrics.horizontalAdvance(self._full_text)
        overflow = self.width() > 0 and self._text_width > self.width()

        self._scroll_timer.stop()
        self._pause_timer.stop()
        self._offset = 0

        if overflow:
            super().setText("")  # paintEvent draws the text manually while scrolling
            self._pause_timer.start(self.PAUSE_MS)
        else:
            super().setText(self._full_text)
        self.update()

    def _advance(self):
        self._offset += self.SPEED_PX_PER_TICK
        if self._offset > self._text_width + self.GAP_PX:
            self._offset = 0
        self.update()

    def paintEvent(self, event):
        overflow = self._text_width > self.width()
        if not overflow:
            super().paintEvent(event)
            return

        metrics = QFontMetrics(self.font())
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        painter.setFont(self.font())
        y = (self.height() + metrics.ascent() - metrics.descent()) // 2

        x = -self._offset
        painter.drawText(x, y, self._full_text)
        # second copy after the gap makes the loop read as continuous
        painter.drawText(x + self._text_width + self.GAP_PX, y, self._full_text)
        painter.end()