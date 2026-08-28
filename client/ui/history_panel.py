"""左侧历史记录面板 - 保单卡片列表 + 分页"""
import json

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import PushButton, ScrollArea, SearchLineEdit

from client.api import list_chat_tasks


class PolicyCardItem(QWidget):
    """保单卡片项 - 参考豆包风格"""

    def __init__(self, task: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self._task = task
        self._is_selected = is_selected
        self._callback = None
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        # 第一行：任务编号
        task_id = self._task.get("task_id", "未知任务")
        self.title_label = QLabel(task_id)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1d2129;")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.title_label)

        # 第二行：首条消息摘要
        first_content = self._task.get("first_content", "无内容")
        sub_label = QLabel(first_content)
        sub_label.setStyleSheet("font-size: 12px; color: #666;")
        sub_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(sub_label)

        # 第三行：日期 + 消息数
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(4)

        created = self._task.get("created_at", "")
        date_str = created[:10] if created else "-"
        date_label = QLabel(date_str)
        date_label.setStyleSheet("font-size: 11px; color: #999;")
        bottom_row.addWidget(date_label)
        bottom_row.addStretch()

        # 消息数标签
        msg_count = self._task.get("msg_count", 0)
        count_tag = QLabel(f"{msg_count}条")
        count_tag.setStyleSheet("""
            font-size: 11px;
            color: #1677ff;
            border: 1px solid #1677ff;
            border-radius: 4px;
            padding: 1px 4px;
        """)
        bottom_row.addWidget(count_tag)
        layout.addLayout(bottom_row)

    def _update_style(self) -> None:
        if self._is_selected:
            self.setStyleSheet("""
                QWidget {
                    background-color: #f0f7ff;
                    border: 1px solid #1677ff;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
                QWidget:hover {
                    background-color: #f7f8fa;
                    border-color: #d9d9d9;
                }
            """)

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_style()

    def mousePressEvent(self, event) -> None:
        if self._callback:
            self._callback()
        super().mousePressEvent(event)

    def set_clicked_callback(self, callback) -> None:
        self._callback = callback


class HistoryPanel(QWidget):
    """历史记录面板 - 保单卡片列表 + 分页"""

    PAGE_SIZE = 10

    def __init__(self, on_item_clicked, parent: QWidget | None = None):
        super().__init__(parent)
        self._on_item_clicked = on_item_clicked
        self._policies: list[dict] = []
        self._cards: list[PolicyCardItem] = []
        self._selected_index: int = -1
        self._current_page: int = 0
        self._total_count: int = 0
        self._init_ui()
        self._load_history()

    def _init_ui(self) -> None:
        self.setFixedWidth(260)
        self.setStyleSheet("background-color: #f7f8fa; border-right: 1px solid #e5e7eb;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(12, 10, 12, 8)
        title_label = QLabel("保单列表")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a1a;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # 刷新按钮
        refresh_btn = PushButton("↻", self)
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.setStyleSheet("""
            PushButton {
                background-color: #e2e8f0;
                color: #4a5568;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #cbd5e0; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_bar.addWidget(refresh_btn)
        layout.addLayout(title_bar)

        # 搜索框
        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 0, 8, 6)
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("搜索保单...")
        self.search_box.setFixedHeight(30)
        self.search_box.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        # 滚动区域
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #f7f8fa; border: none;")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: #f7f8fa;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 4, 6, 6)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

        # 底部提示
        hint = QLabel("点击切换保单上下文")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 11px; color: #c0c4cc; padding: 4px;")
        layout.addWidget(hint)

        # 分页控制
        page_bar = QHBoxLayout()
        page_bar.setContentsMargins(8, 4, 8, 6)
        self.prev_btn = PushButton("<", self)
        self.prev_btn.setFixedSize(28, 24)
        self.prev_btn.setStyleSheet("""
            PushButton {
                background-color: #ffffff;
                color: #666;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 11px;
            }
            PushButton:hover { color: #1677ff; border-color: #1677ff; }
            PushButton:disabled { color: #ccc; border-color: #eee; }
        """)
        self.prev_btn.clicked.connect(self._on_prev_page)
        page_bar.addWidget(self.prev_btn)

        self.page_label = QLabel("1/1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-size: 12px; color: #888;")
        page_bar.addWidget(self.page_label, 1)

        self.next_btn = PushButton(">", self)
        self.next_btn.setFixedSize(28, 24)
        self.next_btn.setStyleSheet("""
            PushButton {
                background-color: #ffffff;
                color: #666;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 11px;
            }
            PushButton:hover { color: #1677ff; border-color: #1677ff; }
            PushButton:disabled { color: #ccc; border-color: #eee; }
        """)
        self.next_btn.clicked.connect(self._on_next_page)
        page_bar.addWidget(self.next_btn)
        layout.addLayout(page_bar)

    @property
    def _page_count(self) -> int:
        return max(1, (self._total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def _load_history(self) -> None:
        """加载当前页"""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        skip = self._current_page * self.PAGE_SIZE
        try:
            self._tasks = list_chat_tasks(skip=skip, limit=self.PAGE_SIZE)
        except Exception as e:
            self._tasks = []
            print(f"加载任务列表失败: {e}")

        self._total_count = skip + len(self._tasks)
        if len(self._tasks) < self.PAGE_SIZE:
            self._total_count = skip + len(self._tasks)
        else:
            self._total_count = skip + len(self._tasks) + 1

        self._refresh_cards()
        self._update_page_label()

    def _refresh_cards(self) -> None:
        """刷新卡片显示"""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        keyword = self.search_box.text().strip().lower()

        for idx, task in enumerate(self._tasks):
            if keyword:
                searchable = (
                    task.get("task_id", "").lower()
                    + task.get("first_content", "").lower()
                    + task.get("creator", "").lower()
                )
                if keyword not in searchable:
                    continue

            card = PolicyCardItem(task, is_selected=(idx == self._selected_index))
            card.set_clicked_callback(lambda i=idx: self._on_card_clicked(i))
            self._cards.append(card)
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)

    def _update_page_label(self) -> None:
        self.page_label.setText(f"{self._current_page + 1}/{self._page_count}")
        self.prev_btn.setEnabled(self._current_page > 0)
        has_next = len(self._policies) >= self.PAGE_SIZE
        self.next_btn.setEnabled(has_next)

    def _on_prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._load_history()

    def _on_next_page(self) -> None:
        if len(self._policies) >= self.PAGE_SIZE:
            self._current_page += 1
            self._load_history()

    def _on_search(self, text: str) -> None:
        self._refresh_cards()

    def _on_card_clicked(self, index: int) -> None:
        self._selected_index = index
        for i, card in enumerate(self._cards):
            card.set_selected(i == index)
        if index < len(self._tasks):
            self._on_item_clicked(self._tasks[index])

    def refresh(self) -> None:
        """刷新列表"""
        self._current_page = 0
        self._selected_index = -1
        self._load_history()

    def get_selected_task(self) -> dict | None:
        if 0 <= self._selected_index < len(self._tasks):
            return self._tasks[self._selected_index]
        return None
