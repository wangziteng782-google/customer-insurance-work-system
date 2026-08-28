"""文件展示组件 - 图片缩略图 + 文件列表"""
import os

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QDesktopServices
from qfluentwidgets import PushButton


class FileDisplayWidget(QWidget):
    """附件展示区 - 点击查看原文件"""

    SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 标题行
        header = QHBoxLayout()
        self.title_label = QLabel("附件")
        self.title_label.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        header.addWidget(self.title_label)
        header.addStretch()
        layout.addLayout(header)

        # 文件内容区
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(self.content_widget)

        layout.addStretch()
        self.hide()  # 默认隐藏

    def set_files(self, files: list[str] | None) -> None:
        """设置要显示的文件列表"""
        # 清除旧内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._files = files or []

        if not self._files:
            self.hide()
            return

        self.show()
        for filepath in self._files:
            if not os.path.exists(filepath):
                continue
            ext = os.path.splitext(filepath)[1].lower()
            if ext in self.SUPPORTED_IMAGE_EXTS:
                self._add_image_thumbnail(filepath)
            else:
                self._add_file_item(filepath)

    def _add_image_thumbnail(self, filepath: str) -> None:
        """添加图片缩略图"""
        frame = QFrame()
        frame.setFixedSize(72, 72)
        frame.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 6px; background: #fafafa;")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)

        # 缩略图
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            scaled = pixmap.scaled(68, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(scaled)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setFixedSize(68, 68)
            img_label.setStyleSheet("border: none; background: transparent;")
            # 点击打开原图
            img_label.setCursor(Qt.PointingHandCursor)
            img_label.mousePressEvent = lambda e, p=filepath: self._open_file(p)
            layout.addWidget(img_label)

        self.content_layout.addWidget(frame)

    def _add_file_item(self, filepath: str) -> None:
        """添加文件项（图标 + 文件名）"""
        filename = os.path.basename(filepath)

        frame = QFrame()
        frame.setFixedSize(72, 72)
        frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: #f7fafc;
            }
            QFrame:hover { border-color: #667eea; background: #edf2f7; }
        """)
        frame.setCursor(Qt.PointingHandCursor)
        frame.mousePressEvent = lambda e, p=filepath: self._open_file(p)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 6, 4, 4)

        # 文件图标
        ext = os.path.splitext(filepath)[1].lower()
        icon = "[文]"
        color = "#666"
        if ext == '.pdf':
            icon = "[PDF]"
            color = "#e53e3e"
        elif ext in ('.doc', '.docx'):
            icon = "[DOC]"
            color = "#3182ce"
        elif ext in ('.xls', '.xlsx'):
            icon = "[XLS]"
            color = "#38a169"
        elif ext == '.txt':
            icon = "[TXT]"

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 22px; color: {color}; border: none; background: transparent;")
        layout.addWidget(icon_label)

        # 文件名（截断）
        display_name = filename if len(filename) <= 8 else filename[:7] + "…"
        name_label = QLabel(display_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 9px; color: #666; border: none; background: transparent;")
        layout.addWidget(name_label)

        self.content_layout.addWidget(frame)

    def _open_file(self, filepath: str) -> None:
        """用系统默认程序打开文件"""
        QDesktopServices.openUrl(__import__("PySide6.QtCore", fromlist=["QUrl"]).QUrl.fromLocalFile(filepath))

    def clear_files(self) -> None:
        """清空文件显示"""
        self.set_files(None)
