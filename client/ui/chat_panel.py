"""聊天面板 - 顶部状态栏 + 消息列表 + 输入区（含快捷标签）"""
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QWidget, QScrollArea, QFileDialog, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from qfluentwidgets import PushButton, ScrollArea

from client.api import create_chat_message, list_chat_messages, upload_files
from client.ui.widgets.chat_message import ChatMessage
from client.ui.dialog import warning_dialog, error_dialog


class ChatPanel(QWidget):
    """聊天面板 - 对话式保单资料收集"""

    # 快捷标签
    QUICK_TAGS = [
        "人保财险", "平安保险", "太平洋保险", "国寿财险", "阳光保险",
        "电梯责任险", "公众责任险", "雇主责任险",
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
        self.scroll_area.setStyleSheet("background-color: #ffffff; border: none;")

        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background-color: #ffffff;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(16, 16, 16, 16)
        self.msg_layout.setSpacing(14)
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
        bar.setFixedHeight(48)
        bar.setStyleSheet("background-color: #f0f7ff; border-bottom: 1px solid #e5e7eb;")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # 当前保单名称
        self.policy_name_label = QLabel("当前保单：未选择")
        self.policy_name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1d2129;")
        layout.addWidget(self.policy_name_label)

        layout.addSpacing(16)

        # 创建日期
        self.date_label = QLabel("创建日期：-")
        self.date_label.setStyleSheet("font-size: 13px; color: #606266;")
        layout.addWidget(self.date_label)

        layout.addSpacing(16)

        # 图片计数
        self.img_count_label = QLabel("已收集图片：0 张")
        self.img_count_label.setStyleSheet("font-size: 13px; color: #606266;")
        layout.addWidget(self.img_count_label)

        layout.addStretch()

        # 开启新保单按钮
        new_btn = PushButton("开启新保单收集", self)
        new_btn.setFixedSize(140, 32)
        new_btn.setStyleSheet("""
            PushButton {
                background-color: #1677ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #4096ff; }
            PushButton:pressed { background-color: #0958d9; }
        """)
        new_btn.clicked.connect(self._on_new_policy)
        layout.addWidget(new_btn)

        return bar

    def _create_input_area(self) -> QWidget:
        """创建输入区域（含预览、文本框、快捷标签、按钮）"""
        wrapper = QWidget()
        wrapper.setStyleSheet("background-color: #ffffff; border-top: 1px solid #e5e7eb;")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(16, 8, 16, 12)
        outer.setSpacing(6)

        # 输入框容器（带拖拽）
        self.input_frame = QFrame()
        self.input_frame.setAcceptDrops(True)
        self.input_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                background-color: #ffffff;
            }
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

        # 文本输入框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("输入文字，拖拽/选择多张图片，点击发送统一上传")
        self.text_edit.setMinimumHeight(60)
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 10px 14px;
                font-size: 14px;
                color: #1d2129;
                background: transparent;
            }
        """)
        frame_layout.addWidget(self.text_edit)

        # 快捷标签栏
        quick_bar = QWidget()
        quick_bar.setStyleSheet("border-top: 1px solid #f0f0f0;")
        quick_layout = QHBoxLayout(quick_bar)
        quick_layout.setContentsMargins(12, 6, 12, 6)
        quick_layout.setSpacing(8)
        quick_layout.setAlignment(Qt.AlignLeft)

        for tag in self.QUICK_TAGS:
            tag_btn = PushButton(tag, self)
            tag_btn.setFixedHeight(28)
            tag_btn.setMinimumWidth(70)
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
        upload_btn.setFixedSize(72, 30)
        upload_btn.setStyleSheet("""
            PushButton {
                background-color: transparent;
                color: #606266;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                font-size: 13px;
            }
            PushButton:hover { color: #1677ff; border-color: #1677ff; }
        """)
        upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(upload_btn)

        # 发送按钮
        send_btn = PushButton("发送", self)
        send_btn.setFixedSize(60, 30)
        send_btn.setStyleSheet("""
            PushButton {
                background-color: #1677ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            PushButton:hover { background-color: #4096ff; }
            PushButton:pressed { background-color: #0958d9; }
            PushButton:disabled { background-color: #a0c4ff; }
        """)
        send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(send_btn)

        frame_layout.addLayout(btn_row)
        outer.addWidget(self.input_frame)

        return wrapper

    # ── 消息操作 ──

    def _add_message(self, content: str, msg_type: str = "user") -> None:
        """添加一条消息到列表"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = ChatMessage(content=content, msg_type=msg_type, timestamp=timestamp)
        # 插入到 stretch 之前
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, msg)
        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_user_message(self, text: str) -> None:
        """添加用户消息"""
        self._add_message(text, "user")

    def add_system_message(self, text: str) -> None:
        """添加系统消息"""
        self._add_message(text, "system")

    def add_ai_message(self, text: str) -> None:
        """添加 AI 消息"""
        self._add_message(text, "bot")

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
            return """
                PushButton {
                    background-color: #e8f4ff;
                    color: #1677ff;
                    border: 1px solid #1677ff;
                    border-radius: 14px;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 0 12px;
                }
                PushButton:hover {
                    background-color: #d6eaff;
                    color: #1677ff;
                }
            """
        else:
            return """
                PushButton {
                    background-color: #f5f5f5;
                    color: #555;
                    border: 1px solid #e0e0e0;
                    border-radius: 14px;
                    font-size: 13px;
                    padding: 0 12px;
                }
                PushButton:hover {
                    background-color: #e8f4ff;
                    color: #1677ff;
                    border-color: #91caff;
                }
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
        from PySide6.QtGui import QTextCursor
        self.text_edit.setPlainText(tag)
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)

    def _update_tag_styles(self) -> None:
        """更新所有标签的样式"""
        for btn in self._tag_buttons:
            btn.setStyleSheet(self._tag_style(selected=(btn.text() == self._selected_tag)))

    def _on_send(self) -> None:
        """发送按钮"""
        text = self.text_edit.toPlainText().strip()
        if not text and not self._files:
            return

        # 添加用户消息到界面
        if text:
            self.add_user_message(text)

        # 上传文件
        file_paths = []
        if self._files and self._current_task_id:
            try:
                result = upload_files(self._current_task_id, self._files)
                file_paths = result.get("file_paths", [])
            except Exception as e:
                print(f"文件上传失败: {e}")

        # 保存消息到后端
        if text or file_paths:
            try:
                create_chat_message(
                    task_id=self._current_task_id or "",
                    content=text,
                    msg_type="user",
                    file_paths=file_paths if file_paths else None,
                )
                # 如果是第一条消息，task_id 可能刚生成，更新当前 task_id
                if not self._current_task_id:
                    # 重新拉取任务列表获取新 task_id
                    pass
            except Exception as e:
                print(f"保存消息失败: {e}")

        # 系统提示
        if file_paths:
            self.add_system_message(f"已上传 {len(file_paths)} 个文件")

        # 清空输入
        self.text_edit.clear()
        self._files.clear()
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
            self.input_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #1677ff;
                    border-radius: 12px;
                    background-color: #f0f7ff;
                }
            """)

    def _on_drop(self, event: QDropEvent) -> None:
        self.input_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #d9d9d9;
                border-radius: 12px;
                background-color: #ffffff;
            }
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
        """添加一个预览项"""
        from PySide6.QtGui import QPixmap

        item = QWidget()
        item.setFixedSize(56, 56)
        item.setStyleSheet("background-color: #f5f5f5; border-radius: 6px;")

        layout = QVBoxLayout(item)
        layout.setContentsMargins(2, 2, 2, 2)

        ext = os.path.splitext(filepath)[1].lower()
        image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

        if ext in image_exts:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(52, 52, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(scaled)
                img_label.setAlignment(Qt.AlignCenter)
                img_label.setStyleSheet("border: none;")
                layout.addWidget(img_label)
        else:
            name = os.path.basename(filepath)
            name_label = QLabel(name[:6])
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("font-size: 10px; color: #666; border: none;")
            layout.addWidget(name_label)

        self.preview_layout.addWidget(item)

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
            if created and len(str(created)) >= 10:
                created = str(created)[:10]
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
                if msg_type == "user":
                    self.add_user_message(content)
                else:
                    self.add_system_message(content)
        except Exception as e:
            print(f"加载聊天记录失败: {e}")

    def clear(self) -> None:
        """清空输入"""
        self.text_edit.clear()
        self._files.clear()
        self._refresh_preview()
