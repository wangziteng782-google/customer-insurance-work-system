"""修改密码对话框"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QMessageBox


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改密码")
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("旧密码"))
        self.old_edit = QLineEdit()
        self.old_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.old_edit)

        layout.addWidget(QLabel("新密码"))
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_edit)

        layout.addWidget(QLabel("确认新密码"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_edit)

        btn = QPushButton("确认修改")
        btn.clicked.connect(self._on_submit)
        layout.addWidget(btn)

    def _on_submit(self):
        if not self.old_pwd() or not self.new_pwd() or not self.confirm_pwd():
            QMessageBox.warning(self, "提示", "请填写所有字段")
            return
        if self.new_pwd() != self.confirm_pwd():
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        self.accept()

    def old_pwd(self): return self.old_edit.text().strip()
    def new_pwd(self): return self.new_edit.text().strip()
    def confirm_pwd(self): return self.confirm_edit.text().strip()
