import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from client.resources import resource_path
from client.ui.main_window import MainWindow


def _setup_font(app: QApplication) -> None:
    """设置全局字体：优先苹果风格字体"""
    # 字体优先级：SF Pro → PingFang SC → Microsoft YaHei
    preferred_fonts = ["SF Pro Display", "SF Pro Text", "PingFang SC", "Microsoft YaHei", "Segoe UI"]
    available = QFontDatabase.families()

    font_family = "Microsoft YaHei"  # 默认回退
    for name in preferred_fonts:
        if name in available:
            font_family = name
            break

    font = QFont(font_family)
    font.setPointSize(13)  # 基础字号 13pt
    font.setWeight(QFont.Normal)
    app.setFont(font)


def _set_app_id() -> None:
    """设置 Windows AppUserModelID，确保任务栏图标正常显示"""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CustomerInsurance.WorkSystem.1.0"
        )


def main():
    # 必须在 QApplication 之前设置 AppID
    _set_app_id()

    app = QApplication(sys.argv)

    # 设置全局字体
    _setup_font(app)

    # Fluent 主题（自动跟随系统暗色/亮色）
    from qfluentwidgets import setTheme, Theme
    setTheme(Theme.AUTO)

    # 设置窗口/任务栏图标（优先 logo.ico，回退 favicon.ico）
    icon_path = resource_path("logo.ico")
    if not os.path.exists(icon_path):
        icon_path = resource_path("favicon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 嵌入 pyside6-mcp bridge，让 AI 能连接并操控本应用
    try:
        from pyside6_mcp import install_bridge
        install_bridge()
        print("pyside6-mcp bridge 已启动，默认端口 7890")
    except ImportError:
        print("pyside6-mcp 未安装，跳过 bridge（不影响正常使用）")

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
