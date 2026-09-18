# 客服保险工单系统 — 桌面客户端（Tauri + Vue3）

用 **Tauri 2 + Vue 3** 重写的客服端桌面应用，功能与 `client/`（PySide6 版）**完全一致**，
调用的后端接口、参数、认证方式全部保持一致，**后端无需任何改动**。

## 与 PySide6 版的功能对照

| 功能 | 说明 | 对应接口 |
| --- | --- | --- |
| 登录 | 手机号 + 密码，token 持久化 | `POST /api/users/login` |
| 保单列表（左侧栏） | 我的任务分页（每页10条）、本地搜索、状态徽标、15s 自动轮询 | `GET /api/chat/tasks/mine`、`GET /api/chat/tasks` |
| 聊天面板（右侧） | 用户/内勤消息气泡、内勤留言标签、右键复制文本 | `GET /api/chat/messages`、`GET /api/chat/tasks/{id}/comments` |
| 历史消息渲染 | 消息+留言合并按时间排序，文字前、图片后重排 | 同上 |
| 发送消息 | Enter 发送 / Ctrl+Enter 换行；未建任务时自动生成 `TK-XXXXXXXX` 任务号 | `POST /api/chat/messages` |
| 文件上传 | 拖拽 / 粘贴截图 / 文件选择，multipart 同步上传（单文件 ≤50MB，图片+文档） | `POST /api/chat/upload` |
| 新建保单收集 | 保险公司（可搜索下拉）、客户公司、新投/批改 | — |
| 图片查看器 | 点击缩略图放大查看 | 图片直链 |
| 修改密码 | 旧密码校验 + 两次一致校验 | `PUT /api/users/{id}/password` |
| 401 处理 | token 失效自动清除并跳回登录页 | — |

PySide6 版中未被界面调用的 `list_users`、`ai_recognize`、`add_task_comment` 等接口
在 `src/api/index.js` 中同样保留，以备后续扩展。

## 目录结构

```
desktop/
├── src/                    # Vue3 前端
│   ├── api/index.js        # API 层（与 client/api.py 一一对应）
│   ├── store.js            # 全局状态（当前用户 / Toast）
│   ├── constants.js        # 状态徽标、保险公司列表等常量
│   ├── App.vue             # 登录页 ⇆ 主界面切换
│   └── components/
│       ├── LoginPage.vue           # 登录页
│       ├── MainWindow.vue          # 主窗口（顶栏 + 左列表 + 右聊天）
│       ├── HistoryPanel.vue        # 左侧保单列表（分页/搜索/轮询）
│       ├── ChatPanel.vue           # 聊天面板（消息/输入/上传）
│       ├── ChatMessage.vue         # 消息气泡（文本/图片/文件/右键菜单）
│       ├── NewPolicyDialog.vue     # 新建保单收集对话框
│       ├── ChangePasswordDialog.vue# 修改密码对话框
│       └── ImageViewer.vue         # 图片查看器
├── src-tauri/              # Tauri 2 (Rust) 壳工程
└── package.json
```

## 环境要求

- [Node.js](https://nodejs.org/) ≥ 18
- [Rust](https://www.rust-lang.org/tools/install)（stable 工具链）
- Windows 构建需要 WebView2（Win10/11 一般已自带）

## 开发调试

```bash
cd desktop
npm install
npm run tauri dev
```

## 打包 exe

```bash
npm run tauri build
```

产物在 `src-tauri/target/release/bundle/nsis/` 下的安装包，
以及 `src-tauri/target/release/保险工单系统.exe` 单文件可执行程序。

## 图标说明

源图标为 `desktop/app-icon.png`（1024x1024，32 位 ARGB）。
如需更换图标：替换该文件后执行 `npx tauri icon app-icon.png` 重新生成 `src-tauri/icons/` 全套图标，再打包。
注意：索引色（Indexed）PNG 会导致打包报 `Unsupported PNG color type: Indexed`，源图必须是 32 位 ARGB 格式。

## 后端地址配置

与 PySide6 版一致，后端地址写在一个地方：

- `src/api/index.js` 顶部的 `BASE_URL`（默认 `http://192.168.1.9:8001`）

修改后重新构建即可。
