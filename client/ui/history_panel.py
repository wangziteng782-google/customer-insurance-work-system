"""左侧历史记录面板 - 保单卡片列表 + 分页"""
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from qfluentwidgets import PushButton, ScrollArea, SearchLineEdit

from client.api import list_chat_tasks

# ── 设计令牌 ──
_PRIMARY = "#1677ff"        # 蓝色 - 主色
_ACCENT = "#d4a853"         # 金色 - 选中/强调
_BG_SIDEBAR = "#f5f6f8"     # 侧栏背景
_BG_CARD = "#ffffff"        # 卡片背景
_BG_HOVER = "#f8f9fa"       # 悬停背景
_TEXT_PRIMARY = "#1a1a2e"   # 主文字
_TEXT_SECONDARY = "#6b7280" # 次文字
_TEXT_MUTED = "#9ca3af"     # 弱化文字
_BADGE_BG = "#e8f4ff"       # 徽标背景
_BADGE_TEXT = "#1677ff"     # 徽标文字


class PolicyCardItem(QWidget):
    """任务卡片项 - 左侧历史列表"""

    def __init__(self, task: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self._task = task
        self._is_selected = is_selected
        self._callback = None
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(72)
        self.setMaximumHeight(90)

        # 主布局：左侧色条 + 内容
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧选中指示条（金色签名元素）
        self.indicator = QWidget()
        self.indicator.setFixedWidth(3)
        main_layout.addWidget(self.indicator)

        # 内容区
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(5)

        # 第一行：保险公司（主标题）+ 消息数徽标
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        insurance_company = self._task.get("insurance_company", "")
        first_content = self._task.get("first_content", "")

        # 主标题
        title_text = insurance_company if insurance_company else (first_content[:15] if first_content else "新任务")
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {_TEXT_PRIMARY};")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top_row.addWidget(self.title_label)
        top_row.addStretch()

        # 消息数圆形徽标
        msg_count = self._task.get("msg_count", 0)
        count_badge = QLabel(f"{msg_count}")
        count_badge.setFixedSize(20, 20)
        count_badge.setAlignment(Qt.AlignCenter)
        count_badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {_BADGE_TEXT};
            background-color: {_BADGE_BG};
            border-radius: 10px;
        """)
        top_row.addWidget(count_badge)
        content_layout.addLayout(top_row)

        # 第二行：首条消息摘要
        if first_content and first_content != insurance_company:
            sub_label = QLabel(first_content)
            sub_label.setStyleSheet(f"font-size: 12px; color: {_TEXT_SECONDARY};")
            sub_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            content_layout.addWidget(sub_label)

        # 第三行：日期
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        created = self._task.get("created_at", "")
        date_str = str(created)[:19].replace("T", " ") if created else "-"
        date_label = QLabel(date_str)
        date_label.setStyleSheet(f"font-size: 11px; color: {_TEXT_MUTED};")
        bottom_row.addWidget(date_label)
        bottom_row.addStretch()
        content_layout.addLayout(bottom_row)

        main_layout.addWidget(content, 1)

    def _update_style(self) -> None:
        if self._is_selected:
            self.indicator.setStyleSheet(f"background-color: {_ACCENT}; border-radius: 2px;")
            self.setStyleSheet(f"""
                QWidget {{ background-color: #f0f7ff; border-radius: 8px; }}
            """)
        else:
            self.indicator.setStyleSheet("background-color: transparent;")
            self.setStyleSheet(f"""
                QWidget {{ background-color: {_BG_CARD}; border-radius: 8px; }}
                QWidget:hover {{ background-color: {_BG_HOVER}; }}
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
        self._tasks: list[dict] = []
        self._cards: list[PolicyCardItem] = []
        self._selected_index: int = -1
        self._current_page: int = 0
        self._total_count: int = 0
        self._init_ui()
        self._load_history()

    def _init_ui(self) -> None:
        self.setFixedWidth(240)
        self.setStyleSheet(f"background-color: {_BG_SIDEBAR}; border-right: 1px solid #e5e7eb;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(10, 10, 10, 8)
        title_label = QLabel("保单列表")
        title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {_PRIMARY}; letter-spacing: 0.5px;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # 刷新按钮
        refresh_btn = PushButton("↻", self)
        refresh_btn.setFixedSize(26, 26)
        refresh_btn.setToolTip("刷新列表")
        refresh_btn.setStyleSheet(f"""
            PushButton {{
                background-color: {_BADGE_BG};
                color: {_PRIMARY};
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
            PushButton:hover {{ background-color: #d6eaff; }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_bar.addWidget(refresh_btn)
        layout.addLayout(title_bar)

        # 搜索框
        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 0, 8, 6)
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("搜索保单...")
        self.search_box.setFixedHeight(28)
        self.search_box.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        # 滚动区域
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"background-color: {_BG_SIDEBAR}; border: none;")

        self.container = QWidget()
        self.container.setStyleSheet(f"background-color: {_BG_SIDEBAR};")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 2, 4, 4)
        self.container_layout.setSpacing(5)
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

        # 底部提示
        hint = QLabel("点击切换保单上下文")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"font-size: 10px; color: {_TEXT_MUTED}; padding: 3px;")
        layout.addWidget(hint)

        # 分页控制
        page_bar = QHBoxLayout()
        page_bar.setContentsMargins(8, 4, 8, 6)
        page_bar.setSpacing(4)
        self.prev_btn = PushButton("<", self)
        self.prev_btn.setFixedSize(26, 22)
        self.prev_btn.setStyleSheet(f"""
            PushButton {{
                background-color: {_BG_CARD};
                color: {_TEXT_SECONDARY};
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 10px;
            }}
            PushButton:hover {{ color: {_PRIMARY}; border-color: {_PRIMARY}; }}
            PushButton:disabled {{ color: #ccc; border-color: #eee; }}
        """)
        self.prev_btn.clicked.connect(self._on_prev_page)
        page_bar.addWidget(self.prev_btn)

        self.page_label = QLabel("1/1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet(f"font-size: 11px; color: {_TEXT_SECONDARY};")
        page_bar.addWidget(self.page_label, 1)

        self.next_btn = PushButton(">", self)
        self.next_btn.setFixedSize(26, 22)
        self.next_btn.setStyleSheet(f"""
            PushButton {{
                background-color: {_BG_CARD};
                color: {_TEXT_SECONDARY};
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 10px;
            }}
            PushButton:hover {{ color: {_PRIMARY}; border-color: {_PRIMARY}; }}
            PushButton:disabled {{ color: #ccc; border-color: #eee; }}
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
        has_next = len(self._tasks) >= self.PAGE_SIZE
        self.next_btn.setEnabled(has_next)

    def _on_prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._load_history()

    def _on_next_page(self) -> None:
        if len(self._tasks) >= self.PAGE_SIZE:
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
