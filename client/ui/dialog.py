"""现代化弹窗组件 - 基于 qfluentwidgets MessageBox"""
from PySide6.QtWidgets import QWidget
from qfluentwidgets import MessageBox


def info_dialog(parent: QWidget, title: str, content: str) -> None:
    """信息提示弹窗"""
    w = MessageBox(title, content, parent)
    w.yesButton.setText("确定")
    w.cancelButton.hide()
    w.exec()


def warning_dialog(parent: QWidget, title: str, content: str) -> None:
    """警告弹窗"""
    w = MessageBox(f"⚠ {title}", content, parent)
    w.yesButton.setText("确定")
    w.cancelButton.hide()
    w.exec()


def error_dialog(parent: QWidget, title: str, content: str) -> None:
    """错误弹窗"""
    w = MessageBox(f"✕ {title}", content, parent)
    w.yesButton.setText("确定")
    w.cancelButton.hide()
    w.exec()


def confirm_dialog(parent: QWidget, title: str, content: str) -> bool:
    """确认弹窗"""
    w = MessageBox(title, content, parent)
    w.yesButton.setText("确定")
    w.cancelButton.setText("取消")
    return w.exec()
