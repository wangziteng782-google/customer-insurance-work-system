"""聊天面板 - 顶部状态栏 + 消息列表 + 输入区（同步上传）"""
import os
import secrets
import tempfile
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QWidget, QFileDialog, QFrame, QProgressBar,
    QApplication, QDialog, QDialogButtonBox, QRadioButton,
    QComboBox, QCompleter, QFormLayout, QLineEdit
)
from PySide6.QtCore import Signal, Qt, QTimer, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QPixmap
from qfluentwidgets import PushButton, ScrollArea

from client.api import create_chat_message, list_chat_messages, list_task_comments, upload_files
from client.ui.widgets.chat_message import ChatMessage

# ── 设计令牌 ──
_PRIMARY = "#1677ff"
_ACCENT = "#d4a853"
_PRIMARY_LIGHT = "#e8f4ff"
_TOP_BG = "#f8f9fa"
_BORDER = "#e5e7eb"
_TEXT_PRIMARY = "#1a1a2e"
_TEXT_SECONDARY = "#6b7280"

_NORMAL_INPUT_STYLE = f"""
    QFrame {{
        border: 1px solid {_BORDER};
        border-radius: 12px;
        background-color: #ffffff;
    }}
"""
_FOCUS_INPUT_STYLE = f"""
    QFrame {{
        border: 1px solid {_PRIMARY};
        border-radius: 12px;
        background-color: #ffffff;
    }}
"""
_DRAG_INPUT_STYLE = f"""
    QFrame {{
        border: 2px solid {_PRIMARY};
        border-radius: 12px;
        background-color: {_PRIMARY_LIGHT};
    }}
"""


class NewPolicyDialog(QDialog):
    """新建保单收集对话框"""

    INSURANCE_COMPANIES = [
        "人保财险", "平安保险", "太平洋保险", "国寿财险",
        "阳光保险", "新华保险", "泰康保险", "太平保险",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("新建保单收集")
        self.setFixedWidth(380)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QLabel { font-size: 13px; color: #3a3a4a; }
            QComboBox { border: 1px solid #d9d9d9; border-radius: 6px; padding: 0 10px; font-size: 13px; }
            QComboBox:focus { border-color: #1677ff; }
            QLineEdit { border: 1px solid #d9d9d9; border-radius: 6px; padding: 0 10px; font-size: 13px; }
            QLineEdit:focus { border-color: #1677ff; }
            QRadioButton { font-size: 13px; spacing: 6px; }
            QPushButton { border-radius: 6px; font-size: 13px; padding: 6px 16px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("新建保单收集")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a2e;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        self.company_combo = QComboBox()
        self.company_combo.setEditable(True)
        self.company_combo.setInsertPolicy(QComboBox.NoInsert)
        self.company_combo.setPlaceholderText("搜索或选择保险公司")
        self.company_combo.addItems(self.INSURANCE_COMPANIES)
        completer = QCompleter(self.INSURANCE_COMPANIES, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.company_combo.setCompleter(completer)
        self.company_combo.setFixedHeight(36)
        form.addRow("保险公司 *", self.company_combo)

        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("输入客户公司名称")
        self.customer_edit.setFixedHeight(36)
        form.addRow("客户公司 *", self.customer_edit)

        type_widget = QWidget()
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(10)
        self.rb_new = QRadioButton("新投")
        self.rb_endorsement = QRadioButton("批改")
        self.rb_new.setChecked(True)
        type_layout.addWidget(self.rb_new)
        type_layout.addWidget(self.rb_endorsement)
        type_layout.addStretch()
        form.addRow("保单类型 *", type_widget)
        layout.addLayout(form)
        layout.addStretch()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok,
            Qt.Horizontal, self
        )
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        ok_btn.setText("确认开始")
        cancel_btn.setText("取消")
        ok_btn.setFixedSize(90, 32)
        cancel_btn.setFixedSize(70, 32)
        ok_btn.setStyleSheet("QPushButton { background: #1677ff; color: white; border: none; font-weight: 500; }")
        cancel_btn.setStyleSheet("QPushButton { background: #f5f5f5; color: #6b7280; border: 1px solid #d9d9d9; }")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_company(self) -> str:
        return self.company_combo.currentText().strip()

    def get_type(self) -> int:
        return 2 if self.rb_endorsement.isChecked() else 1

    def get_customer_company(self) -> str:
        return self.customer_edit.text().strip()

    def accept(self) -> None:
        if not self.get_company():
            self.company_combo.setFocus()
            return
        if not self.get_customer_company():
            self.customer_edit.setFocus()
            return
        super().accept()


class ImageTextEdit(QTextEdit):
    """支持拖拽和粘贴图片的文本输入框"""
    image_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.on_send: callable = None

    def focusInEvent(self, event):
        frame = self.parent()
        if isinstance(frame, QFrame):
            frame.setStyleSheet(_FOCUS_INPUT_STYLE)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        frame = self.parent()
        if isinstance(frame, QFrame):
            frame.setStyleSheet(_NORMAL_INPUT_STYLE)
        super().focusOutEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and os.path.isfile(path):
                    self.image_dropped.emit(path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ControlModifier:
                self.insertPlainText("\n")
                return
            if self.on_send:
                self.on_send()
                return
        if event.matches(QKeySequence.Paste):
            clipboard = QApplication.clipboard()
            mime = clipboard.mimeData()
            if mime.hasImage():
                pixmap = clipboard.pixmap()
                if not pixmap.isNull():
                    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    pixmap.save(tmp.name, "PNG")
                    self.image_dropped.emit(tmp.name)
                    return
            elif mime.hasUrls():
                for url in mime.urls():
                    path = url.toLocalFile()
                    if path and os.path.isfile(path):
                        self.image_dropped.emit(path)
                return
        super().keyPressEvent(event)


class _ChatHistoryLoader(QThread):
    """后台拉取聊天记录 + 留言数据，避免阻塞 UI"""

    loaded = Signal(list, list)   # messages, comments
    failed = Signal(str)

    def __init__(self, task_id: str, parent=None):
        super().__init__(parent)
        self._task_id = task_id

    def run(self) -> None:
        try:
            messages = list_chat_messages(self._task_id)
            comments = list_task_comments(self._task_id)
            self.loaded.emit(messages, comments)
        except Exception as e:
            self.failed.emit(str(e))


class ChatPanel(QWidget):
    """聊天面板 - 对话式保单资料收集"""

    task_created = Signal(str)

    # 类级引用集合，防止后台拉取线程被 Python GC 回收
    _active_history_loaders: set = set()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._current_task_id: str = ""
        self._insurance_company: str = ""
        self._policy_type: int = 1
        self._customer_company: str = ""
        self._history_gen: int = 0          # 用于丢弃旧请求结果
        self._loading_label: QLabel | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.top_bar = self._create_top_bar()
        layout.addWidget(self.top_bar)

        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #fafafa; border: none;")

        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background-color: #fafafa;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(20, 16, 20, 16)
        self.msg_layout.setSpacing(12)
        self.msg_layout.addStretch()

        self.scroll_area.setWidget(self.msg_container)
        layout.addWidget(self.scroll_area, 1)

        input_area = self._create_input_area()
        layout.addWidget(input_area)

        self._set_input_enabled(False)

        self._add_message("你好！可粘贴客户资料或拖拽图片到输入框，点击发送进行 AI 识别。")

    def _create_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background-color: {_TOP_BG}; border-bottom: 1px solid {_BORDER};")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        self.policy_name_label = QLabel("当前任务：未选择")
        self.policy_name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {_PRIMARY};")
        layout.addWidget(self.policy_name_label)

        layout.addSpacing(16)

        self.date_label = QLabel("创建日期：-")
        self.date_label.setStyleSheet(f"font-size: 12px; color: {_TEXT_SECONDARY};")
        layout.addWidget(self.date_label)

        layout.addSpacing(16)

        self.img_count_label = QLabel("已收集图片：0 张")
        self.img_count_label.setStyleSheet(f"font-size: 12px; color: {_TEXT_SECONDARY};")
        layout.addWidget(self.img_count_label)

        layout.addStretch()

        self.new_btn = PushButton("开启新保单收集", self)
        new_btn = self.new_btn
        new_btn.setFixedSize(130, 30)
        new_btn.setStyleSheet(f"""
            PushButton {{
                background-color: {_PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            PushButton:hover {{ background-color: #4096ff; }}
            PushButton:pressed {{ background-color: #0958d9; }}
        """)
        new_btn.clicked.connect(self._on_new_policy)
        layout.addWidget(new_btn)

        return bar

    def _create_input_area(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background-color: #ffffff; border-top: 1px solid #f0f0f0;")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(16, 8, 16, 12)
        outer.setSpacing(6)

        # 上传进度条（平时隐藏）
        self.upload_progress = QProgressBar()
        self.upload_progress.setMaximumHeight(3)
        self.upload_progress.setTextVisible(False)
        self.upload_progress.setRange(0, 0)
        self.upload_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {_PRIMARY};
                border-radius: 1px;
            }}
        """)
        self.upload_progress.hide()
        outer.addWidget(self.upload_progress)

        self.input_frame = QFrame()
        self.input_frame.setAcceptDrops(True)
        self.input_frame.setStyleSheet(_NORMAL_INPUT_STYLE)
        self.input_frame.dragEnterEvent = self._on_drag_enter
        self.input_frame.dragLeaveEvent = self._on_drag_leave
        self.input_frame.dropEvent = self._on_drop

        frame_layout = QVBoxLayout(self.input_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.preview_wrap = QWidget()
        self.preview_wrap.hide()
        self.preview_layout = QHBoxLayout(self.preview_wrap)
        self.preview_layout.setContentsMargins(12, 6, 12, 0)
        self.preview_layout.setSpacing(6)
        self.preview_layout.setAlignment(Qt.AlignLeft)
        frame_layout.addWidget(self.preview_wrap)

        self.text_edit = ImageTextEdit(self.input_frame)
        self.text_edit.setPlaceholderText("输入文字，拖拽/粘贴图片，点击发送")
        self.text_edit.setMinimumHeight(56)
        self.text_edit.setMaximumHeight(110)
        self.text_edit.image_dropped.connect(self._on_image_pasted)
        self.text_edit.on_send = self._on_send
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: none;
                padding: 10px 14px;
                font-size: 13px;
                color: {_TEXT_PRIMARY};
                background: transparent;
                selection-background-color: {_PRIMARY};
                selection-color: #ffffff;
            }}
            QTextEdit::placeholder {{
                color: #c0c4cc;
            }}
        """)
        frame_layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 0, 10, 8)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.upload_btn = PushButton("上传图片", self)
        upload_btn = self.upload_btn
        upload_btn.setFixedSize(70, 28)
        upload_btn.setStyleSheet(f"""
            PushButton {{
                background-color: transparent;
                color: {_TEXT_SECONDARY};
                border: 1px solid {_BORDER};
                border-radius: 6px;
                font-size: 12px;
            }}
            PushButton:hover {{
                color: {_PRIMARY};
                border-color: {_PRIMARY};
                background-color: {_PRIMARY_LIGHT};
            }}
        """)
        upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(upload_btn)

        self.send_btn = PushButton("发送", self)
        send_btn = self.send_btn
        send_btn.setFixedSize(58, 28)
        send_btn.setStyleSheet(f"""
            PushButton {{
                background-color: {_PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            PushButton:hover {{ background-color: #4096ff; }}
            PushButton:pressed {{ background-color: #0958d9; }}
            PushButton:disabled {{ background-color: #d9d9d9; color: #999; }}
        """)
        send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(send_btn)

        frame_layout.addLayout(btn_row)
        outer.addWidget(self.input_frame)

        return wrapper

    def _set_input_enabled(self, enabled: bool) -> None:
        self.text_edit.setEnabled(enabled)
        self.upload_btn.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.input_frame.setAcceptDrops(enabled)
        if enabled:
            self.text_edit.setPlaceholderText("输入文字，拖拽/粘贴图片，点击发送")
        else:
            self.text_edit.setPlaceholderText("请先点击「开启新保单收集」创建任务")

    def _add_message(self, content: str, file_paths: list[str] | None = None,
                     is_handler: bool = False) -> None:
        msg = ChatMessage(content=content, file_paths=file_paths, is_handler=is_handler)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, msg)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_user_message(self, text: str, file_paths: list[str] | None = None) -> None:
        self._add_message(text, file_paths=file_paths)

    def clear_messages(self) -> None:
        """清空所有消息"""
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._files.clear()

    @staticmethod
    def _generate_task_id() -> str:
        return "TK-" + secrets.token_hex(4).upper()

    def _on_send(self) -> str | None:
        """发送按钮 - 同步上传"""
        text = self.text_edit.toPlainText().strip()
        if not text and not self._files:
            return None

        new_task_id = None
        if not self._current_task_id:
            self._current_task_id = self._generate_task_id()
            new_task_id = self._current_task_id

        # 有文件 → 同步上传
        file_paths: list[str] = []
        if self._files:
            self.upload_progress.show()
            self.upload_btn.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.new_btn.setEnabled(False)
            # 让进度条先显示
            QApplication.processEvents()
            try:
                result = upload_files(self._current_task_id, self._files[:])
                file_paths = result.get("file_paths", [])
            except Exception as e:
                print(f"文件上传失败: {e}")
            finally:
                self.upload_progress.hide()
                self.upload_btn.setEnabled(True)
                self.send_btn.setEnabled(True)
                self.new_btn.setEnabled(True)

        self._do_send(text, file_paths, new_task_id)
        return new_task_id

    def _do_send(self, text: str, file_paths: list[str], new_task_id: str | None):
        """实际发送逻辑"""
        if text or file_paths:
            self.add_user_message(text, file_paths=file_paths if file_paths else None)

        if text or file_paths:
            try:
                create_chat_message(
                    task_id=self._current_task_id,
                    content=text,
                    file_paths=file_paths if file_paths else None,
                    user_id=2,
                    insurance_company=self._insurance_company,
                    business_type=self._policy_type,
                    customer_company=self._customer_company,
                )
            except Exception as e:
                print(f"保存消息失败: {e}")

        if new_task_id:
            self.task_created.emit(new_task_id)

        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
        self._set_drag_style(False)

    def _on_image_pasted(self, path: str) -> None:
        if path not in self._files:
            self._files.append(path)
            self._refresh_preview()

    def _on_upload(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;"
            "文档 (*.pdf *.doc *.docx *.xls *.xlsx *.txt *.csv);;"
            "所有文件 (*)"
        )
        if files:
            for f in files:
                if f not in self._files:
                    self._files.append(f)
            self._refresh_preview()

    def _set_drag_style(self, active: bool) -> None:
        if active:
            self.input_frame.setStyleSheet(_DRAG_INPUT_STYLE)
        else:
            still_focus = self.text_edit.hasFocus()
            self.input_frame.setStyleSheet(_FOCUS_INPUT_STYLE if still_focus else _NORMAL_INPUT_STYLE)

    def _on_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_style(True)

    def _on_drag_leave(self, event) -> None:
        self._set_drag_style(False)

    def _on_drop(self, event: QDropEvent) -> None:
        self._set_drag_style(False)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if filepath and os.path.isfile(filepath) and filepath not in self._files:
                    self._files.append(filepath)
            self._refresh_preview()
            event.acceptProposedAction()

    def _refresh_preview(self) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            self.preview_wrap.hide()
            return

        self.preview_wrap.show()
        for idx, filepath in enumerate(self._files[:8]):
            self._add_preview_item(idx, filepath)

    def _add_preview_item(self, idx: int, filepath: str) -> None:
        ext = os.path.splitext(filepath)[1].lower()
        image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
        is_image = ext in image_exts

        item = QFrame()
        item.setFixedSize(60, 68)
        item.setStyleSheet("background-color: #f5f5f5; border: 1px solid #e8e8e8; border-radius: 6px;")
        item.setCursor(Qt.PointingHandCursor)
        item.mousePressEvent = lambda e, p=filepath: os.startfile(p) if e.button() == Qt.LeftButton else None

        content = QLabel(item)
        content.setGeometry(4, 4, 52, 48)
        content.setAlignment(Qt.AlignCenter)
        content.setStyleSheet("border: none; background: transparent;")

        if is_image:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(52, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                content.setPixmap(scaled)
            else:
                content.setText("图")
                content.setStyleSheet("font-size: 10px; color: #999;")
        else:
            icon_map = {'.pdf': 'PDF', '.doc': 'DOC', '.docx': 'DOC',
                        '.xls': 'XLS', '.xlsx': 'XLS', '.txt': 'TXT', '.csv': 'CSV'}
            icon = icon_map.get(ext, '文件')
            content.setText(f"📄{icon}")
            content.setStyleSheet("font-size: 11px; color: #1677ff; font-weight: bold;")

            name_label = QLabel(item)
            name_label.setGeometry(2, 52, 56, 14)
            name = os.path.basename(filepath)
            name_label.setText(name[:8] + ('…' if len(name) > 8 else ''))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("font-size: 9px; color: #999; border: none; background: transparent;")

        del_btn = PushButton("×", item)
        del_btn.setGeometry(44, -2, 18, 18)
        del_btn.setStyleSheet("""
            PushButton {
                background-color: #ff4d4f;
                color: white;
                border: none;
                border-radius: 9px;
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }
            PushButton:hover { background-color: #ff7875; }
        """)
        del_btn.clicked.connect(lambda checked=False, i=idx: self._on_remove_file(i))

        self.preview_layout.addWidget(item)

    def _on_remove_file(self, index: int) -> None:
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self._refresh_preview()

    def _on_new_policy(self) -> None:
        dialog = NewPolicyDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        company = dialog.get_company()
        if not company:
            return
        self._insurance_company = company
        self._policy_type = dialog.get_type()
        self._customer_company = dialog.get_customer_company()
        self._current_task_id = ""

        type_label = "批改" if self._policy_type == 2 else "新投"
        self.policy_name_label.setText(f"{company} · {type_label}")
        self.date_label.setText(f"创建日期：{datetime.now().strftime('%Y-%m-%d')}")
        self.img_count_label.setText("已收集图片：0 张")
        self.clear_messages()
        self._set_drag_style(False)
        self._set_input_enabled(True)

    def set_current_task(self, task: dict | None) -> None:
        if task:
            self._current_task_id = task.get("task_id", "")
            self._insurance_company = task.get("insurance_company", "") or ""
            self._policy_type = task.get("business_type", 1) or 1
            self._customer_company = task.get("customer_company", "") or ""
            insurance = task.get("insurance_company", "") or "-"
            customer = task.get("customer_company", "") or "-"
            self.policy_name_label.setText(f"{insurance} · {customer}")
            created = task.get("created_at", "-")
            if created:
                created = str(created)[:19].replace("T", " ")
            self.date_label.setText(f"创建日期：{created}")
            self.img_count_label.setText(f"消息数：{task.get('msg_count', 0)}")
            self.clear_messages()
            self._load_chat_history(self._current_task_id)
            self._set_input_enabled(True)
        else:
            self._on_new_policy()

    def _load_chat_history(self, task_id: str) -> None:
        """加载聊天记录 — 立即显示加载提示，后台拉取数据，主线程渲染。

        关键点：UI 不再被图片下载阻塞。文字消息会先渲染出来，每张缩略图
        在 ChatMessage 内部用独立后台线程加载，主线程始终流畅。
        """
        self.clear_messages()
        self._show_loading_hint()  # 立即显示「加载消息中...」

        # 用 generation 计数丢弃旧请求结果，避免快速切换任务时旧数据覆盖新数据
        self._history_gen += 1
        gen = self._history_gen

        loader = _ChatHistoryLoader(task_id)
        ChatPanel._active_history_loaders.add(loader)  # 阻止 GC
        loader.loaded.connect(
            lambda msgs, comments, g=gen: self._on_history_loaded(msgs, comments, g)
        )
        loader.failed.connect(
            lambda err, g=gen: self._on_history_failed(err, g)
        )
        loader.finished.connect(
            lambda l=loader: ChatPanel._cleanup_history_loader(l)
        )
        loader.start()

    @staticmethod
    def _cleanup_history_loader(loader) -> None:
        """后台拉取线程结束：从引用集合移除并释放"""
        ChatPanel._active_history_loaders.discard(loader)
        loader.deleteLater()

    def _show_loading_hint(self) -> None:
        """在消息列表中显示「加载消息中...」占位"""
        self._hide_loading_hint()
        loading = QLabel("加载消息中...")
        loading.setAlignment(Qt.AlignCenter)
        loading.setStyleSheet(
            "color: #999; font-size: 13px; padding: 24px; "
            "background: transparent; border: none;"
        )
        self._loading_label = loading
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, loading)
        QApplication.processEvents()  # 立即渲染占位符

    def _hide_loading_hint(self) -> None:
        if self._loading_label is not None:
            self._loading_label.setParent(None)
            self._loading_label.deleteLater()
            self._loading_label = None

    def _on_history_loaded(self, messages: list, comments: list, gen: int) -> None:
        """后台拉取完成回调（主线程）"""
        if gen != self._history_gen:
            return  # 旧请求结果，丢弃
        self._hide_loading_hint()
        self._render_history(messages, comments)

    def _on_history_failed(self, err: str, gen: int) -> None:
        """后台拉取失败回调（主线程）"""
        if gen != self._history_gen:
            return
        self._hide_loading_hint()
        self._add_message(f"加载失败: {err}")

    def _render_history(self, messages: list, comments: list) -> None:
        """主线程渲染聊天记录：合并 + 排序 + 逐条添加（图片异步加载）"""
        # 合并 + 排序
        timeline: list[tuple[str, str, dict]] = []
        for msg in messages:
            timeline.append(("user", msg.get("created_at", ""), msg))
        for c in comments:
            timeline.append(("handler", c.get("created_at", ""), c))
        timeline.sort(key=lambda x: x[1])

        # 重排：文字在前、图片在后
        reordered: list[tuple[str, str, dict]] = []
        i = 0
        while i < len(timeline):
            curr_type, curr_time, curr = timeline[i]
            nxt_type, nxt_time, nxt = timeline[i + 1] if i + 1 < len(timeline) else ("", "", {})
            if (curr_type == nxt_type == "user"
                    and not curr.get("content") and curr.get("file_paths")
                    and nxt.get("content") and not nxt.get("file_paths")):
                reordered.append((nxt_type, nxt_time, nxt))
                reordered.append((curr_type, curr_time, curr))
                i += 2
            else:
                reordered.append((curr_type, curr_time, curr))
                i += 1

        # 逐条渲染（文字立即可见，缩略图在后台线程加载）
        for item_type, _, data in reordered:
            content = data.get("content", "") or ""
            file_paths = data.get("file_paths") or None
            is_handler = (item_type == "handler")
            self._add_message(content, file_paths=file_paths, is_handler=is_handler)
            QApplication.processEvents()  # 让每条文字消息立即显示

    def clear(self) -> None:
        """清空输入"""
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
