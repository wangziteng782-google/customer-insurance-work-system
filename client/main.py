import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from client.resources import resource_path
from client.ui.main_window import MainWindow
from client.ui.login_page import LoginPage


def _setup_font(app: QApplication) -> None:
    """设置全局字体：优先苹果风格字体"""
    preferred_fonts = ["SF Pro Display", "SF Pro Text", "PingFang SC", "Microsoft YaHei", "Segoe UI"]
    available = QFontDatabase.families()

    font_family = "Microsoft YaHei"
    for name in preferred_fonts:
        if name in available:
            font_family = name
            break

    font = QFont(font_family)
    font.setPointSize(13)
    font.setWeight(QFont.Normal)
    app.setFont(font)


def _set_app_id() -> None:
    """设置 Windows AppUserModelID，确保任务栏图标正常显示"""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CustomerInsurance.WorkSystem.1.0"
        )


class App(QMainWindow):
    """主应用窗口 — QStackedWidget 切换登录页和主界面"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("保险工单系统")
        self.resize(1000, 620)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.main_window = MainWindow()

        self.stack.addWidget(self.login_page)   # index 0
        self.stack.addWidget(self.main_window)  # index 1

        self.stack.setCurrentIndex(0)

        self.login_page.login_success.connect(self._on_login_success)

    def _on_login_success(self, user):
        self.main_window.set_current_user(user)
        self.stack.setCurrentIndex(1)


def main():
    _set_app_id()

    app = QApplication(sys.argv)

    _setup_font(app)

    from qfluentwidgets import setTheme, Theme
    setTheme(Theme.AUTO)

    icon_path = resource_path("logo.ico")
    if not os.path.exists(icon_path):
        icon_path = resource_path("favicon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    try:
        from pyside6_mcp import install_bridge
        install_bridge()
        print("pyside6-mcp bridge 已启动，默认端口 7890")
    except ImportError:
        print("pyside6-mcp 未安装，跳过 bridge（不影响正常使用）")

    window = App()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
