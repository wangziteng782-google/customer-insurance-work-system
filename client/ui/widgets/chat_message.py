"""聊天消息气泡组件 - 用户/系统/AI 三种类型"""
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt


class ChatMessage(QWidget):
    """单条聊天消息气泡"""

    def __init__(
        self,
        content: str,
        msg_type: str = "user",  # user | bot | system
        timestamp: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
        self._msg_type = msg_type
        self._timestamp = timestamp
        self._init_ui()

    def _init_ui(self) -> None:
        # 外层布局：控制对齐
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 气泡本体
        self.bubble = QLabel(self._content)
        self.bubble.setWordWrap(True)
        self.bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.bubble.setMaximumWidth(520)
        self.bubble.setContentsMargins(12, 10, 12, 10)

        # 时间标签
        self.time_label = QLabel(self._timestamp)
        self.time_label.setStyleSheet("font-size: 11px; color: #909399; background: transparent;")

        if self._msg_type == "user":
            # 用户消息：蓝色气泡，右对齐
            self.bubble.setStyleSheet("""
                QLabel {
                    background-color: #1677ff;
                    color: #ffffff;
                    border-radius: 12px 2px 12px 12px;
                    font-size: 14px;
                    line-height: 1.55;
                }
            """)
            outer.addStretch()
            outer.addWidget(self.bubble)
        elif self._msg_type == "bot":
            # AI/机器人消息：灰色气泡，左对齐
            self.bubble.setStyleSheet("""
                QLabel {
                    background-color: #f2f3f5;
                    color: #1d2129;
                    border-radius: 2px 12px 12px 12px;
                    font-size: 14px;
                    line-height: 1.55;
                }
            """)
            outer.addWidget(self.bubble)
            outer.addStretch()
        else:
            # 系统消息：居中灰色
            self.bubble.setStyleSheet("""
                QLabel {
                    background-color: #f2f3f5;
                    color: #1d2129;
                    border-radius: 2px 12px 12px 12px;
                    font-size: 14px;
                    line-height: 1.55;
                }
            """)
            outer.addWidget(self.bubble)
            outer.addStretch()
