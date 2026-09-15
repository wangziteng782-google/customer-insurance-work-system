"""聊天消息气泡组件 - 支持文本 + 图片缩略图（异步加载）"""
import os

import requests

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy,
    QDialog, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

from client.api import BASE_URL

# ── 设计令牌 ──
_PRIMARY = "#1677ff"
_USER_TEXT = "#ffffff"


class ImageViewer(QDialog):
    """图片查看器 - 点击缩略图后放大显示"""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查看图片")
        self.setMinimumSize(400, 300)
        self.resize(800, 600)
        self._url = url
        self._pixmap: QPixmap | None = None
        self._init_ui()
        self._load()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("background: #2a2a2a; border: none;")

        self.image_label = QLabel("加载中...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #2a2a2a; color: #999; font-size: 14px;")
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

    def _load(self):
        """同步加载图片"""
        pixmap = QPixmap()
        try:
            resp = requests.get(self._url, timeout=15)
            if resp.status_code == 200:
                pixmap.loadFromData(resp.content)
        except Exception:
            pass
        self._on_loaded(pixmap)

    def _on_loaded(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.image_label.setText("加载失败")
            return
        self._pixmap = pixmap
        self._fit()

    def _fit(self):
        if self._pixmap:
            vp = self.scroll.viewport().size()
            self.image_label.setPixmap(
                self._pixmap.scaled(vp, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.image_label.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap:
            self._fit()


class _ThumbnailLoader(QThread):
    """后台加载单张缩略图，避免阻塞 UI 主线程"""

    loaded = Signal(QPixmap)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        pixmap = QPixmap()
        if self._url:
            try:
                resp = requests.get(self._url, timeout=10)
                if resp.status_code == 200:
                    pixmap.loadFromData(resp.content)
            except Exception:
                pass
        self.loaded.emit(pixmap)


class ChatMessage(QWidget):
    """单条聊天消息气泡 - 支持文本和图片"""

    SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

    # 类级引用集合，防止后台加载线程被 Python GC 回收
    _active_loaders: set = set()

    def __init__(
        self,
        content: str,
        file_paths: list[str] | None = None,
        is_handler: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
        self._file_paths = file_paths or []
        self._is_handler = is_handler
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        bubble = QWidget()
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bubble.setMaximumWidth(520)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 内勤标签（仅 handler 留言显示）
        if self._is_handler:
            tag = QLabel("内勤留言")
            tag.setStyleSheet("font-size: 11px; color: #999; background: transparent; border: none;")
            layout.addWidget(tag)

        # 文字内容
        if self._content:
            text_label = QLabel(self._content)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            text_label.setStyleSheet(self._text_style())
            layout.addWidget(text_label)

        # 图片缩略图（同步加载）— 仅用户消息展示
        if not self._is_handler:
            image_paths = [p for p in self._file_paths if self._is_image(p)]
            if image_paths:
                img_row = QHBoxLayout()
                img_row.setSpacing(4)
                img_row.setAlignment(Qt.AlignLeft)
                for path in image_paths[:4]:
                    thumb = self._make_thumbnail(path)
                    img_row.addWidget(thumb)
                if len(image_paths) > 4:
                    more_label = QLabel(f"+{len(image_paths) - 4}")
                    more_label.setStyleSheet("font-size: 12px; color: #ccc; background: transparent; padding-left: 4px;")
                    img_row.addWidget(more_label)
                layout.addLayout(img_row)

            # 文件附件（非图片）
            file_paths = [p for p in self._file_paths if not self._is_image(p)]
            if file_paths:
                file_row = QHBoxLayout()
                file_row.setSpacing(4)
                file_row.setAlignment(Qt.AlignLeft)
                for path in file_paths[:3]:
                    file_chip = self._make_file_chip(path)
                    file_row.addWidget(file_chip)
                if len(file_paths) > 3:
                    more_label = QLabel(f"+{len(file_paths) - 3}")
                    more_label.setStyleSheet("font-size: 12px; color: #ccc; background: transparent; padding-left: 4px;")
                    file_row.addWidget(more_label)
                layout.addLayout(file_row)

        bubble.setStyleSheet(self._bubble_style())
        outer.addStretch()
        outer.addWidget(bubble)

    def _bubble_style(self) -> str:
        """气泡样式：用户蓝色 / 内勤灰色"""
        if self._is_handler:
            return """
                QWidget {
                    background-color: #f0f0f0;
                    border-radius: 12px 2px 12px 12px;
                }
            """
        return f"""
            QWidget {{
                background-color: {_PRIMARY};
                border-radius: 12px 2px 12px 12px;
            }}
        """

    def _text_style(self) -> str:
        """文字样式：用户白色 / 内勤深色"""
        if self._is_handler:
            return "font-size: 13px; line-height: 1.55; color: #1a1a2e; background: transparent; border: none;"
        return f"font-size: 13px; line-height: 1.55; color: {_USER_TEXT}; background: transparent; border: none;"

    def _is_image(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in self.SUPPORTED_IMAGE_EXTS

    def _make_thumbnail(self, path: str) -> QLabel:
        """创建缩略图 — 先展示占位符，后台线程加载图片，不阻塞 UI"""
        label = QLabel("加载中...")
        label.setFixedSize(80, 80)
        label.setAlignment(Qt.AlignCenter)
        label.setCursor(Qt.PointingHandCursor)
        label.setStyleSheet(
            "font-size: 11px; color: #ccc; border: 1px solid rgba(255,255,255,0.3); "
            "border-radius: 6px; background: rgba(255,255,255,0.1);"
        )

        url = self._to_url(path)
        label.mousePressEvent = lambda e, u=url: self._open_viewer(u)

        # 后台线程加载图片；主线程仅创建占位符，立即可见
        loader = _ThumbnailLoader(url)
        loader._label = label  # 供主线程 slot 取回对应 label
        ChatMessage._active_loaders.add(loader)  # 阻止 GC
        loader.loaded.connect(self._on_thumbnail_loaded)
        loader.finished.connect(lambda l=loader: ChatMessage._cleanup_loader(l))
        loader.start()
        return label

    @staticmethod
    def _cleanup_loader(loader) -> None:
        """加载线程结束：从引用集合移除并释放"""
        ChatMessage._active_loaders.discard(loader)
        loader.deleteLater()

    def _on_thumbnail_loaded(self, pixmap: QPixmap) -> None:
        """图片下载完成回调（主线程执行）"""
        loader = self.sender()
        if loader is None:
            return
        label = getattr(loader, "_label", None)
        if label is None:
            return
        self._apply_thumbnail(label, pixmap)

    @staticmethod
    def _apply_thumbnail(label: QLabel, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            label.setText("失败")
            label.setStyleSheet(
                "font-size: 11px; color: #ff7875; border: 1px solid rgba(255,120,117,0.3); "
                "border-radius: 6px; background: rgba(255,255,255,0.1);"
            )
        else:
            scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.setStyleSheet("border: 1px solid rgba(255,255,255,0.2); border-radius: 6px;")

    @staticmethod
    def _open_viewer(url: str):
        if url:
            ImageViewer(url).exec()

    def _make_file_chip(self, path: str) -> QWidget:
        """创建文件标签（可点击打开）"""
        from PySide6.QtWidgets import QVBoxLayout

        chip = QWidget()
        chip.setFixedSize(120, 56)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setStyleSheet("""
            QWidget { background-color: #ffffff; border: 1px solid #d9d9d9; border-radius: 6px; }
            QWidget:hover { border-color: #1677ff; background-color: #f0f7ff; }
        """)
        chip.mousePressEvent = lambda e, p=path: os.startfile(self._to_url(p)) if e.button() == Qt.LeftButton else None

        layout = QVBoxLayout(chip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        ext = os.path.splitext(path)[1].lower()
        icon_map = {'.pdf': '📕', '.doc': '📘', '.docx': '📘', '.xls': '📗', '.xlsx': '📗', '.txt': '📄', '.csv': '📊'}
        icon = icon_map.get(ext, '📎')

        icon_label = QLabel(f"{icon} {ext.upper()[1:]}")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #1677ff; border: none; background: transparent;")
        layout.addWidget(icon_label)

        name = os.path.basename(path)
        name_label = QLabel(name[:12] + ('…' if len(name) > 12 else ''))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 9px; color: #666; border: none; background: transparent;")
        layout.addWidget(name_label)

        return chip

    @staticmethod
    def _to_url(path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{BASE_URL}/{path.lstrip('/')}"
