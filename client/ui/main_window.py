"""主窗口 - 三栏布局：左历史 中编辑 右保司"""
import os

from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon

from client.resources import resource_path
from client.ui.history_panel import HistoryPanel
from client.ui.form_panel import FormPanel
from client.ui.company_panel import CompanyPanel
from client.ui.dialog import info_dialog


class MainWindow(QMainWindow):
    """客服工单录入主窗口 - 三栏布局"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("客服工单录入")
        self.resize(1100, 650)
        self._setup_icon()

        # 主布局
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧历史面板
        self.history_panel = HistoryPanel(on_item_clicked=self._on_history_item_clicked)
        layout.addWidget(self.history_panel)

        # 中间 AI 输入面板
        self.form_panel = FormPanel()
        self.form_panel.ai_result_ready.connect(self._on_ai_result)
        layout.addWidget(self.form_panel, 1)

        # 右侧保险公司选择面板
        self.company_panel = CompanyPanel()
        self.company_panel.company_selected.connect(self._on_company_selected)
        layout.addWidget(self.company_panel)

        self.setCentralWidget(central)

    def _setup_icon(self) -> None:
        icon_path = resource_path("logo.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("favicon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _on_history_item_clicked(self, policy: dict | None) -> None:
        """历史记录点击 - 显示附件"""
        if policy:
            # 显示附件
            import json
            file_paths_raw = policy.get("file_paths")
            if file_paths_raw:
                try:
                    paths = json.loads(file_paths_raw) if isinstance(file_paths_raw, str) else file_paths_raw
                    self.form_panel.show_files(paths if isinstance(paths, list) else None)
                except (json.JSONDecodeError, TypeError):
                    self.form_panel.show_files(None)
            else:
                self.form_panel.show_files(None)
        else:
            self.form_panel.clear()

    def _on_ai_result(self, result: dict) -> None:
        """AI 识别结果"""
        if result:
            info_dialog(self, "AI 识别完成", f"识别到 {len(result)} 个字段")

    def _on_company_selected(self, company: str) -> None:
        """选中保险公司"""
        # 可以在这里处理选中公司的逻辑
        print(f"选中公司: {company}")
