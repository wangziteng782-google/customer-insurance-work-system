"""主窗口 - 两栏布局：左保单列表 右聊天面板"""
import os

from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon

from client.resources import resource_path
from client.ui.history_panel import HistoryPanel
from client.ui.chat_panel import ChatPanel


class MainWindow(QMainWindow):
    """客服工单录入主窗口 - 聊天风格两栏布局"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("客服工单录入")
        self.resize(1000, 620)
        self._setup_icon()

        # 主布局
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧保单列表
        self.history_panel = HistoryPanel(on_item_clicked=self._on_history_item_clicked)
        layout.addWidget(self.history_panel)

        # 右侧聊天面板
        self.chat_panel = ChatPanel()
        self.chat_panel.task_created.connect(self._on_task_created)
        layout.addWidget(self.chat_panel, 1)

        self.setCentralWidget(central)

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
