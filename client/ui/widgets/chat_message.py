"""聊天消息气泡组件 - 支持文本 + 图片缩略图"""
import os
import tempfile

import requests

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from client.api import BASE_URL

# ── 设计令牌 ──
_PRIMARY = "#1677ff"        # 气泡 - 蓝色
_USER_TEXT = "#ffffff"      # 文字


class ChatMessage(QWidget):
    """单条聊天消息气泡 - 支持文本和图片"""

    SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

    def __init__(
        self,
        content: str,
        file_paths: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._content = content
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
            text_label.setStyleSheet(f"font-size: 13px; line-height: 1.55; color: {_USER_TEXT}; background: transparent; border: none;")
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

        # 文件附件（非图片）
        file_paths = [p for p in self._file_paths if not self._is_image(p)]
        if file_paths:
            file_row = QHBoxLayout()
            file_row.setSpacing(4)
            file_row.setAlignment(Qt.AlignLeft)
            for path in file_paths[:3]:  # 最多显示3个
                file_chip = self._make_file_chip(path)
                file_row.addWidget(file_chip)
            if len(file_paths) > 3:
                more_label = QLabel(f"+{len(file_paths) - 3}")
                more_label.setStyleSheet("font-size: 12px; color: #999; background: transparent;")
                file_row.addWidget(more_label)
            layout.addLayout(file_row)

        # 气泡样式
        bubble.setStyleSheet(f"""
            QWidget {{
                background-color: {_PRIMARY};
                border-radius: 12px 2px 12px 12px;
            }}
        """)
        outer.addStretch()
        outer.addWidget(bubble)

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

        # 文件类型图标
        ext = os.path.splitext(path)[1].lower()
        icon_map = {'.pdf': '📕', '.doc': '📘', '.docx': '📘', '.xls': '📗', '.xlsx': '📗', '.txt': '📄', '.csv': '📊'}
        icon = icon_map.get(ext, '📎')

        icon_label = QLabel(f"{icon} {ext.upper()[1:]}")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #1677ff; border: none; background: transparent;")
        layout.addWidget(icon_label)

        # 文件名
        name = os.path.basename(path)
        name_label = QLabel(name[:12] + ('…' if len(name) > 12 else ''))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 9px; color: #666; border: none; background: transparent;")
        layout.addWidget(name_label)

        return chip

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
    def _download_file(path: str) -> None:
        """下载文件到本地下载目录"""
        url = ChatMessage._to_url(path)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return
            # 下载目录
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(download_dir, exist_ok=True)
            filename = os.path.basename(path)
            filepath = os.path.join(download_dir, filename)
            # 重名加序号
            if os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(os.path.join(download_dir, f"{name}({i}){ext}")):
                    i += 1
                filepath = os.path.join(download_dir, f"{name}({i}){ext}")
            with open(filepath, "wb") as f:
                f.write(resp.content)
            # 打开文件所在文件夹
            os.startfile(os.path.dirname(filepath))
        except Exception as e:
            print(f"下载文件失败: {e}")

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
