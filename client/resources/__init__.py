"""资源路径工具 - 兼容本地运行和 PyInstaller 打包"""
import os
import sys


def resource_path(rel: str) -> str:
    """获取资源文件路径

    用法：resource_path("favicon.ico") 或 resource_path("logo.png")
    自动兼容本地运行和 PyInstaller 打包环境
    """
    # PyInstaller 打包后资源在 _MEIPASS 根目录
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)

    # 本地运行：从 client/resources/ 出发
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)
