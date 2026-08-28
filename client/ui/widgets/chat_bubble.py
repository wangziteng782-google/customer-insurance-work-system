"""聊天风格的气泡组件 - 现代化设计"""
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from qfluentwidgets import CardWidget, FluentIcon, IconWidget


class ChatBubble(CardWidget):
    """单条历史记录气泡 - 聊天风格"""

    # 状态颜色映射
    STATUS_COLORS = {
        "待完成": "#a0aec0",
        "已完成": "#38a169",
        "有异常": "#e53e3e",
    }

    def __init__(
        self,
        company_name: str,
        insurance_type: str,
        created_at: str,
        file_count: int = 0,
        status: str = "待完成",
        is_selected: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._company_name = company_name
        self._is_selected = is_selected
        self._file_count = file_count
        self._status = status
        self.setMinimumHeight(72)
        self.setMaximumHeight(90)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui(insurance_type, created_at)
        self._update_style()

    def _setup_ui(self, insurance_type: str, created_at: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 左侧图标
        self.icon = IconWidget(FluentIcon.PEOPLE, self)
        self.icon.setFixedSize(32, 32)
        self.icon.setStyleSheet("background-color: #e8f5e9; border-radius: 16px;")
        layout.addWidget(self.icon)

        # 右侧内容
        right = QVBoxLayout()
        right.setSpacing(2)

        # 第一行：公司名称（自动截断）
        self.title_label = QLabel(self._company_name)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1a1a1a; background: transparent; border: none;")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        right.addWidget(self.title_label)

        # 第二行：日期
        date_str = created_at[:16].replace("T", " ") if created_at else ""
        date_label = QLabel(date_str)
        date_label.setStyleSheet("font-size: 11px; color: #999; background: transparent; border: none;")
        right.addWidget(date_label)

        # 第三行：险种 + 附件 + 状态
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)
        bottom_row.setContentsMargins(0, 0, 0, 0)
        type_str = insurance_type or "未分类"
        self.subtitle_label = QLabel(type_str)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #666; background: transparent; border: none;")
        bottom_row.addWidget(self.subtitle_label)

        if self._file_count > 0:
            file_badge = QLabel(f"[{self._file_count}个附件]")
            file_badge.setStyleSheet("font-size: 12px; color: #667eea; background: transparent; border: none;")
            bottom_row.addWidget(file_badge)

        status_color = self.STATUS_COLORS.get(self._status, "#a0aec0")
        status_badge = QLabel(f"●{self._status}")
        status_badge.setStyleSheet(f"font-size: 12px; color: {status_color}; background: transparent; border: none;")
        bottom_row.addWidget(status_badge)

        bottom_row.addStretch()
        right.addLayout(bottom_row)
        layout.addLayout(right, 1)

    def _update_style(self) -> None:
        if self._is_selected:
            self.setStyleSheet("ChatBubble { background-color: #e8f5e9; border: 2px solid #07c160; border-radius: 12px; }")
        else:
            self.setStyleSheet("ChatBubble { background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 12px; } ChatBubble:hover { background-color: #f5f7fa; border-color: #d0d0d0; }")

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_style()

    def mousePressEvent(self, event) -> None:
        self._on_clicked_callback()
        super().mousePressEvent(event)

    def set_clicked_callback(self, callback) -> None:
        self._on_clicked_callback = callback
