from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy, QSpacerItem, QLineEdit, QGraphicsDropShadowEffect
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat, QPainterPath, QLinearGradient
from PyQt5.QtCore import Qt, QSize, QTimer, QPointF
from dotenv import dotenv_values
from pathlib import Path
import sys
import os


# Paths (kept)
PROJECT_ROOT = Path(__file__).parent.parent
TempDirPath = PROJECT_ROOT / "Frontend" / "Files"
GraphicsDirPath = PROJECT_ROOT / "Frontend" / "Graphics"
TempDirPath.mkdir(parents=True, exist_ok=True)
GraphicsDirPath.mkdir(parents=True, exist_ok=True)


# Read ONLY from .env file (no os.getenv) to avoid Windows USERNAME collision
_env = dotenv_values(PROJECT_ROOT / ".env")  # returns dict from file only
Assistantname = _env.get("Assistantname", "Ash")
Username = _env.get("Username", "Admin")


old_chat_message = ""


def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)


def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', ' ?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()


def SetMicrophoneStatus(Command):
    (TempDirPath / "Mic.data").write_text(Command, encoding="utf-8")


def GetMicrophoneStatus():
    return (TempDirPath / "Mic.data").read_text(encoding="utf-8")


def SetAssistantStatus(Status):
    (TempDirPath / "Status.data").write_text(Status, encoding="utf-8")


def GetAssistantStatus():
    return (TempDirPath / "Status.data").read_text(encoding="utf-8")


def MicButtonInitialed():
    SetMicrophoneStatus("False")


def MicButtonClosed():
    SetMicrophoneStatus("True")


def GraphicsDirectoryPath(Filename):
    return str(GraphicsDirPath / Filename)


def TempDirectoryPath(Filename):
    return str(TempDirPath / Filename)


def ShowTextToScreen(Text):
    (TempDirPath / "Responses.data").write_text(Text, encoding="utf-8")


# ---------- Subtle, non‑flicker animated label ----------
class AnimatedGradientLabel(QLabel):
    def __init__(self, text="", parent=None, font_pt=24, bold=True):
        super().__init__(text, parent)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)
        f = QFont()
        f.setPointSize(font_pt)     # smaller size per request
        f.setBold(bold)
        self.setFont(f)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(int(font_pt * 2))
        # professional palette (matched to GIF/glow)
        self._c1 = QColor("#1A73E8")
        self._c2 = QColor("#1E88E5")
        self._c3 = QColor("#DCEBFF")

    def _tick(self):
        self._offset = (self._offset + 0.0065) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        path = QPainterPath()
        fm = self.fontMetrics()
        txt = self.text()
        tw = fm.horizontalAdvance(txt)
        th = fm.ascent()
        x = (rect.width() - tw) / 2
        y = (rect.height() + th) / 2
        path.addText(QPointF(x, y), self.font(), txt)

        # Always-visible animated gradient, no flicker
        grad = QLinearGradient(QPointF(self._offset, 0.0), QPointF(1.0 + self._offset, 0.0))
        grad.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        grad.setSpread(QLinearGradient.RepeatSpread)
        grad.setColorAt(0.00, self._c1)
        grad.setColorAt(0.55, self._c2)
        grad.setColorAt(1.00, self._c3)

        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawPath(path)


# ---------- Chat page ----------
class ChatSection(QWidget):
    def __init__(self):
        super(ChatSection, self).__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(-10, 40, 40, 80)
        root.setSpacing(-100)

        self.chat_text_edit = QTextEdit()
        self.chat_text_edit.setReadOnly(True)
        self.chat_text_edit.setTextInteractionFlags(Qt.NoTextInteraction)
        self.chat_text_edit.setFrameStyle(QFrame.NoFrame)
        root.addWidget(self.chat_text_edit)
        self.setStyleSheet("background-color: black;")
        root.setSizeConstraint(QVBoxLayout.SetDefaultConstraint)
        root.setStretch(1, 1)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(Qt.blue))
        self.chat_text_edit.setCurrentCharFormat(fmt)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(10, 0, 12, 10)
        bottom_row.setSpacing(8)

        # Center container (Gemini-like pill, slightly smaller, always highlighted)
        center_wrap = QWidget()
        center_wrap.setAttribute(Qt.WA_TranslucentBackground, True)
        center_box = QHBoxLayout(center_wrap)
        center_box.setContentsMargins(0, 0, 0, 0)
        center_box.setSpacing(8)

        # Soft blue glow always visible (subtle)
        shadow = QGraphicsDropShadowEffect(center_wrap)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(26, 115, 232, 90))  # semi-transparent Google blue
        center_wrap.setGraphicsEffect(shadow)

        screen_w = QApplication.desktop().screenGeometry().width()
        # Slightly smaller than before but still centered
        center_width = max(880, min(1180, int(screen_w * 0.60)))

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Type a message…")
        self.input_edit.setFrame(False)  # ensure the Qt native frame doesn't square the corners
        self.input_edit.setStyleSheet("""
    QLineEdit {
        color: #ffffff;
        background-color: #121212;
        border: 1.5px solid rgba(26,115,232,0.40);
        padding: 12px 16px;
        border-radius: 23px;
        selection-background-color: #1A73E8;
        font-size: 15px;   /* add or adjust: try 15–16 */
    }
    QLineEdit:hover {
        border: 1.5px solid rgba(26,115,232,0.60);
    }
    QLineEdit:focus {
        border: 2px solid #1A73E8;
        background-color: #161819;
    }
""")
        self.input_edit.setFixedWidth(center_width)
        self.input_edit.setFixedHeight(46)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A73E8;
                color: white;
                padding: 0 20px;
                border: none;
                border-radius: 23px;                        /* match pill */
                font-weight: 600;
            }
            QPushButton:hover  { background-color: #1E88E5; }
            QPushButton:pressed{ background-color: #1669C1; }
        """)
        self.send_btn.setFixedHeight(46)
        self.send_btn.clicked.connect(self._send_text)
        self.input_edit.returnPressed.connect(self._send_text)

        center_box.addWidget(self.input_edit, 0)
        center_box.addWidget(self.send_btn, 0)

        right_wrap = QWidget()
        right_col = QVBoxLayout(right_wrap)
        right_col.setContentsMargins(0, 0, 4, 0)
        right_col.setSpacing(5)
        right_col.setAlignment(Qt.AlignBottom | Qt.AlignRight)

        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none;")
        movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
        movie.setScaledSize(QSize(360, 180))
        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.gif_label.setMovie(movie)
        movie.start()

        self.chat_mic_button = QLabel()
        self._setup_chat_mic_button()

        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size:14px; border: none; margin-top: -5px;")
        self.label.setAlignment(Qt.AlignHCenter)

        right_col.addWidget(self.gif_label, alignment=Qt.AlignRight)
        right_col.addWidget(self.chat_mic_button, alignment=Qt.AlignHCenter)
        right_col.addWidget(self.label, alignment=Qt.AlignHCenter)

        bottom_row.addStretch(1)
        bottom_row.addWidget(center_wrap, 0, Qt.AlignBottom | Qt.AlignHCenter)
        bottom_row.addStretch(1)
        bottom_row.addWidget(right_wrap, 0, Qt.AlignRight | Qt.AlignBottom)

        root.addLayout(bottom_row)

        font = QFont()
        font.setPointSize(13)
        self.chat_text_edit.setFont(font)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loadMessages)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(100)

        self.chat_text_edit.viewport().installEventFilter(self)

        self.setStyleSheet("""
            QScrollBar:vertical { border: none; background: black; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: white; min-height: 20px; }
            QScrollBar::add-line:vertical { background: black; height: 10px; }
            QScrollBar::sub-line:vertical { background: black; height: 10px; }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { border: none; background: none; color: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

    def _send_text(self):
        text = self.input_edit.text().strip()
        if not text:
            return
        (TempDirPath / "TypedInput.data").write_text(text, encoding="utf-8")
        (TempDirPath / "TypedTrigger.flag").write_text("1", encoding="utf-8")
        self.addMessage(message=f"Admin : {text}", color='White')
        self.input_edit.clear()

    def _setup_chat_mic_button(self):
        self.chat_mic_button.setFixedSize(55, 55)
        self.chat_mic_toggled = True
        pixmap = QPixmap(GraphicsDirectoryPath('Mic_on.png'))
        self.chat_mic_button.setPixmap(pixmap.scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.chat_mic_button.setStyleSheet("QLabel{border:none; background:transparent; border-radius:27px;} QLabel:hover{background:rgba(255,255,255,0.08);}")
        self.chat_mic_button.setAlignment(Qt.AlignCenter)
        self.chat_mic_button.mousePressEvent = self._toggle_chat_mic
        MicButtonInitialed()

    def _toggle_chat_mic(self, event=None):
        if self.chat_mic_toggled:
            self._load_chat_mic_icon(GraphicsDirectoryPath('Mic_on.png'), 45, 45)
            MicButtonInitialed()
        else:
            self._load_chat_mic_icon(GraphicsDirectoryPath('Mic_off.png'), 45, 45)
            MicButtonClosed()
        self.chat_mic_toggled = not self.chat_mic_toggled

    def _load_chat_mic_icon(self, path, width=45, height=45):
        pixmap = QPixmap(path)
        self.chat_mic_button.setPixmap(pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def loadMessages(self):
        global old_chat_message
        messages = (TempDirPath / 'Responses.data').read_text(encoding='utf-8')
        if messages and len(messages) > 1 and str(old_chat_message) != str(messages):
            self.addMessage(message=messages, color='White')
            old_chat_message = messages

    def SpeechRecogText(self):
        messages = (TempDirPath / 'Status.data').read_text(encoding='utf-8')
        self.label.setText(messages)

    def addMessage(self, message, color):
        cursor = self.chat_text_edit.textCursor()
        fmt = QTextCharFormat()
        blk = QTextBlockFormat()
        blk.setTopMargin(10)
        blk.setLeftMargin(10)
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.setBlockFormat(blk)
        cursor.insertText(message + "\n")
        self.chat_text_edit.setTextCursor(cursor)


# ---------- Home page (unchanged) ----------
class InitialScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()

        self.setStyleSheet("background-color: black;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget(self)
        header.setStyleSheet("background: black;")
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(16, 10, 16, 0)
        header_row.setSpacing(10)

        # Keep Ash AI and Hello Username headers
        self.left_title = AnimatedGradientLabel(f"{Assistantname} AI", font_pt=24, bold=True)
        self.right_greet = AnimatedGradientLabel(f"Hello {Username}", font_pt=20, bold=True)
        header_row.addWidget(self.left_title, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        header_row.addStretch(1)
        header_row.addWidget(self.right_greet, alignment=Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(header)

        layout.addStretch(2)

        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setScaledContents(False)

        self.movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
        reserved_h = 260
        gif_side = min(1050, max(400, int(screen_height * 0.58)))
        gif_side = min(gif_side, screen_height - reserved_h)
        self.movie.setScaledSize(QSize(gif_side, gif_side))
        self.gif_label.setMovie(self.movie)
        self.gif_label.setFixedSize(gif_side, gif_side)
        layout.addWidget(self.gif_label, 0, Qt.AlignCenter)

        layout.addSpacing(40)

        self.label = QLabel("", self)
        self.label.setStyleSheet("color: white; font-size: 16px;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, 0, Qt.AlignCenter)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        self.icon_label = QLabel(self)
        pixmap = QPixmap(GraphicsDirectoryPath('Mic_on.png'))
        self.icon_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setFixedSize(80, 80)
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.toggled = True
        self.toggle_icon()
        self.icon_label.mousePressEvent = self.toggle_icon

        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        layout.addSpacing(140)

        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)

        self.movie.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(100)

    def SpeechRecogText(self):
        messages = (TempDirPath / 'Status.data').read_text(encoding='utf-8')
        self.label.setText(messages)

    def load_icon(self, path, width=80, height=80):
        pixmap = QPixmap(path)
        self.icon_label.setPixmap(pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def toggle_icon(self, event=None):
        if self.toggled:
            self.load_icon(GraphicsDirectoryPath('Mic_on.png'), 80, 80)
            MicButtonInitialed()
        else:
            self.load_icon(GraphicsDirectoryPath('Mic_off.png'), 80, 80)
            MicButtonClosed()
        self.toggled = not self.toggled


class MessageScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        layout = QVBoxLayout()
        label = QLabel("")
        layout.addWidget(label)
        chat_section = ChatSection()
        layout.addWidget(chat_section)
        self.setLayout(layout)
        self.setStyleSheet("background-color: black;")
        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)


class CustomTopBar(QWidget):
    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        self.initUI()
        self.current_screen = None
        self.stacked_widget = stacked_widget

    def initUI(self):
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignRight)

        home_button = QPushButton()
        home_button.setIcon(QIcon(GraphicsDirectoryPath("Home.png")))
        home_button.setText("Home")
        home_button.setStyleSheet("height:40px; line-height:40px; background-color: white; color: black")

        message_button = QPushButton()
        message_button.setIcon(QIcon(GraphicsDirectoryPath("Chats.png")))
        message_button.setText(" Chat")
        message_button.setStyleSheet("height:40px; line-height:40px; background-color: white; color: black")

        minimize_button = QPushButton()
        minimize_button.setIcon(QIcon(GraphicsDirectoryPath("Minimize2.png")))
        minimize_button.setStyleSheet("background-color:white")
        minimize_button.clicked.connect(self.minimizeWindow)

        self.maximize_button = QPushButton()
        self.maximize_icon = QIcon(GraphicsDirectoryPath('Maximize.png'))
        self.restore_icon = QIcon(GraphicsDirectoryPath('Minimize.png'))
        self.maximize_button.setIcon(self.maximize_icon)
        self.maximize_button.setFlat(True)
        self.maximize_button.setStyleSheet("background-color:white")
        self.maximize_button.clicked.connect(self.maximizeWindow)

        close_button = QPushButton()
        close_button.setIcon(QIcon(GraphicsDirectoryPath('Close.png')))
        close_button.setStyleSheet("background-color:white")
        close_button.clicked.connect(self.closeWindow)

        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setFrameShape(QFrame.HLine)
        line_frame.setFrameShadow(QFrame.Sunken)
        line_frame.setStyleSheet("border-color: black;")

        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        layout.addStretch(1)
        layout.addWidget(home_button)
        layout.addWidget(message_button)
        layout.addStretch(1)
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)
        layout.addWidget(line_frame)

        self.draggable = True
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        super().paintEvent(event)

    def minimizeWindow(self):
        self.parent().showMinimized()

    def maximizeWindow(self):
        if self.parent().isMaximized():
            self.parent().showNormal()
            self.maximize_button.setIcon(self.maximize_icon)
        else:
            self.parent().showMaximized()
            self.maximize_button.setIcon(self.restore_icon)

    def closeWindow(self):
        self.parent().close()

    def mousePressEvent(self, event):
        if self.draggable:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.draggable and self.offset:
            new_pos = event.globalPos() - self.offset
            self.parent().move(new_pos)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        stacked_widget = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = MessageScreen()
        stacked_widget.addWidget(initial_screen)
        stacked_widget.addWidget(message_screen)
        self.setGeometry(0, 0, screen_width, screen_height)
        self.setStyleSheet("background-color: black;")
        top_bar = CustomTopBar(self, stacked_widget)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked_widget)


def GraphicalUserInterface():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    GraphicalUserInterface()
