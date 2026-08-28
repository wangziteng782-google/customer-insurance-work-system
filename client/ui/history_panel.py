"""左侧历史记录面板 - 紧凑分页列表"""
import json

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from qfluentwidgets import PushButton, ScrollArea, SearchLineEdit

from client.api import list_new_policies
from client.ui.widgets.chat_bubble import ChatBubble


class HistoryPanel(QWidget):
    """历史记录面板 - 分页"""

    PAGE_SIZE = 10

    def __init__(self, on_item_clicked, parent: QWidget | None = None):
        super().__init__(parent)
        self._on_item_clicked = on_item_clicked
        self._policies: list[dict] = []
        self._bubbles: list[ChatBubble] = []
        self._selected_index: int = -1
        self._current_page: int = 0
        self._total_count: int = 0
        self._init_ui()
        self._load_history()

    def _init_ui(self) -> None:
        self.setFixedWidth(240)
        self.setStyleSheet("background-color: #f7f8fa; border-right: 1px solid #e5e7eb;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(12, 10, 12, 8)
        title_label = QLabel("历史")
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #1a1a1a;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # 刷新按钮
        refresh_btn = PushButton("↻", self)
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.setStyleSheet("""
            PushButton {
                background-color: #e2e8f0;
                color: #4a5568;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #cbd5e0; }
            PushButton:pressed { background-color: #a0aec0; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_bar.addWidget(refresh_btn)

        new_btn = PushButton("新建", self)
        new_btn.setFixedSize(65, 32)
        new_btn.setStyleSheet("""
            PushButton {
                background-color: #07c160;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #06ad56; }
            PushButton:pressed { background-color: #059a4c; }
        """)
        new_btn.clicked.connect(self._on_new_clicked)
        title_bar.addWidget(new_btn)
        layout.addLayout(title_bar)

        # 搜索框
        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 0, 8, 6)
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("搜索...")
        self.search_box.setFixedHeight(32)
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
        self.container_layout.setContentsMargins(8, 4, 8, 8)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

        # 分页控制
        page_bar = QHBoxLayout()
        page_bar.setContentsMargins(8, 6, 8, 6)
        self.prev_btn = PushButton("<", self)
        self.prev_btn.setFixedSize(32, 26)
        self.prev_btn.setStyleSheet("""
            PushButton {
                background-color: #e2e8f0;
                color: #4a5568;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            PushButton:hover { background-color: #cbd5e0; }
            PushButton:disabled { color: #cbd5e0; }
        """)
        self.prev_btn.clicked.connect(self._on_prev_page)
        page_bar.addWidget(self.prev_btn)

        self.page_label = QLabel("1/1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-size: 13px; color: #666;")
        page_bar.addWidget(self.page_label, 1)

        self.next_btn = PushButton(">", self)
        self.next_btn.setFixedSize(32, 26)
        self.next_btn.setStyleSheet("""
            PushButton {
                background-color: #e2e8f0;
                color: #4a5568;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            PushButton:hover { background-color: #cbd5e0; }
            PushButton:disabled { color: #cbd5e0; }
        """)
        self.next_btn.clicked.connect(self._on_next_page)
        page_bar.addWidget(self.next_btn)
        layout.addLayout(page_bar)

    @property
    def _page_count(self) -> int:
        return max(1, (self._total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def _load_history(self) -> None:
        """加载当前页"""
        for bubble in self._bubbles:
            bubble.deleteLater()
        self._bubbles.clear()

        skip = self._current_page * self.PAGE_SIZE
        try:
            self._policies = list_new_policies(skip=skip, limit=self.PAGE_SIZE)
        except Exception as e:
            self._policies = []
            print(f"加载历史记录失败: {e}")

        # 估算总数（如果返回满页，说明可能还有更多）
        self._total_count = skip + len(self._policies)
        if len(self._policies) < self.PAGE_SIZE:
            # 最后一页，总数就是当前数量
            self._total_count = skip + len(self._policies)
        else:
            # 可能还有下一页，先假设至少多一页
            self._total_count = skip + len(self._policies) + 1

        self._refresh_bubbles()
        self._update_page_label()

    def _refresh_bubbles(self) -> None:
        """刷新气泡显示"""
        for bubble in self._bubbles:
            bubble.deleteLater()
        self._bubbles.clear()

        keyword = self.search_box.text().strip().lower()

        for idx, policy in enumerate(self._policies):
            if keyword and keyword not in policy.get("company_name", "").lower():
                continue

            file_count = 0
            file_paths_raw = policy.get("file_paths")
            if file_paths_raw:
                try:
                    paths = json.loads(file_paths_raw) if isinstance(file_paths_raw, str) else file_paths_raw
                    file_count = len(paths) if isinstance(paths, list) else 0
                except (json.JSONDecodeError, TypeError):
                    file_count = 0

            bubble = ChatBubble(
                company_name=policy.get("company_name", ""),
                insurance_type=policy.get("insurance_type", ""),
                created_at=policy.get("created_at", ""),
                file_count=file_count,
                status=policy.get("status", "待完成"),
            )
            bubble.set_clicked_callback(lambda i=idx: self._on_bubble_clicked(i))
            self._bubbles.append(bubble)
            self.container_layout.insertWidget(self.container_layout.count() - 1, bubble)

    def _update_page_label(self) -> None:
        """更新分页标签"""
        self.page_label.setText(f"{self._current_page + 1}/{self._page_count}")
        self.prev_btn.setEnabled(self._current_page > 0)
        # 如果返回数量等于页面大小，说明可能有下一页
        has_next = len(self._policies) >= self.PAGE_SIZE
        self.next_btn.setEnabled(has_next)

    def _on_prev_page(self) -> None:
        """上一页"""
        if self._current_page > 0:
            self._current_page -= 1
            self._load_history()

    def _on_next_page(self) -> None:
        """下一页"""
        if len(self._policies) >= self.PAGE_SIZE:
            self._current_page += 1
            self._load_history()

    def _on_search(self, text: str) -> None:
        """搜索过滤（本地过滤当前页）"""
        self._refresh_bubbles()

    def _on_bubble_clicked(self, index: int) -> None:
        """气泡点击"""
        self._selected_index = index
        for i, bubble in enumerate(self._bubbles):
            bubble.set_selected(i == index)
        if self._policies:
            self._on_item_clicked(self._policies[index])

    def _on_new_clicked(self) -> None:
        """新建按钮"""
        self._selected_index = -1
        for bubble in self._bubbles:
            bubble.set_selected(False)
        self._on_item_clicked(None)

    def refresh(self) -> None:
        """刷新列表（回到第一页）"""
        self._current_page = 0
        self._load_history()

    def get_selected_policy(self) -> dict | None:
        if 0 <= self._selected_index < len(self._policies):
            return self._policies[self._selected_index]
        return None
