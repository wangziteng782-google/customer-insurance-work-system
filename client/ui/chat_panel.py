"""聊天面板 - 顶部状态栏 + 消息列表 + 输入区（含快捷标签）"""
import os
import tempfile
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QWidget, QScrollArea, QFileDialog, QFrame, QSizePolicy,
    QApplication
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QTextCursor, QKeySequence
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
_TAG_SELECTED_BG = "#e8f4ff"
_TAG_SELECTED_TEXT = "#1677ff"
_TAG_SELECTED_BORDER = "#1677ff"
_TAG_BG = "#f5f5f5"
_TAG_TEXT = "#555555"
_TAG_BORDER = "#e0e0e0"


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

    # 快捷标签（保险公司）
    QUICK_TAGS = [
        "人保财险", "平安保险", "太平洋保险", "国寿财险",
        "阳光保险", "新华保险", "泰康保险", "太平保险",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._current_task_id: str = ""
        self._tag_buttons: list[PushButton] = []
        self._selected_tag: str | None = None
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

        # 当前保单名称
        self.policy_name_label = QLabel("当前保单：未选择")
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

        # 快捷标签栏
        quick_bar = QWidget()
        quick_bar.setStyleSheet("border-top: 1px solid #f0f0f0;")
        quick_layout = QHBoxLayout(quick_bar)
        quick_layout.setContentsMargins(12, 5, 12, 5)
        quick_layout.setSpacing(6)
        quick_layout.setAlignment(Qt.AlignLeft)

        for tag in self.QUICK_TAGS:
            tag_btn = PushButton(tag, self)
            tag_btn.setFixedHeight(26)
            tag_btn.setMinimumWidth(66)
            tag_btn.setStyleSheet(self._tag_style(selected=False))
            tag_btn.clicked.connect(lambda checked=False, t=tag: self._on_quick_tag(t))
            self._tag_buttons.append(tag_btn)
            quick_layout.addWidget(tag_btn)

        quick_layout.addStretch()
        frame_layout.addWidget(quick_bar)

        # 底部按钮行 - 上传和发送靠右并排
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 0, 10, 8)
        btn_row.setSpacing(8)

        btn_row.addStretch()

        # 上传按钮
        upload_btn = PushButton("上传图片", self)
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
        send_btn = PushButton("发送", self)
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

    # ── 消息操作 ──

    def _add_message(self, content: str, msg_type: str = "user",
                     file_paths: list[str] | None = None) -> None:
        """添加一条消息到列表"""
        msg = ChatMessage(content=content, msg_type=msg_type, file_paths=file_paths)
        # 插入到 stretch 之前
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, msg)
        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_user_message(self, text: str, file_paths: list[str] | None = None) -> None:
        """添加用户消息"""
        self._add_message(text, "user", file_paths=file_paths)

    def add_system_message(self, text: str, file_paths: list[str] | None = None) -> None:
        """添加系统消息"""
        self._add_message(text, "system", file_paths=file_paths)

    def clear_messages(self) -> None:
        """清空所有消息"""
        while self.msg_layout.count() > 1:  # 保留 stretch
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── 事件处理 ──

    @staticmethod
    def _tag_style(selected: bool) -> str:
        """快捷标签样式 - 选中/未选中"""
        if selected:
            return f"""
                PushButton {{
                    background-color: {_TAG_SELECTED_BG};
                    color: {_TAG_SELECTED_TEXT};
                    border: 1px solid {_TAG_SELECTED_BORDER};
                    border-radius: 13px;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 12px;
                }}
                PushButton:hover {{
                    background-color: #d6eaff;
                    color: {_TAG_SELECTED_TEXT};
                }}
            """
        else:
            return f"""
                PushButton {{
                    background-color: {_TAG_BG};
                    color: {_TAG_TEXT};
                    border: 1px solid {_TAG_BORDER};
                    border-radius: 13px;
                    font-size: 12px;
                    padding: 0 12px;
                }}
                PushButton:hover {{
                    background-color: {_PRIMARY_LIGHT};
                    color: {_PRIMARY};
                    border-color: {_PRIMARY};
                }}
            """

    def _on_quick_tag(self, tag: str) -> None:
        """点击快捷标签 - 单选切换，文本框内容替换"""
        # 如果点击的是已选中的标签，则取消选中
        if self._selected_tag == tag:
            self._selected_tag = None
            self._update_tag_styles()
            return

        # 选中新标签
        self._selected_tag = tag
        self._update_tag_styles()

        # 替换输入框内容为当前选中标签，光标移到末尾
        self.text_edit.setPlainText(tag)
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)

    def _update_tag_styles(self) -> None:
        """更新所有标签的样式"""
        for btn in self._tag_buttons:
            btn.setStyleSheet(self._tag_style(selected=(btn.text() == self._selected_tag)))

    def _on_send(self) -> str | None:
        """发送按钮，返回新建任务的 task_id（如果有）"""
        text = self.text_edit.toPlainText().strip()
        if not text and not self._files:
            return None

        new_task_id = None

        # 上传文件（需要先有 task_id，如果没有先创建一个空任务）
        file_paths = []
        if self._files:
            # 如果有文件但还没有 task_id，先创建一个任务
            if not self._current_task_id:
                try:
                    result = create_chat_message(
                        task_id="",
                        content="",
                        msg_type="system",
                        file_paths=None,
                        user_id=2,
                    )
                    if result:
                        self._current_task_id = result.get("task_id", "")
                        new_task_id = self._current_task_id
                except Exception as e:
                    print(f"创建任务失败: {e}")
                    return None

            try:
                result = upload_files(self._current_task_id, self._files)
                file_paths = result.get("file_paths", [])
            except Exception as e:
                print(f"文件上传失败: {e}")

        # 添加用户消息到界面（带图片缩略图）
        if text or file_paths:
            self.add_user_message(text, file_paths=file_paths if file_paths else None)

        # 保存消息到后端（文字或文件）
        if text or file_paths:
            try:
                result = create_chat_message(
                    task_id=self._current_task_id or "",
                    content=text,
                    msg_type="user",
                    file_paths=file_paths if file_paths else None,
                    user_id=2,
                    insurance_company=self._selected_tag,
                )
                if not self._current_task_id and result:
                    self._current_task_id = result.get("task_id", "")
                    new_task_id = self._current_task_id
            except Exception as e:
                print(f"保存消息失败: {e}")

        # 通知外部有新任务创建
        if new_task_id:
            self.task_created.emit(new_task_id)

        # 清空输入
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()

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

    def _on_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.input_frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {_PRIMARY};
                    border-radius: 10px;
                    background-color: {_PRIMARY_LIGHT};
                }}
            """)

    def _on_drop(self, event: QDropEvent) -> None:
        self.input_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {_BORDER};
                border-radius: 10px;
                background-color: #ffffff;
            }}
        """)
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

        # 容器
        item = QFrame()
        item.setFixedSize(60, 60)
        item.setStyleSheet("background-color: #f5f5f5; border: none; border-radius: 6px;")

        # 图片/文件名
        content = QLabel(item)
        content.setGeometry(4, 4, 52, 52)
        content.setAlignment(Qt.AlignCenter)
        content.setStyleSheet("border: none; background: transparent;")

        ext = os.path.splitext(filepath)[1].lower()
        image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

        if ext in image_exts:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(52, 52, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                content.setPixmap(scaled)
            else:
                content.setText("图")
                content.setStyleSheet("font-size: 10px; color: #999;")
        else:
            name = os.path.basename(filepath)
            content.setText(name[:6])
            content.setStyleSheet("font-size: 10px; color: #666;")

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
        """开启新任务"""
        self._current_task_id = ""
        self.policy_name_label.setText("当前任务：新建会话")
        self.date_label.setText(f"创建日期：{datetime.now().strftime('%Y-%m-%d')}")
        self.img_count_label.setText("已收集图片：0 张")
        self.clear_messages()
        self.add_system_message("已开启新会话，发送第一条消息后任务自动创建。")

    def set_current_task(self, task: dict | None) -> None:
        """设置当前任务"""
        if task:
            self._current_task_id = task.get("task_id", "")
            self.policy_name_label.setText(f"当前任务：{self._current_task_id}")
            created = task.get("created_at", "-")
            if created:
                created = str(created)[:19].replace("T", " ")
            self.date_label.setText(f"创建日期：{created}")
            self.img_count_label.setText(f"消息数：{task.get('msg_count', 0)}")
            # 加载聊天记录
            self.clear_messages()
            self._load_chat_history(self._current_task_id)
        else:
            self._on_new_policy()

    def _load_chat_history(self, task_id: str) -> None:
        """加载聊天记录"""
        try:
            messages = list_chat_messages(task_id)
            for msg in messages:
                content = msg.get("content", "")
                msg_type = msg.get("msg_type", "user")
                file_paths = msg.get("file_paths")
                if msg_type == "user":
                    self.add_user_message(content, file_paths=file_paths)
                else:
                    self.add_system_message(content, file_paths=file_paths)
        except Exception as e:
            print(f"加载聊天记录失败: {e}")

    def clear(self) -> None:
        """清空输入"""
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
