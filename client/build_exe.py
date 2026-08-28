"""
Nuitka 打包客服端为 .exe
用法：在项目根目录执行 python client/build_exe.py
产物：client/dist/客服工单录入.exe
"""
import os
import shutil
import subprocess
import sys

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(ROOT_DIR, "client")

DIST_DIR = os.path.join(CLIENT_DIR, "dist")
BUILD_DIR = os.path.join(CLIENT_DIR, "build")

# 清理旧构建
for path in [DIST_DIR, BUILD_DIR]:
    if os.path.exists(path):
        shutil.rmtree(path)

# Nuitka 打包命令
logo_path = os.path.join(CLIENT_DIR, "resources", "logo.ico")
resources_dir = os.path.join(CLIENT_DIR, "resources")

cmd = [
    sys.executable, "-m", "nuitka",
    "--standalone",                          # 独立运行，无需 Python 环境
    "--onefile",                             # 单文件 .exe
    f"--windows-icon-from-ico={logo_path}",  # 程序图标
    "--enable-plugin=pyside6",               # PySide6 支持
    f"--include-data-dir={resources_dir}=resources",
    f"--output-dir={DIST_DIR}",
    "--output-filename=客服工单录入",
    "--windows-disable-console",             # 禁用控制台窗口
    "--assume-yes-for-downloads",            # 自动下载依赖
    # 隐藏导入
    "--include-module=client.api",
    "--include-module=client.ui.main_window",
    "--include-module=client.ui.history_panel",
    "--include-module=client.ui.chat_panel",
    "--include-module=client.ui.dialog",
    "--include-module=client.ui.widgets.chat_message",
    "--include-module=client.resources",
    os.path.join(CLIENT_DIR, "main.py"),
]

print("开始打包（首次可能需要 5-15 分钟）...")
subprocess.check_call(cmd)
print(f"打包完成，产物在 {DIST_DIR}/客服工单录入.exe")
