from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QSize


class AnimatedButton(QWidget):
    clicked = Signal()

    def __init__(self, text: str, animation_path: str, objectname: str, w : int , h : int , parent=None):
        super().__init__(parent)

        self.setObjectName("AnimatedButton")
        self.width0 = w
        self.height0 = h
        self.setFixedSize(self.width0,self.height0)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self._build_ui(text, animation_path, objectname)

    def _build_ui(self, text, animation_path, objectname):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # animation
        self.anim = QLabel(self)
        self.anim.setAlignment(Qt.AlignCenter)
        self.anim.setAttribute(Qt.WA_TransparentForMouseEvents)

        movie = QMovie(animation_path)
        self.anim.setMovie(movie)
        movie.start()

        # text
        self.label = QLabel(text, self)
        self.label.setObjectName(objectname)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout.addWidget(self.anim)
        layout.addWidget(self.label)


    def _animate_to(self, target: QSize):
        for prop in (b"minimumSize", b"maximumSize"):
            a = QPropertyAnimation(self, prop)
            a.setDuration(150)
            a.setStartValue(self.size())
            a.setEndValue(target)
            a.start()
            # store reference to avoid GC
            setattr(self, f"_anim_{prop}", a)

    def enterEvent(self, event):
        self._animate_to(QSize(self.width0 + 20, self.height0 + 20))

    def leaveEvent(self, event):
        self._animate_to(QSize(self.width0, self.height0))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_to(QSize(self.width0 - 10, self.height0 - 10))
            self.setStyleSheet(
                """
                #AnimatedButton{ background-color: #9C0073;
                 border-radius: 12px;
                 border:2px solid #2E0249;
                 }
                 #AnimatedButton QLabel {
                background-color: transparent;
                border: none;}
                """
            )  # squish down

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_to(QSize(self.width0 + 20,self.height0 + 20))  # bounce back to hover size
            self.setStyleSheet("")
            self.clicked.emit()




class SimpleButton(QWidget):
    clicked = Signal()

    def __init__(self, text: str, objectname: str, w: int, h: int, parent=None):
        super().__init__(parent)

        self.setObjectName("SimpleButton")
        self.width0 = w
        self.height0 = h
        self._scale = 1.0

        # RESERVE extra space so growth never touches the layout again,
        # but the widget's LAYOUT FOOTPRINT never changes after this.
        self.setFixedSize(w + 20, h + 20)

        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self._build_ui(text, objectname)

    def _build_ui(self, text, objectname):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # inner "face" widget — THIS is what actually resizes visually
        self.face = QWidget(self)
        self.face.setObjectName(objectname + "_face")
        self.face.setFixedSize(self.width0, self.height0)

        face_layout = QVBoxLayout(self.face)
        face_layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(text, self.face)
        self.label.setObjectName(objectname)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        face_layout.addWidget(self.label)

        layout.addWidget(self.face)

    def _animate_to(self, target: QSize):
        # animate the INNER face, not self — outer widget size never changes
        self._anim = QPropertyAnimation(self.face, b"minimumSize")
        self._anim2 = QPropertyAnimation(self.face, b"maximumSize")
        for a in (self._anim, self._anim2):
            a.setDuration(150)
            a.setStartValue(self.face.size())
            a.setEndValue(target)
            a.start()

    def enterEvent(self, event):
        self._animate_to(QSize(self.width0 + 20, self.height0 + 20))

    def leaveEvent(self, event):
        self._animate_to(QSize(self.width0, self.height0))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_to(QSize(self.width0 + 20, self.height0 + 20))
            self.face.setStyleSheet(
                """
                QWidget{ background-color: #9C0073;
                 border-radius: 12px;
                 border:2px solid #2E0249;
                 }
                 QLabel {
                background-color: transparent;
                border: none;}
                """
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_to(QSize(self.width0 + 20, self.height0 + 20))
            self.face.setStyleSheet("")
            self.clicked.emit()
