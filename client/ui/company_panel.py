"""右侧保险公司选择面板"""
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import SearchLineEdit


class CompanyPanel(QWidget):
    """保险公司选择面板"""

    company_selected = Signal(str)

    # 常见保险公司
    COMPANIES = [
        "中国人保",
        "中国平安",
        "中国人寿",
        "太平洋保险",
        "新华保险",
        "泰康保险",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._companies = self.COMPANIES.copy()
        self._init_ui()

    def _init_ui(self) -> None:
        self.setFixedWidth(180)
        self.setStyleSheet("background-color: #f7f8fa; border-left: 1px solid #e5e7eb;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(14, 12, 14, 10)
        title_label = QLabel("保险公司")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a1a;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        layout.addLayout(title_bar)

        # 搜索框
        search_row = QHBoxLayout()
        search_row.setContentsMargins(10, 0, 10, 8)
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("搜索公司...")
        self.search_box.setFixedHeight(32)
        self.search_box.setStyleSheet("""
            SearchLineEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
            }
            SearchLineEdit:focus { border: 1px solid #667eea; }
        """)
        self.search_box.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        # 公司列表
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: none;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                padding: 12px 14px;
                margin: 2px 4px;
                border-radius: 8px;
                font-size: 14px;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #f0f2f5;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: #07c160;
                font-weight: bold;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        self._refresh_list()

    def _refresh_list(self) -> None:
        """刷新列表"""
        self.list_widget.clear()
        keyword = self.search_box.text().strip().lower()

        for company in self._companies:
            if keyword and keyword not in company.lower():
                continue
            item = QListWidgetItem(company)
            self.list_widget.addItem(item)

    def _on_search(self, text: str) -> None:
        """搜索过滤"""
        self._refresh_list()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """选中公司"""
        self.company_selected.emit(item.text())

    def get_selected_company(self) -> str | None:
        """获取当前选中的公司"""
        item = self.list_widget.currentItem()
        return item.text() if item else None
