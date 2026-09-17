"""主窗口 - 两栏布局：左保单列表 右聊天面板"""
import os

from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QDialog, QMessageBox, QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from client.resources import resource_path
from client.ui.history_panel import HistoryPanel
from client.ui.chat_panel import ChatPanel
from client.api import change_password
from client.ui.change_password_dialog import ChangePasswordDialog


class MainWindow(QMainWindow):
    """客服工单录入主窗口 - 聊天风格两栏布局"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("客服工单录入")
        self.resize(1000, 620)
        self._current_user: dict | None = None
        self._setup_icon()

        # 主布局：顶部用户栏 + 内容区
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部用户栏
        self._setup_top_bar(main_layout)

        # 内容区：左保单列表 + 右聊天面板
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self.history_panel = HistoryPanel(on_item_clicked=self._on_history_item_clicked)
        content.addWidget(self.history_panel)

        self.chat_panel = ChatPanel()
        self.chat_panel.task_created.connect(self._on_task_created)
        content.addWidget(self.chat_panel, 1)

        main_layout.addLayout(content, 1)
        self.setCentralWidget(central)

    def _setup_top_bar(self, parent_layout: QHBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addStretch()
        user_label = QLabel("当前用户：")
        user_label.setStyleSheet("font-size: 13px; color: #6b7280; padding: 6px 0;")
        bar.addWidget(user_label)
        self._user_btn = QPushButton("未登录")
        self._user_btn.setCursor(Qt.PointingHandCursor)
        self._user_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #1677ff;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 14px;
                background: transparent;
            }
            QPushButton:hover {
                background: #e8f4ff;
                border-radius: 4px;
            }
        """)
        self._user_btn.clicked.connect(self._on_change_password)
        bar.addWidget(self._user_btn)
        parent_layout.addLayout(bar)

    def set_current_user(self, user: dict):
        """设置当前登录用户"""
        self._current_user = user
        self.chat_panel.set_current_user(user)
        display_name = user.get("display_name", user.get("username", ""))
        self.setWindowTitle(f"客服工单录入 — {display_name}")
        self._user_btn.setText(display_name)

    def _on_change_password(self) -> None:
        if not self._current_user:
            return
        dlg = ChangePasswordDialog(self)
        if dlg.exec() == QDialog.Accepted:
            try:
                change_password(self._current_user["id"], dlg.old_pwd(), dlg.new_pwd())
                QMessageBox.information(self, "成功", "密码已修改")
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))

    def _setup_icon(self) -> None:
        icon_path = resource_path("logo.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("favicon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _on_history_item_clicked(self, task: dict | None) -> None:
        """历史记录点击 - 切换到对应任务"""
        self.chat_panel.set_current_task(task)

    def _on_task_created(self, task_id: str) -> None:
        """新任务创建 - 刷新左侧列表"""
        self.history_panel.refresh()
