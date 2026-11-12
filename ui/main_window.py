
import logging
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QPropertyAnimation, QSettings, QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QProgressBar, QScrollArea, QStackedWidget, QStyle, QSystemTrayIcon,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt6.QtWidgets import QHeaderView

from sample_data import get_sample_rows
from services.generator import excel_generator, pdf_generator
from services.validator import HEADERS, calculate_totals, validate_input_rows

LOGGER = logging.getLogger(__name__)


class FolderDropLabel(QLabel):

    folder_dropped = pyqtSignal(str)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.setToolTip("Choose folder.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            Path(url.toLocalFile()).is_dir() for url in event.mimeData().urls() if url.isLocalFile()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                folder = Path(url.toLocalFile())
                if folder.is_dir():
                    self.folder_dropped.emit(str(folder))
                    event.acceptProposedAction()
                    return
        event.ignore()


class ReportWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    succeeded = pyqtSignal(str, str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, action, rows, output_folder, workbook_path=None, filename_prefix="Project_worksummary"):
        super().__init__()
        self.action = action
        self.rows = rows
        self.output_folder = output_folder
        self.workbook_path = workbook_path
        self.filename_prefix = filename_prefix

    def run(self):
        try:
            report_progress = lambda value, message: self.progress_changed.emit(value, message)
            if self.action == "excel":
                xlsx_path = excel_generator(
                    self.rows, self.output_folder, report_progress, self.filename_prefix,
                )
                self.succeeded.emit(self.action, str(xlsx_path), "")
            else:
                pdf_path = pdf_generator(self.workbook_path, self.rows, report_progress)
                self.succeeded.emit(self.action, str(self.workbook_path), str(pdf_path))
        except Exception as exc:
            LOGGER.exception("%s report  failed during export", self.action)
            self.failed.emit(self.action, str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project_worksummary")
        self.resize(1120, 760)
        self.settings = QSettings("Project", "Project_worksummary")
        default_folder = Path.home() / "Documents" / "Project_worksummary"
        self.output_folder = Path(self.settings.value("output_folder", str(default_folder)))
        self.filename_prefix = str(self.settings.value("filename_prefix", "Project_worksummary"))
        self.theme = str(self.settings.value("theme", "light"))
        self.history = self.load_history()
        self.progress_animations = {}
        self.worker = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        self.sidebar = sidebar
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(22, 26, 18, 20)
        brand = QLabel("Project")
        self.brand_label = brand
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        side_layout.addSpacing(34)
        side_layout.addWidget(self.nav_button("Home", 0))
        side_layout.addWidget(self.nav_button("Data entry", 1))
        side_layout.addStretch()
        # note = QLabel("")
        # note.setObjectName("side_note")
        # side_layout.addWidget(note)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(38, 28, 38, 30)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_home())
        self.stack.addWidget(self.build_entries())
        self.stack.addWidget(self.build_generation())
        self.stack.addWidget(self.build_pdf_conversion())
        self.stack.addWidget(self.build_success())
        content_layout.addWidget(self.stack)
        layout.addWidget(sidebar)
        layout.addWidget(content, 1)

        self.apply_theme(self.theme)
        self.refresh_summary()
        self.refresh_history()
        self.setup_notifications()

    def apply_theme(self, theme):
        self.theme = "dark" if theme == "dark" else "light"
        if self.theme == "dark":
            stylesheet = """
                QWidget { background: #18232d; color: #e5edf2; font-family: 'Segoe UI'; font-size: 14px; }
                #sidebar { background: #111b24; }
                #brand { color: #ffffff; font-size: 25px; font-weight: 700; letter-spacing: 1px; }
                #side_note, #muted { color: #a6b6c0; }
                #page_title { color: #f2f6f8; font-size: 25px; font-weight: 650; }
                #hero { background: #203a46; border: 1px solid #355563; border-radius: 16px; }
                #hero_title { color: #ffffff; font-size: 27px; font-weight: 700; }
                #hero_copy, #eyebrow { color: #b4c8cf; }
                #eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 1px; }
                #metric_value, #card_title { color: #f2f6f8; }
                #card { background: #24323d; border: 1px solid #354854; border-radius: 12px; }
                QPushButton { background: #16877f; color: white; border: 0; border-radius: 7px; padding: 11px 16px; font-weight: 600; }
                QPushButton:hover { background: #1a9a90; }
                QPushButton:disabled { background: #52646e; }
                QPushButton[nav="true"] { background: transparent; color: #c5d2d8; text-align: left; padding: 11px 12px; border-left: 3px solid transparent; }
                QPushButton[nav="true"]:hover { background: #203441; color: white; }
                QPushButton[nav="true"]:checked { background: #294252; color: white; border-left: 3px solid #55c7b6; padding-left: 9px; }
                QPushButton[secondary="true"] { background: #354a56; color: #e5edf2; }
                QTableWidget, QLineEdit, QListWidget { background: #1e2c36; color: #e5edf2; border: 1px solid #3b4e5a; border-radius: 7px; gridline-color: #354854; padding: 6px; }
                QHeaderView::section { background: #2d3c47; color: #e5edf2; border: 0; padding: 10px 6px; font-weight: 600; }
                QProgressBar { border: 0; border-radius: 5px; background: #354854; text-align: center; height: 10px; }
                QProgressBar::chunk { border-radius: 5px; background: #16877f; }
                QScrollArea { border: 0; background: transparent; }
                QScrollBar:vertical { background: transparent; width: 10px; margin: 2px 0; }
                QScrollBar::handle:vertical { background: #52646e; border-radius: 5px; min-height: 28px; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """
        else:
            stylesheet = """
                QWidget { background: #f5f7f6; color: #263746; font-family: 'Segoe UI'; font-size: 14px; }
                #sidebar { background: #18324a; }
                #brand { color: #ffffff; font-size: 25px; font-weight: 700; letter-spacing: 1px; }
                #side_note { color: #b7c7d1; }
                #page_title { color: #18324a; font-size: 25px; font-weight: 650; }
                #hero { background: #e8f2ef; border: 1px solid #d6e7e1; border-radius: 14px; }
                #hero_title { color: #18324a; font-size: 25px; font-weight: 700; }
                #hero_copy, #eyebrow { color: #627b79; }
                #eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 1px; }
                #metric_value, #card_title { color: #18324a; }
                #muted { color: #71818d; }
                #card { background: #ffffff; border: 1px solid #e5ebea; border-radius: 12px; }
                QPushButton { background: #147d78; color: white; border: 0; border-radius: 7px; padding: 11px 16px; font-weight: 600; }
                QPushButton:hover { background: #106b67; }
                QPushButton:disabled { background: #a9bbb9; }
                QPushButton[nav="true"] { background: transparent; color: #c5d2d8; text-align: left; padding: 11px 12px; border-left: 3px solid transparent; }
                QPushButton[nav="true"]:hover { background: #203a4c; color: white; }
                QPushButton[nav="true"]:checked { background: #29465b; color: white; border-left: 3px solid #55c7b6; padding-left: 9px; }
                QPushButton[secondary="true"] { background: #e7f0ef; color: #176d69; }
                QTableWidget, QLineEdit, QListWidget { background: white; color: #263746; border: 1px solid #e5ebea; border-radius: 7px; padding: 6px; gridline-color: #edf1f0; }
                QHeaderView::section { background: #eef3f2; color: #526573; border: 0; padding: 10px 6px; font-weight: 600; }
                QProgressBar { border: 0; border-radius: 5px; background: #e5eceb; text-align: center; height: 10px; }
                QProgressBar::chunk { border-radius: 5px; background: #147d78; }
                QScrollArea { border: 0; background: transparent; }
                QScrollBar:vertical { background: transparent; width: 10px; margin: 2px 0; }
                QScrollBar::handle:vertical { background: #c3d0cc; border-radius: 5px; min-height: 28px; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """
        self.setStyleSheet(stylesheet)
        sidebar_color = "#18324a" if self.theme == "light" else "#111b24"
        self.sidebar.setStyleSheet(f"background-color: {sidebar_color};")
        self.brand_label.setStyleSheet(
            "color: #ffffff; background: transparent; font-size: 25px; "
            "font-weight: 700; letter-spacing: 1px;"
        )
        self.settings.setValue("theme", self.theme)
        if hasattr(self, "theme_button"):
            self.theme_button.setText("Use dark theme" if self.theme == "light" else "Use light theme")

    def toggle_theme(self):
        self.apply_theme("dark" if self.theme == "light" else "light")

    def setup_notifications(self):
        self.tray_icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.tray_icon.setToolTip("Project_worksummary")
        self.tray_icon.show()

    def notify_user(self, title, message):
        if self.tray_icon:
            self.tray_icon.showMessage(
                title, message, QSystemTrayIcon.MessageIcon.Information, 5000,
            )

    def load_history(self):
        try:
            history = json.loads(self.settings.value("recent_history", "[]"))
        except (TypeError, ValueError):
            return []
        return history if isinstance(history, list) else []

    def save_history(self, xlsx_path, pdf_path):
        record = {
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "excel": str(xlsx_path),
            "pdf": str(pdf_path),
        }
        self.history = [record] + [
            old for old in self.history
            if old.get("excel") != record["excel"]
        ]
        self.history = self.history[:10]
        self.settings.setValue("recent_history", json.dumps(self.history))
        self.settings.sync()
        self.refresh_history()

    def refresh_history(self):
        if not hasattr(self, "history_list"):
            return
        self.history_list.clear()
        for record in self.history:
            item = QListWidgetItem(f"{record.get('created', 'Recent')}   {Path(record.get('excel', '')).name}")
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.history_list.addItem(item)
        self.history_list.setVisible(bool(self.history))
        if hasattr(self, "history_empty"):
            self.history_empty.setVisible(not self.history)
            self.history_actions_widget.setVisible(bool(self.history))
            self.history_hint.setVisible(bool(self.history))

    def open_history_file(self, file_type):
        item = self.history_list.currentItem()
        if not item:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        file_path = Path(record.get(file_type, ""))
        if not file_path.is_file():
            QMessageBox.warning(self, "File not found", f"This history file is no longer available:\n{file_path}")
            return
        self.open_file(str(file_path))

    def animate_progress(self, progress_bar, value):
        animation = self.progress_animations.get(progress_bar)
        if animation:
            animation.stop()
        animation = QPropertyAnimation(progress_bar, b"value", self)
        animation.setDuration(450)
        animation.setStartValue(progress_bar.value())
        animation.setEndValue(value)
        self.progress_animations[progress_bar] = animation
        animation.start()

    def nav_button(self, label, page):
        button = QPushButton(label)
        button.setProperty("nav", "true")
        button.setCheckable(True)
        button.clicked.connect(lambda: self.show_page(page))
        if not hasattr(self, "nav_buttons"):
            self.nav_buttons = []
        self.nav_buttons.append(button)
        if page == 0:
            button.setChecked(True)
        return button

    def show_page(self, page):
        self.stack.setCurrentIndex(page)
        active_nav = 0 if page == 0 else 1
        for index, button in enumerate(self.nav_buttons):
            button.setChecked(index == active_nav)

    def build_home(self):
        page = QScrollArea()
        page.setObjectName("home_scroll")
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("Workspace overview")
        title.setObjectName("page_title")
        subtitle = QLabel("Your work, totals, and reports in one place.")
        subtitle.setObjectName("muted")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()
        self.theme_button = QPushButton()
        self.theme_button.setProperty("secondary", "true")
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        layout.addLayout(header)
        layout.addSpacing(14)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 17, 22, 17)
        intro = QVBoxLayout()
        eyebrow = QLabel("PROJECT WORKSUMMARY")
        eyebrow.setObjectName("eyebrow")
        hero_title = QLabel("Work summary, made simple")
        hero_title.setObjectName("hero_title")
        hero_copy = QLabel("Add entries, check totals, and create Excel and PDF reports.")
        hero_copy.setObjectName("hero_copy")
        hero_copy.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addSpacing(3)
        intro.addWidget(hero_title)
        intro.addSpacing(4)
        intro.addWidget(hero_copy)
        hero_layout.addLayout(intro, 1)
        hero_action = QPushButton("Create a report")
        hero_action.setMinimumHeight(44)
        hero_action.clicked.connect(lambda: self.show_page(1))
        hero_layout.addWidget(hero_action, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(hero)
        layout.addSpacing(14)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.hours_card = self.metric_card("TOTAL HOURS", "0")
        self.amount_card = self.metric_card("REPORT VALUE", "\u20b90.00")
        self.rows_card = self.metric_card("ENTRIES", "0")
        for card in (self.hours_card, self.amount_card, self.rows_card):
            cards.addWidget(card)
        layout.addLayout(cards)
        layout.addSpacing(14)

        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 16, 20, 18)
        panel_layout.setSpacing(10)
        heading = QLabel("Report setup")
        heading.setObjectName("card_title")
        heading.setStyleSheet("font-size: 17px; font-weight: 650;")
        panel_layout.addWidget(heading)
        description = QLabel("Choose where reports are saved and set a filename prefix.")
        description.setObjectName("muted")
        panel_layout.addWidget(description)
        folder_row = QHBoxLayout()
        self.folder_label = FolderDropLabel(str(self.output_folder))
        self.folder_label.setObjectName("muted")
        self.folder_label.setMinimumWidth(0)
        self.folder_label.setWordWrap(True)
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.folder_label.setToolTip(str(self.output_folder))
        self.folder_label.folder_dropped.connect(self.set_output_folder)
        folder_caption = QLabel("SAVE TO")
        folder_caption.setObjectName("eyebrow")
        folder_row.addWidget(folder_caption)
        folder_row.addWidget(self.folder_label, 1)
        choose = QPushButton("Choose folder")
        choose.setProperty("secondary", "true")
        choose.clicked.connect(self.choose_folder)
        folder_row.addWidget(choose)
        panel_layout.addLayout(folder_row)
        prefix_row = QHBoxLayout()
        prefix_caption = QLabel("FILE NAME")
        prefix_caption.setObjectName("eyebrow")
        prefix_row.addWidget(prefix_caption)
        self.filename_prefix_input = QLineEdit(self.filename_prefix)
        self.filename_prefix_input.setPlaceholderText("e.g. Project_worksummary")
        self.filename_prefix_input.setMinimumHeight(38)
        self.filename_prefix_input.editingFinished.connect(self.save_filename_preference)
        prefix_row.addWidget(self.filename_prefix_input, 1)
        panel_layout.addLayout(prefix_row)
        hint = QLabel("Tip: drag a folder from Explorer onto the save path.")
        hint.setObjectName("muted")
        panel_layout.addWidget(hint)
        layout.addWidget(panel)
        layout.addSpacing(14)

        history_card = QFrame()
        history_card.setObjectName("card")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(20, 14, 20, 16)
        history_layout.setSpacing(8)
        history_header = QHBoxLayout()
        history_title = QLabel("Recent exports")
        history_title.setObjectName("card_title")
        history_title.setStyleSheet("font-size: 17px; font-weight: 650;")
        history_header.addWidget(history_title)
        history_header.addStretch()
        history_hint = QLabel("Double click an export to open it")
        self.history_hint = history_hint
        history_hint.setObjectName("muted")
        history_header.addWidget(history_hint)
        history_layout.addLayout(history_header)
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(48)
        self.history_list.setMaximumHeight(88)
        self.history_list.itemDoubleClicked.connect(lambda _item: self.open_history_file("excel"))
        history_layout.addWidget(self.history_list)
        self.history_empty = QLabel("Your completed reports will appear here.")
        self.history_empty.setObjectName("muted")
        self.history_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_empty.setMinimumHeight(42)
        history_layout.addWidget(self.history_empty)
        history_actions_widget = QWidget()
        self.history_actions_widget = history_actions_widget
        history_actions = QHBoxLayout(history_actions_widget)
        history_actions.setContentsMargins(0, 0, 0, 0)
        history_excel = QPushButton("Open selected Excel")
        history_excel.setProperty("secondary", "true")
        history_excel.clicked.connect(lambda: self.open_history_file("excel"))
        history_pdf = QPushButton("Open selected PDF")
        history_pdf.setProperty("secondary", "true")
        history_pdf.clicked.connect(lambda: self.open_history_file("pdf"))
        history_actions.addWidget(history_excel)
        history_actions.addWidget(history_pdf)
        history_actions.addStretch()
        history_layout.addWidget(history_actions_widget)
        layout.addWidget(history_card)
        layout.addStretch()
        page.setWidget(body)
        return page

    def metric_card(self, label, value):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 12, 18, 12)
        heading = QLabel(label)
        heading.setObjectName("muted")
        number = QLabel(value)
        number.setObjectName("metric_value")
        number.setStyleSheet("font-size: 23px; font-weight: 700;")
        card_layout.addWidget(heading)
        card_layout.addWidget(number)
        card.value_label = number
        return card

    def build_generation(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Generate Excel")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Create the formatted workbook from your entries."))

        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        self.excel_progress = QProgressBar()
        self.excel_progress.setRange(0, 100)
        self.excel_progress.setValue(0)
        self.excel_progress.setTextVisible(False)
        panel_layout.addWidget(self.excel_progress)
        self.excel_status_label = QLabel("Waiting to generate Excel.")
        self.excel_status_label.setObjectName("muted")
        panel_layout.addWidget(self.excel_status_label)
        layout.addWidget(panel)
        back = QPushButton("Back to data entry")
        back.setProperty("secondary", "true")
        back.clicked.connect(lambda: self.show_page(1))
        layout.addWidget(back)
        layout.addStretch()
        return page

    def build_pdf_conversion(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Convert to PDF")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Convert the generated Excel workbook into  PDF report."))

        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        panel_layout.addWidget(QLabel("Excel workbook"))
        self.xlsx_path_label = QLabel("")
        self.xlsx_path_label.setWordWrap(True)
        self.xlsx_path_label.setObjectName("muted")
        panel_layout.addWidget(self.xlsx_path_label)
        self.pdf_progress = QProgressBar()
        self.pdf_progress.setRange(0, 100)
        self.pdf_progress.setValue(0)
        self.pdf_progress.setTextVisible(False)
        panel_layout.addWidget(self.pdf_progress)
        self.pdf_status_label = QLabel("Ready to convert the workbook.")
        self.pdf_status_label.setObjectName("muted")
        panel_layout.addWidget(self.pdf_status_label)
        self.convert_pdf_button = QPushButton("Convert Excel to PDF")
        self.convert_pdf_button.clicked.connect(self.start_pdf_conversion)
        panel_layout.addWidget(self.convert_pdf_button)
        layout.addWidget(panel)
        back = QPushButton("Back to data entry")
        back.setProperty("secondary", "true")
        back.clicked.connect(lambda: self.show_page(1))
        layout.addWidget(back)
        layout.addStretch()
        return page

    def build_success(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Reports ready")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Excel and PDF files were generated successfully."))

        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        panel_layout.addWidget(QLabel("Open  your generated files:"))
        self.files_label = QLabel("")
        self.files_label.setWordWrap(True)
        panel_layout.addWidget(self.files_label)
        actions = QHBoxLayout()
        self.open_excel_button = QPushButton("Open Excel")
        self.open_excel_button.clicked.connect(lambda: self.open_file(self.xlsx_path))
        self.open_pdf_button = QPushButton("Open PDF")
        self.open_pdf_button.clicked.connect(lambda: self.open_file(self.pdf_path))
        self.open_folder_button = QPushButton("Open output folder")
        self.open_folder_button.setProperty("secondary", "true")
        self.open_folder_button.clicked.connect(self.open_output_folder)
        actions.addWidget(self.open_excel_button)
        actions.addWidget(self.open_pdf_button)
        actions.addWidget(self.open_folder_button)
        actions.addStretch()
        panel_layout.addLayout(actions)
        layout.addWidget(panel)
        layout.addStretch()
        return page

    def build_entries(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Work entries")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Click  to edit it. Use (YYYY-MM-DD), hours, and hourly rates."))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search client, category, description, date...")
        self.search_input.textChanged.connect(self.filter_rows)
        layout.addWidget(self.search_input)
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        add = QPushButton("Add row")
        add.setProperty("secondary", "true")
        add.clicked.connect(self.add_row)
        remove = QPushButton("Remove selected")
        remove.setProperty("secondary", "true")
        remove.clicked.connect(self.remove_rows)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        back = QPushButton("Home dashboard")
        back.setProperty("secondary", "true")
        back.clicked.connect(lambda: self.show_page(0))
        self.generate_excel_button = QPushButton("Generate Excel")
        self.generate_excel_button.clicked.connect(self.start_generation)
        buttons.addWidget(back)
        buttons.addWidget(self.generate_excel_button)
        layout.addLayout(buttons)
        self.load_rows(get_sample_rows())
        return page

    def load_rows(self, rows):
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.itemChanged.connect(self.refresh_summary)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate(("2026-11-01", "New client", "Service", "Work description", "1", "0.00")):
            self.table.setItem(row, column, QTableWidgetItem(value))
        self.refresh_summary()

    def remove_rows(self):
        selected = sorted({index.row() for index in self.table.selectionModel().selectedRows()}, reverse=True)
        for row in selected:
            self.table.removeRow(row)
        self.refresh_summary()

    def current_rows(self):
        rows = []
        for row in range(self.table.rowCount()):
            rows.append([
                self.table.item(row, column).text().strip() if self.table.item(row, column) else ""
                for column in range(len(HEADERS))
            ])
        return rows

    def filter_rows(self, search_text):
        query = search_text.strip().casefold()
        for row in range(self.table.rowCount()):
            values = [
                self.table.item(row, column).text().casefold()
                for column in range(self.table.columnCount())
                if self.table.item(row, column)
            ]
            self.table.setRowHidden(row, bool(query) and not any(query in value for value in values))

    def refresh_summary(self, *_):
        rows = self.current_rows()
        if validate_input_rows(rows):
            self.hours_card.value_label.setText("—")
            self.amount_card.value_label.setText("—")
        else:
            hours, amount, _ = calculate_totals(rows)
            self.hours_card.value_label.setText(f"{hours:,.2f}")
            self.amount_card.value_label.setText(f"\u20b9{amount:,.2f}")
        self.rows_card.value_label.setText(str(len(rows)))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.output_folder))
        if folder:
            self.set_output_folder(folder)

    def set_output_folder(self, folder):
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            QMessageBox.warning(self, "Invalid output folder", "Choose an existing folder.")
            return
        self.output_folder = path
        self.folder_label.setText(str(path))
        self.folder_label.setToolTip(str(path))
        self.settings.setValue("output_folder", str(path))
        self.settings.sync()

    def save_filename_preference(self):
        self.filename_prefix = self.filename_prefix_input.text().strip() or "Project_worksummary"
        self.filename_prefix_input.setText(self.filename_prefix)
        self.settings.setValue("filename_prefix", self.filename_prefix)
        self.settings.sync()

    def start_generation(self):
        rows = self.current_rows()
        problems = validate_input_rows(rows)
        if problems:
            QMessageBox.warning(self, "Check the entries", "\n".join(problems))
            self.show_page(1)
            return

        self.report_rows = rows
        self.save_filename_preference()
        self.excel_progress.setValue(0)
        self.excel_status_label.setText("Starting Excel generation...")
        self.generate_excel_button.setEnabled(False)
        self.show_page(2)
        self.worker = ReportWorker(
            "excel", rows, self.output_folder,
            filename_prefix=self.filename_prefix,
        )
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_export_complete)
        self.worker.failed.connect(self.on_export_failure)
        self.worker.start()

    def start_pdf_conversion(self):
        if not self.xlsx_path or not Path(self.xlsx_path).exists():
            QMessageBox.warning(self, "Excel file missing", "Generate the Excel report before converting it to PDF.")
            self.show_page(1)
            return

        self.pdf_progress.setValue(0)
        self.pdf_status_label.setText("Starting PDF conversion...")
        self.convert_pdf_button.setEnabled(False)
        self.show_page(3)
        self.worker = ReportWorker(
            "pdf", self.report_rows, self.output_folder, workbook_path=self.xlsx_path,
        )
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_export_complete)
        self.worker.failed.connect(self.on_export_failure)
        self.worker.start()

    def on_progress(self, value, message):
        if self.worker and self.worker.action == "excel":
            self.animate_progress(self.excel_progress, value)
            self.excel_status_label.setText(message)
        else:
            self.animate_progress(self.pdf_progress, value)
            self.pdf_status_label.setText(message)

    def on_export_complete(self, action, xlsx_path, pdf_path):
        if action == "excel":
            self.xlsx_path = xlsx_path
            self.xlsx_path_label.setText(xlsx_path)
            self.excel_status_label.setText("Excel report generated successfully.")
            self.generate_excel_button.setEnabled(True)
            self.pdf_progress.setValue(0)
            self.pdf_status_label.setText("Ready to convert the workbook.")
            LOGGER.info("Created Excel report: %s", xlsx_path)
            self.show_page(3)
            return

        self.xlsx_path = xlsx_path
        self.pdf_path = pdf_path
        self.pdf_progress.setValue(100)
        self.pdf_status_label.setText("PDF report generated successfully.")
        self.convert_pdf_button.setEnabled(True)
        self.files_label.setText(f"Excel: {xlsx_path}\nPDF: {pdf_path}")
        self.save_history(xlsx_path, pdf_path)
        self.notify_user("Project_worksummary ready", "Your Excel and PDF reports have been generated.")
        LOGGER.info("Created report files: %s and %s", xlsx_path, pdf_path)
        self.show_page(4)

    def on_export_failure(self, action, message):
        LOGGER.error("%s report export failed: %s", action, message)
        if action == "excel":
            self.generate_excel_button.setEnabled(True)
            self.excel_status_label.setText("Excel generation failed.")
        else:
            self.convert_pdf_button.setEnabled(True)
            self.pdf_status_label.setText("PDF conversion failed.")
        self.notify_user("Project_worksummary export failed", message)
        QMessageBox.critical(self, "Report generation failed", message)

    def open_output_folder(self):
        folder = Path(self.xlsx_path).parent if getattr(self, "xlsx_path", None) else self.output_folder
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @staticmethod
    def open_file(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

