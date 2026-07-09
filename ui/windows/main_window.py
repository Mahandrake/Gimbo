from PySide6.QtWidgets import QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Qt, QPropertyAnimation

from db import create_session , create_review
from ui.factories import UiFactory
from ui.widgets.animated_buttons import AnimatedButton
from ui.windows.game_hub_window import GameHubWindow
from ui.windows.journal_window import JournalWindow
from ui.windows.writing_window import WritingPage
from ui.windows.finished_window import FinishedPage
from ui.windows.index_window import IndexWindow        # <-- new
from ui.windows.diary_window import DiaryWindow
from config.settings import BASE_DIR


class TitleBar(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("titlebar")
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        self.titlelabel = UiFactory.make_label("Gimbo", "titlelabel")
        self.closebtn = UiFactory.make_button("X", "closebtn")
        self.closebtn.setFixedSize(30,30)

        layout.addWidget(self.titlelabel)
        layout.addStretch()
        layout.addWidget(self.closebtn)

    def _connect_signals(self):
        self.closebtn.clicked.connect(self.window().close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gimbo")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self._build_ui()

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        central.setObjectName("mainwindow")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.titlebar = TitleBar(self)
        root_layout.addWidget(self.titlebar)

        # stacked widget holds all "pages"
        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack)

        # build home page (your menu)
        self.home_page = QWidget()
        home_layout = QVBoxLayout(self.home_page)
        home_layout.addStretch()
        home_layout.addLayout(self._build_menu())
        home_layout.addStretch()

        # build game hub page
        self.game_hub_page = GameHubWindow()
        self.game_hub_page.back_requested.connect(self.go_to_home)

        # build journal page
        self.journal_page = JournalWindow()
        self.game_hub_page.journal_requested.connect(self.go_to_journal_page)
        self.journal_page.back_requested.connect(self.go_to_game_hub)
        self.journal_page.view_requested.connect(self.go_to_diary_page)

        # build writing page
        self.writing_page = WritingPage()
        self.journal_page.start_requested.connect(self.go_to_writing_page)
        self.writing_page.back_requested.connect(self.go_to_journal_page)
        self.writing_page.session_saved.connect(self.handle_session_saved)

        # build finished page
        self.finished_page = FinishedPage()
        self.journal_page.finished_requested.connect(self.go_to_finished_page)
        self.finished_page.back_requested.connect(self.go_to_journal_page)
        self.finished_page.review_saved.connect(self.handle_review_saved)

        # build index page
        self.index_page = IndexWindow()
        self.game_hub_page.index_requested.connect(self.go_to_index_page)
        self.index_page.back_requested.connect(self.go_to_game_hub)
        self.index_page.game_selected.connect(self.go_to_diary_page)

        # build diary page
        self.diary_page = DiaryWindow()
        self.diary_page.back_requested.connect(self.go_to_index_page)

        # register pages
        self.stack.addWidget(self.home_page)  # index 0
        self.stack.addWidget(self.game_hub_page)  # index 1
        self.stack.addWidget(self.journal_page)  # index 2
        self.stack.addWidget(self.writing_page)  # index 3
        self.stack.addWidget(self.finished_page)  # index 4
        self.stack.addWidget(self.index_page)  # index 5
        self.stack.addWidget(self.diary_page)  # index 6

        self.stack.setCurrentWidget(self.home_page)

    def _build_menu(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)

        games = AnimatedButton("Games", str(BASE_DIR / "assets" / "gifs" / "mario.gif"), "animatedbutton",225,240)
        movies = AnimatedButton("Movies", str(BASE_DIR / "assets" / "gifs" / "film.png"), "animatedbutton",225,240)
        books = AnimatedButton("Books", str(BASE_DIR / "assets" / "gifs" / "book.gif"), "animatedbutton",225,240)

        games.clicked.connect(self.go_to_game_hub)   # ← switch page here
        movies.clicked.connect(lambda: print("movies"))
        books.clicked.connect(lambda: print("books"))

        layout.addWidget(games)
        layout.addWidget(movies)
        layout.addWidget(books)
        return layout

    def go_to_game_hub(self):
        self.stack.setCurrentWidget(self.game_hub_page)
        self.game_hub_page.show_with_fade()

    def go_to_home(self):
        self.stack.setCurrentWidget(self.home_page)
        self.show_with_fade()

    def go_to_journal_page(self):
        self.stack.setCurrentWidget(self.journal_page)
        self.journal_page.show_with_fade()

    def go_to_writing_page(self, game: dict):
        self.writing_page.set_game(game)
        self.stack.setCurrentWidget(self.writing_page)
        self.writing_page.show_with_fade()

    def go_to_finished_page(self, game: dict):
        self.finished_page.set_game(game)
        self.stack.setCurrentWidget(self.finished_page)
        self.finished_page.show_with_fade()

    def go_to_index_page(self):
        self.stack.setCurrentWidget(self.index_page)
        self.index_page.show_with_fade()

    def go_to_diary_page(self, game: dict):
        self.diary_page.set_game(game)
        self.stack.setCurrentWidget(self.diary_page)
        self.diary_page.show_with_fade()

    def handle_review_saved(self, review_entry: dict):
        create_review(
            review_entry.get("game_id"),
            {"rating": review_entry.get("rating"), "body": review_entry.get("text")},
        )
        self.go_to_journal_page()

    def handle_session_saved(self, session_entry: dict):
        create_session(session_entry)
        self.go_to_journal_page()

    def show_with_fade(self, duration_ms: int = 800) -> None:
        """Display the window maximised with a smooth fade-in."""
        self.setWindowOpacity(0)

        # Keep a reference on self so the GC cannot destroy it mid-flight
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
