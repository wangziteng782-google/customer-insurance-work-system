"""聊天面板 - 顶部状态栏 + 消息列表 + 输入区"""
import os
import secrets
import tempfile
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QWidget, QFileDialog, QFrame,
    QApplication, QDialog, QDialogButtonBox, QRadioButton,
    QComboBox, QCompleter, QFormLayout, QLineEdit
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence
from qfluentwidgets import PushButton, ScrollArea

from client.api import create_chat_message, list_chat_messages, upload_files
from client.ui.widgets.chat_message import ChatMessage

# ── 设计令牌 ──
_PRIMARY = "#1677ff"        # 蓝色 - 主色
_ACCENT = "#d4a853"         # 金色 - 强调
_PRIMARY_LIGHT = "#e8f4ff"  # 浅蓝背景
_TOP_BG = "#f8f9fa"         # 顶部栏背景
_BORDER = "#e5e7eb"         # 边框
_TEXT_PRIMARY = "#1a1a2e"   # 主文字
_TEXT_SECONDARY = "#6b7280" # 次文字

# 输入框样式
_NORMAL_INPUT_STYLE = f"""
    QFrame {{
        border: 1px solid {_BORDER};
        border-radius: 10px;
        background-color: #ffffff;
    }}
"""
_DRAG_INPUT_STYLE = f"""
    QFrame {{
        border: 2px solid {_PRIMARY};
        border-radius: 10px;
        background-color: {_PRIMARY_LIGHT};
    }}
"""


class NewPolicyDialog(QDialog):
    """新建保单收集对话框 - 选择保险公司和类型"""

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
        # 整体样式 — 一次性设置，避免逐控件重绘
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

        # 标题
        title = QLabel("新建保单收集")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a2e;")
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        # 保险公司（可搜索下拉）
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

        # 客户公司
        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("输入客户公司名称")
        self.customer_edit.setFixedHeight(36)
        form.addRow("客户公司 *", self.customer_edit)

        # 保单类型
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

        # 按钮
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
        """提交前校验必填项"""
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


class ChatPanel(QWidget):
    """聊天面板 - 对话式保单资料收集"""

    # 新建任务时发射，携带 task_id
    task_created = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._current_task_id: str = ""
        self._insurance_company: str = ""
        self._policy_type: str = "new"
        self._customer_company: str = ""
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 顶部状态栏 ──
        self.top_bar = self._create_top_bar()
        layout.addWidget(self.top_bar)

        # ── 消息滚动区 ──
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

        # ── 输入区 ──
        input_area = self._create_input_area()
        layout.addWidget(input_area)

        # 初始禁用输入区（需先创建任务）
        self._set_input_enabled(False)

        # 欢迎消息
        self._add_message(
            "你好！可粘贴客户资料或拖拽图片到输入框，点击发送进行 AI 识别。",
            "system"
        )

    def _create_top_bar(self) -> QWidget:
        """创建顶部状态栏"""
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background-color: {_TOP_BG}; border-bottom: 1px solid {_BORDER};")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # 保险公司 + 类型
        self.policy_name_label = QLabel("当前任务：未选择")
        self.policy_name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {_PRIMARY};")
        layout.addWidget(self.policy_name_label)

        layout.addSpacing(16)

        # 创建日期
        self.date_label = QLabel("创建日期：-")
        self.date_label.setStyleSheet(f"font-size: 12px; color: {_TEXT_SECONDARY};")
        layout.addWidget(self.date_label)

        layout.addSpacing(16)

        # 图片计数
        self.img_count_label = QLabel("已收集图片：0 张")
        self.img_count_label.setStyleSheet(f"font-size: 12px; color: {_TEXT_SECONDARY};")
        layout.addWidget(self.img_count_label)

        layout.addStretch()

        # 开启新保单按钮
        new_btn = PushButton("开启新保单收集", self)
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
        """创建输入区域（含预览、文本框、快捷标签、按钮）"""
        wrapper = QWidget()
        wrapper.setStyleSheet(f"background-color: #ffffff; border-top: 1px solid {_BORDER};")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(16, 8, 16, 12)
        outer.setSpacing(6)

        # 输入框容器（带拖拽）
        self.input_frame = QFrame()
        self.input_frame.setAcceptDrops(True)
        self.input_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {_BORDER};
                border-radius: 10px;
                background-color: #ffffff;
            }}
        """)
        self.input_frame.dragEnterEvent = self._on_drag_enter
        self.input_frame.dragLeaveEvent = self._on_drag_leave
        self.input_frame.dropEvent = self._on_drop

        frame_layout = QVBoxLayout(self.input_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # 预览区
        self.preview_wrap = QWidget()
        self.preview_wrap.hide()
        self.preview_layout = QHBoxLayout(self.preview_wrap)
        self.preview_layout.setContentsMargins(12, 6, 12, 0)
        self.preview_layout.setSpacing(6)
        self.preview_layout.setAlignment(Qt.AlignLeft)
        frame_layout.addWidget(self.preview_wrap)

        # 文本输入框（支持拖拽图片 + 粘贴图片）
        self.text_edit = ImageTextEdit(self)
        self.text_edit.setPlaceholderText("输入文字，拖拽/粘贴图片，点击发送")
        self.text_edit.setMinimumHeight(56)
        self.text_edit.setMaximumHeight(110)
        self.text_edit.image_dropped.connect(self._on_image_pasted)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: none;
                padding: 10px 14px;
                font-size: 13px;
                color: {_TEXT_PRIMARY};
                background: transparent;
            }}
        """)
        frame_layout.addWidget(self.text_edit)

        # 底部按钮行 - 上传和发送靠右并排
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 0, 10, 8)
        btn_row.setSpacing(8)

        btn_row.addStretch()

        # 上传按钮
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
            PushButton:hover {{ color: {_PRIMARY}; border-color: {_PRIMARY}; }}
        """)
        upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(upload_btn)

        # 发送按钮
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
            PushButton:disabled {{ background-color: #a0c4ff; }}
        """)
        send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(send_btn)

        frame_layout.addLayout(btn_row)
        outer.addWidget(self.input_frame)

        return wrapper

    # ── 输入区状态 ──

    def _set_input_enabled(self, enabled: bool) -> None:
        """启用/禁用输入区"""
        self.text_edit.setEnabled(enabled)
        self.upload_btn.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.input_frame.setAcceptDrops(enabled)
        if enabled:
            self.text_edit.setPlaceholderText("输入文字，拖拽/粘贴图片，点击发送")
        else:
            self.text_edit.setPlaceholderText("请先点击「开启新保单收集」创建任务")

    # ── 消息操作 ──

    def _add_message(self, content: str, file_paths: list[str] | None = None) -> None:
        """添加一条消息到列表"""
        msg = ChatMessage(content=content, file_paths=file_paths)
        # 插入到 stretch 之前
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, msg)
        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_user_message(self, text: str, file_paths: list[str] | None = None) -> None:
        """添加消息"""
        self._add_message(text, file_paths=file_paths)

    def clear_messages(self) -> None:
        """清空所有消息"""
        while self.msg_layout.count() > 1:  # 保留 stretch
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── 事件处理 ──

    @staticmethod
    def _generate_task_id() -> str:
        """客户端生成任务编号"""
        return "TK-" + secrets.token_hex(4).upper()

    def _on_send(self) -> str | None:
        """发送按钮，返回新建任务的 task_id（如果有）"""
        text = self.text_edit.toPlainText().strip()
        if not text and not self._files:
            return None

        new_task_id = None
        # 客户端生成 task_id（避免发空 system 消息）
        if not self._current_task_id:
            self._current_task_id = self._generate_task_id()
            new_task_id = self._current_task_id

        # 上传文件
        file_paths = []
        if self._files:
            try:
                result = upload_files(self._current_task_id, self._files)
                file_paths = result.get("file_paths", [])
            except Exception as e:
                print(f"文件上传失败: {e}")

        # 添加用户消息到界面（带图片缩略图）
        if text or file_paths:
            self.add_user_message(text, file_paths=file_paths if file_paths else None)

        # 保存消息到后端
        if text or file_paths:
            try:
                result = create_chat_message(
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

        # 通知外部有新任务创建
        if new_task_id:
            self.task_created.emit(new_task_id)

        # 清空输入
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
        self._set_drag_style(False)

    def _on_image_pasted(self, path: str) -> None:
        """拖拽或粘贴的图片"""
        if path not in self._files:
            self._files.append(path)
            self._refresh_preview()

    def _on_upload(self) -> None:
        """上传文件"""
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
        self.input_frame.setStyleSheet(_DRAG_INPUT_STYLE if active else _NORMAL_INPUT_STYLE)

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
        """刷新预览区"""
        # 清除旧预览
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._files:
            self.preview_wrap.hide()
            return

        self.preview_wrap.show()
        for idx, filepath in enumerate(self._files[:8]):  # 最多显示8个
            self._add_preview_item(idx, filepath)

    def _add_preview_item(self, idx: int, filepath: str) -> None:
        """添加一个预览项（带删除按钮）"""
        from PySide6.QtGui import QPixmap

        ext = os.path.splitext(filepath)[1].lower()
        image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
        is_image = ext in image_exts

        # 容器
        item = QFrame()
        item.setFixedSize(60, 68)
        item.setStyleSheet("background-color: #f5f5f5; border: 1px solid #e8e8e8; border-radius: 6px;")

        # 点击打开文件
        item.setCursor(Qt.PointingHandCursor)
        item.mousePressEvent = lambda e, p=filepath: os.startfile(p) if e.button() == Qt.LeftButton else None

        # 内容区
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
            # 文件类型图标
            icon_map = {'.pdf': 'PDF', '.doc': 'DOC', '.docx': 'DOC',
                        '.xls': 'XLS', '.xlsx': 'XLS', '.txt': 'TXT', '.csv': 'CSV'}
            icon = icon_map.get(ext, '文件')
            content.setText(f"📄{icon}")
            content.setStyleSheet("font-size: 11px; color: #1677ff; font-weight: bold;")

            # 文件名（底部）
            name_label = QLabel(item)
            name_label.setGeometry(2, 52, 56, 14)
            name = os.path.basename(filepath)
            name_label.setText(name[:8] + ('…' if len(name) > 8 else ''))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("font-size: 9px; color: #999; border: none; background: transparent;")

        # 删除按钮（右上角 ×）
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
            PushButton:hover {
                background-color: #ff7875;
            }
        """)
        del_btn.clicked.connect(lambda checked=False, i=idx: self._on_remove_file(i))

        self.preview_layout.addWidget(item)

    def _on_remove_file(self, index: int) -> None:
        """删除预览区的文件"""
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self._refresh_preview()

    def _on_new_policy(self) -> None:
        """开启新任务 - 先弹出选择对话框"""
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
        """设置当前任务"""
        if task:
            self._current_task_id = task.get("task_id", "")
            insurance = task.get("insurance_company", "") or "-"
            customer = task.get("customer_company", "") or "-"
            self.policy_name_label.setText(f"{insurance} · {customer}")
            created = task.get("created_at", "-")
            if created:
                created = str(created)[:19].replace("T", " ")
            self.date_label.setText(f"创建日期：{created}")
            self.img_count_label.setText(f"消息数：{task.get('msg_count', 0)}")
            # 加载聊天记录
            self.clear_messages()
            self._load_chat_history(self._current_task_id)
            self._set_input_enabled(True)
        else:
            self._on_new_policy()

    def _load_chat_history(self, task_id: str) -> None:
        """加载聊天记录（带加载状态）"""
        # 显示加载提示
        self.clear_messages()
        loading_label = QLabel("加载消息中...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet(f"color: {_TEXT_SECONDARY}; font-size: 13px; padding: 20px;")
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, loading_label)
        # 让UI先刷新显示加载提示
        QTimer.singleShot(10, lambda: self._do_load_history(task_id, loading_label))

    def _do_load_history(self, task_id: str, loading_label: QLabel) -> None:
        """实际加载聊天记录"""
        try:
            messages = list_chat_messages(task_id)
            reordered: list[dict] = []
            i = 0
            while i < len(messages):
                curr = messages[i]
                nxt = messages[i + 1] if i + 1 < len(messages) else {}
                if (not curr.get("content") and curr.get("file_paths")
                        and nxt.get("content") and not nxt.get("file_paths")):
                    reordered.append(nxt)
                    reordered.append(curr)
                    i += 2
                else:
                    reordered.append(curr)
                    i += 1
            # 移除加载提示
            loading_label.deleteLater()
            # 添加消息
            for msg in reordered:
                content = msg.get("content", "") or ""
                file_paths = msg.get("file_paths") or None
                self.add_user_message(content, file_paths=file_paths)
        except Exception as e:
            loading_label.setText(f"加载失败: {e}")
            print(f"加载聊天记录失败: {e}")

    def clear(self) -> None:
        """清空输入"""
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
