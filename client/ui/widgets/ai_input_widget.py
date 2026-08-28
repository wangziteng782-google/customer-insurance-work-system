"""AI 识别输入组件 - 支持粘贴文本/图片 + 拖拽文件"""
import os

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QWidget, QFileDialog, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from qfluentwidgets import PushButton


class AiInputWidget(QWidget):
    """AI 识别输入区域 - 粘贴 + 拖拽 + 上传"""

    ai_result_ready = Signal(dict)

    SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    SUPPORTED_FILE_EXTS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv'}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── 单行：标题 + 上传 + AI 按钮 ──
        row = QHBoxLayout()
        row.setSpacing(6)

        title = QLabel("粘贴客户信息")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        row.addWidget(title)
        row.addStretch()

        # 上传按钮
        self.upload_btn = PushButton("上传", self)
        self.upload_btn.setFixedSize(80, 32)
        self.upload_btn.setStyleSheet("""
            PushButton {
                background-color: #e2e8f0;
                color: #4a5568;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                font-size: 13px;
            }
            PushButton:hover { background-color: #cbd5e0; }
        """)
        self.upload_btn.clicked.connect(self._on_upload)
        row.addWidget(self.upload_btn)

        # AI 按钮
        self.ai_btn = PushButton("AI 识别", self)
        self.ai_btn.setFixedSize(110, 32)
        self.ai_btn.setStyleSheet("""
            PushButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #5a6fd6; }
            PushButton:pressed { background-color: #4f63c2; }
            PushButton:disabled { background-color: #a0aec0; }
        """)
        self.ai_btn.clicked.connect(self._on_ai_recognize)
        row.addWidget(self.ai_btn)

        layout.addLayout(row)

        # ── 拖拽区域 ──
        self.drop_frame = QFrame()
        self.drop_frame.setAcceptDrops(True)
        self.drop_frame.setMinimumHeight(60)
        self.drop_frame.setMaximumHeight(80)
        self.drop_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 2px dashed #cbd5e0;
                border-radius: 8px;
            }
        """)
        self.drop_frame.dragEnterEvent = self._on_drag_enter
        self.drop_frame.dropEvent = self._on_drop

        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setAlignment(Qt.AlignCenter)

        self.drop_label = QLabel("拖拽文件到这里，粘贴文本/图片")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("font-size: 13px; color: #a0aec0; border: none; background: transparent;")
        drop_layout.addWidget(self.drop_label)

        layout.addWidget(self.drop_frame)

        # ── 文本输入框 ──
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("直接输入或粘贴文本...")
        self.text_edit.setMinimumHeight(100)
        self.text_edit.setMaximumHeight(150)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f0f2f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #333;
            }
            QTextEdit:focus { border: 1px solid #667eea; }
        """)
        layout.addWidget(self.text_edit)

        # ── 文件列表 ──
        self.file_list_frame = QFrame()
        self.file_list_frame.setStyleSheet("background-color: transparent;")
        self.file_list_layout = QVBoxLayout(self.file_list_frame)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(3)
        self.file_list_frame.hide()
        layout.addWidget(self.file_list_frame)

    # ── 拖拽处理 ──

    def _on_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_frame.setStyleSheet("""
                QFrame {
                    background-color: #edf2f7;
                    border: 2px dashed #667eea;
                    border-radius: 8px;
                }
            """)

    def _on_drop(self, event: QDropEvent) -> None:
        self.drop_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 2px dashed #cbd5e0;
                border-radius: 8px;
            }
        """)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if filepath and os.path.isfile(filepath) and filepath not in self._files:
                    self._files.append(filepath)
            self._refresh_file_list()
            event.acceptProposedAction()

    # ── 文件上传 ──

    def _on_upload(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有支持的文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.pdf *.doc *.docx *.xls *.xlsx *.txt *.csv);;"
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;"
            "文档 (*.pdf *.doc *.docx *.xls *.xlsx *.txt *.csv)"
        )
        if files:
            for f in files:
                if f not in self._files:
                    self._files.append(f)
            self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        while self.file_list_layout.count():
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            self.file_list_frame.hide()
            self.drop_label.setText("拖拽文件到这里，或 Ctrl+V 粘贴文本/图片")
            return

        self.file_list_frame.show()
        self.drop_label.setText(f"已添加 {len(self._files)} 个文件，可继续拖拽或粘贴")

        for idx, filepath in enumerate(self._files):
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filepath)[1].lower()
            icon = "[图]" if ext in self.SUPPORTED_IMAGE_EXTS else "[文]"

            row = QHBoxLayout()
            row.setContentsMargins(8, 3, 8, 3)

            lbl = QLabel(f"{idx + 1}. {icon} {filename}")
            lbl.setStyleSheet("font-size: 13px; color: #4a5568; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()

            # 文件大小
            try:
                size = os.path.getsize(filepath)
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            except OSError:
                size_str = ""
            size_label = QLabel(size_str)
            size_label.setStyleSheet("font-size: 12px; color: #a0aec0; background: transparent;")
            row.addWidget(size_label)

            del_btn = PushButton("✕", self)
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("""
                PushButton {
                    background-color: transparent;
                    color: #ccc;
                    border: none;
                    font-size: 10px;
                }
                PushButton:hover { color: #e53e3e; }
            """)
            del_btn.clicked.connect(lambda checked=False, i=idx: self._on_remove_file(i))
            row.addWidget(del_btn)

            widget = QWidget()
            widget.setLayout(row)
            widget.setStyleSheet("background-color: #f7fafc; border-radius: 4px;")
            self.file_list_layout.addWidget(widget)

    def _on_remove_file(self, index: int) -> None:
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self._refresh_file_list()

    def _on_ai_recognize(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text and not self._files:
            return

        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("识别中...")

        try:
            from client.api import ai_recognize
            result = ai_recognize(text=text)
            if result:
                self.ai_result_ready.emit(result)
            else:
                from client.ui.dialog import warning_dialog
                warning_dialog(self, "AI 识别", "未能从文本中识别出有效信息")
        except Exception as e:
            from client.ui.dialog import error_dialog
            error_dialog(self, "AI 识别失败", f"调用失败：{e}")
        finally:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("AI 识别")

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def get_files(self) -> list[str]:
        return self._files.copy()

    def clear(self) -> None:
        self.text_edit.clear()
        self._files.clear()
        self._refresh_file_list()
