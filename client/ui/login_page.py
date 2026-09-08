"""登录页面"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from client.api import login


class LoginPage(QWidget):
    """登录页面 — 登录成功后发射信号"""
    login_success = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("background-color: #f5f7fa;")

        # ── 背景装饰 ──
        self._add_decor_circle(-50, -80, "#e8f4ff", 220)   # 左上 浅蓝大圆
        self._add_decor_circle(820, 380, "#e8f4ff", 180)   # 右下 浅蓝
        self._add_decor_circle(-30, 420, "#f0f0f0", 100)   # 左下 浅灰
        self._add_decor_rounded(700, -40, "#f0f7ff", 120, 20)   # 右上 圆角方块
        self._add_decor_rounded(60, 200, "#e8f4ff", 60, 12)     # 左中 小方块
        self._add_decor_circle(900, 100, "#f5f5f5", 50)    # 右中 小灰圆

        # 居中布局
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        # 登录卡片
        card = QWidget()
        card.setFixedSize(360, 380)
        card.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e5e7eb;
            }
        """)

        # 卡片顶部蓝色装饰条
        top_bar = QWidget(card)
        top_bar.setFixedHeight(3)
        top_bar.setGeometry(0, 0, 360, 3)
        top_bar.setStyleSheet("""
            background-color: #1677ff;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)
        outer.addStretch()

        # 卡片内容
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(12)
        layout.addSpacing(6)  # 给顶部装饰条留空间

        # 标题
        title = QLabel("保险工单系统")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1a1a2e;")
        layout.addWidget(title)

        subtitle = QLabel("请登录以继续")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #999; margin-bottom: 6px;")
        layout.addWidget(subtitle)

        # 表单
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        # 标签样式
        label_style = "font-size: 13px; color: #3a3a4a; font-weight: 500;"

        phone_label = QLabel("手机号")
        phone_label.setStyleSheet(label_style)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("请输入手机号")
        self.phone_edit.setFixedHeight(40)
        self.phone_edit.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #d9d9d9;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                color: #1a1a2e;
                background: #fafafa;
            }
            QLineEdit:focus {
                border-color: #1677ff;
                background: #ffffff;
            }
        """)
        form.addRow(phone_label, self.phone_edit)

        pwd_label = QLabel("密码")
        pwd_label.setStyleSheet(label_style)
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setFixedHeight(40)
        self.pwd_edit.setPlaceholderText("请输入密码")
        self.pwd_edit.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #d9d9d9;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                color: #1a1a2e;
                background: #fafafa;
            }
            QLineEdit:focus {
                border-color: #1677ff;
                background: #ffffff;
            }
        """)
        form.addRow(pwd_label, self.pwd_edit)
        layout.addLayout(form)

        # 错误提示
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("font-size: 12px; color: #ff4d4f;")
        layout.addWidget(self.error_label)

        # 登录按钮
        self.login_btn = QPushButton("登 录")
        self.login_btn.setFixedHeight(42)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1677ff;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4096ff; }
            QPushButton:pressed { background-color: #0958d9; }
        """)
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

    def _add_decor_circle(self, x: int, y: int, color: str, size: int) -> None:
        """添加装饰圆"""
        circle = QWidget(self)
        circle.setFixedSize(size, size)
        circle.move(x, y)
        circle.setStyleSheet(f"""
            background-color: {color};
            border-radius: {size // 2}px;
        """)
        circle.setAttribute(Qt.WA_TransparentForMouseEvents)
        circle.lower()

    def _add_decor_rounded(self, x: int, y: int, color: str, size: int, radius: int) -> None:
        """添加圆角方块装饰"""
        box = QWidget(self)
        box.setFixedSize(size, size)
        box.move(x, y)
        box.setStyleSheet(f"""
            background-color: {color};
            border-radius: {radius}px;
        """)
        box.setAttribute(Qt.WA_TransparentForMouseEvents)
        box.lower()

    def _on_login(self):
        """登录"""
        phone = self.phone_edit.text().strip()
        password = self.pwd_edit.text()
        if not phone or not password:
            self.error_label.setText("请输入手机号和密码")
            return
        try:
            user = login(phone, password)
            self.error_label.setText("")
            self.login_success.emit(user)
        except Exception as e:
            msg = str(e)
            if "401" in msg:
                self.error_label.setText("手机号或密码错误")
            else:
                self.error_label.setText(f"登录失败: {msg}")
