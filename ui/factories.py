from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QLabel, QWidget


class UiFactory:
    @staticmethod
    def make_button(label: str , objname: str):
        button = QPushButton(label)
        button.setObjectName(objname)
        return button

    @staticmethod
    def make_label(label: str , objname: str):
        label = QLabel(label)
        label.setObjectName(objname)
        return label
