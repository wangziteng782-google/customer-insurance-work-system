"""中间 AI 识别输入面板"""
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from client.ui.widgets.ai_input_widget import AiInputWidget
from client.ui.widgets.file_display_widget import FileDisplayWidget


class FormPanel(QWidget):
    """AI 识别输入面板 - 粘贴 + 拖拽 + AI识别"""

    ai_result_ready = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: #f0f2f5;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # AI 识别输入区域
        self.ai_input = AiInputWidget()
        self.ai_input.ai_result_ready.connect(self.ai_result_ready)
        layout.addWidget(self.ai_input, 1)

        # 文件展示区（点击历史记录时显示附件）
        self.file_display = FileDisplayWidget()
        layout.addWidget(self.file_display)

    def clear(self) -> None:
        """清空输入"""
        self.ai_input.clear()
        self.file_display.clear_files()

    def show_files(self, file_paths: list[str] | None) -> None:
        """显示附件"""
        if file_paths:
            self.file_display.set_files(file_paths)
        else:
            self.file_display.clear_files()
