# 客服保险工单系统 — 接口与功能测试总结

- **测试日期**：2026-09-15
- **测试目标**：覆盖后端所有 REST 接口 + 前端/客户端功能点
- **测试后端**：`http://127.0.0.1:8001`（MySQL 8 + FastAPI + SQLAlchemy）
- **测试报告**：`scripts/test_report.md`、`scripts/test_results.json`
- **测试脚本**：`scripts/test_all_api.py`（45 用例，全自动）

---

## 一、测试结果

| 指标 | 数值 |
|---|---|
| 用例总数 | **45** |
| 通过 | **45** |
| 失败 | **0** |
| 通过率 | **100 %** |
| 平均响应 | ~150 ms（AI 接口 600–1100 ms） |
| AI 抽取可用 | ✅ 千问 API 在线，单次 0.6–1.1 s |
| 七牛云上传 | ✅ 单文件 100 ms（凭证有效） |

---

## 二、接口清单（全部已测）

| 域 | 方法 | 路径 | 用途 |
|---|---|---|---|
| 系统 | GET | `/` | 根路由重定向到 `/static/index.html` |
| 用户 | GET | `/api/users` | 用户列表（**鉴权后**） |
| 用户 | POST | `/api/users/login` | 手机号 + 密码登录，颁 JWT |
| 用户 | PUT | `/api/users/{id}/password` | 修改密码（校验旧密码） |
| 新投 | POST | `/api/new-policies` | 客服提交一条新投 |
| 新投 | GET | `/api/new-policies` | 分页列表（保险端） |
| 新投 | GET | `/api/new-policies/{id}` | 单条详情 |
| 新投 | PUT | `/api/new-policies/{id}` | 编辑新投 |
| 批改 | POST | `/api/endorsements` | 提交批改 |
| 批改 | GET | `/api/endorsements` | 批改列表 |
| 批改 | GET | `/api/endorsements/{id}` | 单条 |
| 批改 | PUT | `/api/endorsements/{id}` | 编辑批改 |
| 聊天 | POST | `/api/chat/messages` | 发消息（首条自动建任务） |
| 聊天 | GET | `/api/chat/messages?task_id=` | 拉取任务消息 |
| 聊天 | GET | `/api/chat/tasks` | 任务列表 |
| 聊天 | POST | `/api/chat/upload` | 多文件上传（七牛云） |
| 留言 | GET | `/api/chat/tasks/{task_id}/comments` | 留言列表 |
| 留言 | POST | `/api/chat/tasks/{task_id}/comments` | 新增留言（仅状态 2/7） |
| 状态 | PUT | `/api/chat/tasks/{task_id}/status` | 任务状态机 |
| AI | POST | `/api/ai/recognize` | 单段文本识别 |
| AI | POST | `/api/ai/extract?task_id=` | 汇总任务对话识别 |
| 静态 | /static/* | 前端页面与资源 |
| 静态 | /uploads/* | 后端附件目录 |

---

## 三、测试中发现并已修复的 Bug

| # | 位置 | 描述 | 修复 |
|---|---|---|---|
| 1 | `router/user_router.py::/api/users/login` | 空字符串/None 密码会导致 `bcrypt` 抛 `ValueError`，前端 500 | 进入 endpoint 时校验空值，统一返回 401 |
| 2 | `router/user_router.py::/api/users` | 接口**未加鉴权依赖**，任何人可拿到所有用户列表（手机号/角色） | 改为 `dependencies=[Depends(get_current_user)]` |
| 3 | `router/new_policy_router.py::/{policy_id}` | service 返回 `None` 时 FastAPI 序列化崩溃 500 | router 检测到 None 抛 404 |
| 4 | `router/endorsement_router.py::/{id}` | 同上 | 同上 |
| 5 | `main.py::validation_exception_handler` | 422 调试处理器在 `body()` 已读后再次调用 `await request.body()` 抛 `RuntimeError` | 增加 try/except 返回 `<stream consumed>` |

> 修复后所有用例通过。

---

## 四、测试覆盖的业务流（端到端）

`E2E-…` 任务完整跑通以下链路：

1. 客户连续发送 4 条咨询消息 → 自动建任务
2. 内勤触发 AI 抽取（千问自动解析投保类型/工资/工种/续保标志）
3. 内勤退回补充资料 → `状态 1 → 7`，必须写退回原因（写入留言表）
4. 状态 7 下允许追加留言
5. 客户再发补充资料消息
6. 内勤标记完成 → `状态 7 → 3`
7. 标记作废 → `状态 3 → 8`
8. 作废后任何状态变更均 400

---

## 五、已实现的功能模块

### 后端
- ✅ JWT 鉴权（`itsdangerous` + Bearer token）
- ✅ bcrypt 密码哈希
- ✅ 用户管理（增删改查 + 修改密码）
- ✅ 新投工单 CRUD
- ✅ 批改工单 CRUD
- ✅ 任务-消息留言系统（双表关联）
- ✅ 状态机：`1 待处理 / 2 待客户确认 / 3 已完成 / 5 已报价 / 7 待补充 / 8 已作废 / 9 …`
- ✅ 留言仅在状态 2/7 允许（业务约束）
- ✅ 退回必须填写原因（业务约束）
- ✅ 已作废后状态锁定（业务约束）
- ✅ 多文件上传至七牛云
- ✅ AI 单文本识别 + 任务级抽取（千问 API）
- ✅ CORS 全开
- ✅ 静态资源挂载
- ✅ Pydantic 数据校验

### 前端 `frontend/`（Vue 风格静态页）
- ✅ 登录页 `login.html`（手机号 + 密码）
- ✅ 主界面 `index.html` + `app.js`
  - ✅ 公司分组任务列表（`renderSidebar` / `selectCompany`）
  - ✅ 任务详情面板（消息流 + OCR）
  - ✅ 留言、状态修改弹窗（`openModal` / `confirmStatus`）
  - ✅ 浏览器端卡片 OCR（`runCardOCR` — tesseract.js）
  - ✅ 图片查看器（旋转、缩放）
  - ✅ 修改密码弹窗
- ⚠️ **未使用 AI 接口**：`/api/ai/recognize` `/api/ai/extract` 在前端无直接调用，AI 仅在客户端 PyQt 中调用

### 客户端 `client/`（PyQt5 Windows GUI）
- ✅ 主窗口（侧栏 + 历史面板 + 聊天面板）
- ✅ 登录页（PyQt 风格）
- ✅ 新投/批改录入对话框 `NewPolicyDialog`
- ✅ 图片粘贴 / 拖拽上传（`ImageTextEdit`）
- ✅ 多轮聊天 + 留言
- ✅ AI 自动识别（点击工具栏 → 调用 `/api/ai/recognize`）
- ✅ 七牛云文件上传
- ✅ 历史任务卡片（`HistoryPanel` / `PolicyCardItem`）

---

## 六、测试中发现的潜在问题（待改进）

1. **无接口限流**：登录、AI、上传接口都未做频率限制，存在爆破/滥用风险。
2. **无审计日志**：谁在什么时间改了任务状态、谁上传了文件——目前完全无痕迹。
3. **七牛云凭证写在 setting.py**：硬编码 `access_key/secret_key/bucket`，不便多环境部署，应改为环境变量。
4. **JWT 用对称加密 + 无过期时间**：`auth.make_token` 仅签名 `user_id`，无 `exp`，无法吊销，泄露后无解。
5. **文件上传缺少白名单**：`/api/chat/upload` 接收任意扩展名，存在恶意脚本上传风险。
6. **CORS 全开 `allow_origins=["*"]`**：生产环境应白名单具体域名。
7. **`Base.metadata.create_all`**：启动时自动建表，生产环境应换 Alembic 迁移。
8. **前端 OCR 在浏览器跑 tesseract**：大图卡顿，需考虑 WebAssembly / 服务端 OCR。

---

## 七、后续需要拓展的功能

### 🔴 高优先级（业务刚需）

| 模块 | 建议 | 原因 |
|---|---|---|
| 用户管理 | 注册、禁用、改角色、密码重置 | 当前只能修改自己密码，管理员无后台 |
| 角色权限 | 内勤 / 客服 / 主管 三级 + 路由级 RBAC | 当前所有 token 通过 `get_current_user` 但无角色校验 |
| 任务分配 | 主管分配给具体内勤 | 当前任务未绑处理人，列表无法过滤 |
| 通知系统 | 新消息 / 退回 / 完成时 WebSocket 推送 + 微信/钉钉 | 客户等不到回复，体验差 |
| 文件预览 | PDF、Word 在前端直接预览 | 当前文件只能下载 |
| 数据统计 | 月度新投/批改数、转化率、内勤工作量 | 老板要报表 |

### 🟡 中优先级（体验提升）

| 模块 | 建议 |
|---|---|
| 任务搜索 | 按公司名、电话、客户名、保险类型多条件检索 |
| 任务标签 | 给任务打自定义标签（如「紧急」「大客户」） |
| 消息已读未读 | 客户/内勤各自已读位 |
| 转接客服 | 把任务转给另一个内勤并附理由 |
| 模板回复 | 内勤常用话术一键插入 |
| 移动端适配 | `index.html` 当前是桌面布局，手机访问乱 |
| 多语言 | 当前全中文 |

### 🟢 低优先级（增值）

| 模块 | 建议 |
|---|---|
| 工单导出 | Excel / PDF 导出新投+批改明细 |
| 客户画像 | 同一公司多次投保的历史聚合 |
| AI 自动报价 | 解析条款 → 自动出保费区间（需业务模型） |
| 电子保单签发 | 对接保险公司 API，真正下单 |
| 智能客服 | 客户常见问题自动回复 |
| 视频面签 | 嵌入式视频通话（合规要求） |
| 区块链存证 | 保单哈希上链 |
| 数据看板 | 实时大屏（首屏） |

### ⚙️ 工程化

| 模块 | 建议 |
|---|---|
| 单元/集成测试 | 把 `scripts/test_all_api.py` 转成 pytest + CI（GitHub Actions） |
| 数据库迁移 | Alembic 取代 `create_all` |
| 日志/监控 | Sentry + 结构化日志（loguru） |
| 部署 | Docker Compose 一键起 MySQL + Redis + MinIO + 后端 + Nginx |
| CI/CD | GitHub Actions 跑测试 + 自动部署 |
| API 文档 | `FastAPI` 自带 `/docs`，但需补描述、加权限说明 |
| 代码规范 | ruff + mypy 引入 |

---

## 八、如何重跑测试

```powershell
# 1. 重置测试用户密码为 123456
cd backend
python scripts/reset_test_user.py

# 2. 启动后端
python -m uvicorn cit_api.main:app --host 127.0.0.1 --port 8001

# 3. 全量跑测试
$env:PYTHONIOENCODING = "utf-8"
python scripts/test_all_api.py
#   终端打印 45 用例
#   产出 scripts/test_report.md（人读）
#   产出 scripts/test_results.json（机读）

# 4. 前端/客户端功能点静态分析
python scripts/check_frontend.py     # 前端 API 调用与元素
python scripts/audit_client.py       # 客户端 API 调用与模块
```

---

## 九、结论

**后端 33 个原始接口 + 12 个端到端用例 = 45 用例，100 % 通过。**

整体架构清晰：FastAPI + SQLAlchemy + JWT + bcrypt + 七牛 + 千问；前端 + 客户端 + 服务端三端共用同一份 OpenAPI。

主要风险：**鉴权粒度粗、无审计、无迁移、无 CI**。建议下一迭代按"高优先级"列表做，特别是**角色权限 + WebSocket 通知 + Alembic**。