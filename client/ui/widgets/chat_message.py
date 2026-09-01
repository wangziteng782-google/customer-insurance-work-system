"""聊天消息气泡组件 - 支持文本 + 图片缩略图"""
import os
import tempfile

import requests

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from client.api import BASE_URL

# ── 设计令牌 ──
_PRIMARY = "#1677ff"        # 用户气泡 - 蓝色
_USER_TEXT = "#ffffff"      # 用户文字
_SYSTEM_BG = "#f2f3f5"      # 系统气泡背景
_SYSTEM_TEXT = "#1a1a2e"    # 系统文字


class ChatMessage(QWidget):
    """单条聊天消息气泡 - 支持文本和图片"""

    SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

    def __init__(
        self,
        content: str,
        msg_type: str = "user",  # user | system
        file_paths: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
        self._msg_type = msg_type
        self._file_paths = file_paths or []
        self._init_ui()

    def _init_ui(self) -> None:
        # 外层布局：控制对齐
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 气泡容器（垂直：文字 + 图片）
        bubble = QWidget()
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bubble.setMaximumWidth(520)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 文字内容（如果有）
        if self._content:
            text_label = QLabel(self._content)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if self._msg_type == "user":
                text_label.setStyleSheet(f"font-size: 13px; line-height: 1.55; color: {_USER_TEXT}; background: transparent; border: none;")
            else:
                text_label.setStyleSheet(f"font-size: 13px; line-height: 1.55; color: {_SYSTEM_TEXT}; background: transparent; border: none;")
            layout.addWidget(text_label)

        # 图片缩略图
        image_paths = [p for p in self._file_paths if self._is_image(p)]
        if image_paths:
            img_row = QHBoxLayout()
            img_row.setSpacing(4)
            img_row.setAlignment(Qt.AlignLeft)
            for path in image_paths[:4]:  # 最多显示4张
                thumb = self._make_thumbnail(path)
                img_row.addWidget(thumb)
            if len(image_paths) > 4:
                more_label = QLabel(f"+{len(image_paths) - 4}")
                more_label.setStyleSheet("font-size: 12px; color: #999; background: transparent;")
                img_row.addWidget(more_label)
            layout.addLayout(img_row)

        # 气泡样式
        if self._msg_type == "user":
            bubble.setStyleSheet(f"""
                QWidget {{
                    background-color: {_PRIMARY};
                    border-radius: 12px 2px 12px 12px;
                }}
            """)
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            bubble.setStyleSheet(f"""
                QWidget {{
                    background-color: {_SYSTEM_BG};
                    border-radius: 2px 12px 12px 12px;
                }}
            """)
            outer.addWidget(bubble)
            outer.addStretch()

    def _is_image(self, path: str) -> bool:
        """判断路径是否为图片"""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.SUPPORTED_IMAGE_EXTS

    def _make_thumbnail(self, path: str) -> QLabel:
        """创建缩略图标签"""
        label = QLabel()
        label.setFixedSize(80, 80)
        label.setAlignment(Qt.AlignCenter)

        # 转为完整 URL
        url = self._to_url(path)
        if not url:
            return self._placeholder(label)

        # 下载到临时文件
        tmp_path = self._download(url)
        if not tmp_path:
            return self._placeholder(label)

        pixmap = QPixmap(tmp_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            label.setPixmap(scaled)
        else:
            return self._placeholder(label)

        return label

    @staticmethod
    def _placeholder(label: QLabel) -> QLabel:
        """占位符"""
        label.setText("图")
        label.setStyleSheet("font-size: 12px; color: #999; border: 1px solid #ddd; border-radius: 4px;")
        return label

    @staticmethod
    def _to_url(path: str) -> str:
        """路径转 URL"""
        if path.startswith("http"):
            return path
        # 相对路径 → 拼接 BASE_URL
        return f"{BASE_URL}/{path.lstrip('/')}"

    @staticmethod
    def _download(url: str) -> str | None:
        """下载文件到临时目录，返回本地路径"""
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            ext = os.path.splitext(url)[1] or ".png"
            fd, tmp = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(resp.content)
            return tmp
        except Exception:
            return None
