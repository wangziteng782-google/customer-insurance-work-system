# 接口测试报告

- **基址**: `http://127.0.0.1:8001`
- **时间**: 2026-09-15 11:47:22
- **总数**: 45  **成功**: 45  **失败**: 0  **通过率**: 100.0%

## 测试结果明细

### system (1/1)

| # | 用例 | 方法 | 路径 | 期望 | 实际 | 用时 | 通过 | 说明 |
|---|---|---|---|---|---|---|---|---|
| 1 | 根路由重定向 | GET | `/` | 200,307,308 | 200 | 262.0ms | ✓ | GET / 重定向到前端  |

### api (44/44)

| # | 用例 | 方法 | 路径 | 期望 | 实际 | 用时 | 通过 | 说明 |
|---|---|---|---|---|---|---|---|---|
| 1 | 登录失败 - 空密码 | POST | `/api/users/login` | 401 | 401 | 3.0ms | ✓ | 空白字符串应 401  |
| 2 | 登录失败 - 错误密码 | POST | `/api/users/login` | 401 | 401 | 5.0ms | ✓ | 错误密码应 401  |
| 3 | 登录失败 - 不存在手机号 | POST | `/api/users/login` | 401 | 401 | 6.0ms | ✓ | 手机号不存在应 401  |
| 4 | 获取用户列表(需登录) | GET | `/api/users` | 200 | 200 | 6.0ms | ✓ | 鉴权后下拉框数据  |
| 5 | 错误 token 被拦截 | GET | `/api/users` | 401,403 | 401 | 14.0ms | ✓ | 缺少有效 token 应 401/403  |
| 6 | 创建新投 | POST | `/api/new-policies` | 200 | 200 | 20.6ms | ✓ | 客服端提交一条新投  |
| 7 | 列出新投 | GET | `/api/new-policies?skip=0&limit=10` | 200 | 200 | 5.0ms | ✓ | 分页列出新投  |
| 8 | 获取单条新投 | GET | `/api/new-policies/13` | 200 | 200 | 24.0ms | ✓ | 按 id 查询  |
| 9 | 更新新投 | PUT | `/api/new-policies/13` | 200 | 200 | 25.0ms | ✓ | 编辑字段  |
| 10 | 获取不存在的新投 | GET | `/api/new-policies/99999999` | 404 | 404 | 7.0ms | ✓ | 不存在应返回 404  |
| 11 | 创建批改 | POST | `/api/endorsements` | 200 | 200 | 9.0ms | ✓ | 客服端提交批改  |
| 12 | 列出批改 | GET | `/api/endorsements?skip=0&limit=10` | 200 | 200 | 23.0ms | ✓ |   |
| 13 | 获取单条批改 | GET | `/api/endorsements/8` | 200 | 200 | 5.0ms | ✓ |   |
| 14 | 更新批改 | PUT | `/api/endorsements/8` | 200 | 200 | 29.0ms | ✓ |   |
| 15 | 创建聊天消息(首条→自动建任务) | POST | `/api/chat/messages` | 200 | 200 | 34.5ms | ✓ |   |
| 16 | 再发一条同任务消息 | POST | `/api/chat/messages` | 200 | 200 | 7.0ms | ✓ | 同 task_id 多次发消息  |
| 17 | 获取任务的所有聊天记录 | GET | `/api/chat/messages?task_id=TEST-1789444039` | 200 | 200 | 5.0ms | ✓ | 按 task_id 拉取  |
| 18 | 获取任务列表 | GET | `/api/chat/tasks?skip=0&limit=20` | 200 | 200 | 6.0ms | ✓ | 左侧任务列表  |
| 19 | 上传文件到七牛云 | POST | `/api/chat/upload` | 200 | 200 | 99.7ms | ✓ | 单文件上传到七牛 若无七牛云凭证会失败 |
| 20 | 获取留言(状态=1不允许) | GET | `/api/chat/tasks/TEST-1789444039/comments` | 200 | 200 | 29.7ms | ✓ | 状态 1 应返回空列表  |
| 21 | 状态 1 时不允许留言 | POST | `/api/chat/tasks/TEST-1789444039/comments` | 400,409 | 409 | 5.0ms | ✓ | 非可留言状态应被拒绝  |
| 22 | 修改任务状态到 待确认(2) | PUT | `/api/chat/tasks/TEST-1789444039/status` | 200 | 200 | 9.0ms | ✓ | 必须填写 reject_reason  |
| 23 | 留言(状态=2允许) | POST | `/api/chat/tasks/TEST-1789444039/comments` | 200 | 200 | 8.0ms | ✓ |   |
| 24 | 获取留言(状态=2应返回) | GET | `/api/chat/tasks/TEST-1789444039/comments` | 200 | 200 | 6.0ms | ✓ | 状态 2 应返回列表  |
| 25 | 退回无原因应 400 | PUT | `/api/chat/tasks/TEST-1789444039/status` | 400 | 400 | 4.0ms | ✓ |   |
| 26 | 非法状态值应 400 | PUT | `/api/chat/tasks/TEST-1789444039/status` | 400 | 400 | 5.0ms | ✓ |   |
| 27 | 不存在的任务应 404 | PUT | `/api/chat/tasks/NOT-EXIST/status` | 404 | 404 | 5.0ms | ✓ |   |
| 28 | AI 识别(空文本) | POST | `/api/ai/recognize` | 200 | 200 | 3.0ms | ✓ | 空文本应返回空 dict  |
| 29 | AI 识别(模拟客户对话) | POST | `/api/ai/recognize` | 200 | 200 | 1058.4ms | ✓ | 调用千问 AI 抽取 需千问 API 凭证, 无则返回 {} |
| 30 | AI 提取(按 task_id) | POST | `/api/ai/extract?task_id=TEST-1789444039` | 200 | 200 | 583.1ms | ✓ | 汇总任务消息并 AI 抽取  |
| 31 | 修改密码-旧密码错误 | PUT | `/api/users/2/password` | 401 | 401 | 61.9ms | ✓ |   |
| 32 | 修改密码-新密码过短 | PUT | `/api/users/2/password` | 400 | 400 | 93.0ms | ✓ |   |
| 33 | E2E 发消息: 你好 我们是XX建筑... | POST | `/api/chat/messages` | 200 | 200 | 41.0ms | ✓ |   |
| 34 | E2E 发消息: 我们有 30 个工人... | POST | `/api/chat/messages` | 200 | 200 | 9.0ms | ✓ |   |
| 35 | E2E 发消息: 想投保意外险 年薪 ... | POST | `/api/chat/messages` | 200 | 200 | 29.2ms | ✓ |   |
| 36 | E2E 发消息: 我们是新投 不是续保... | POST | `/api/chat/messages` | 200 | 200 | 31.0ms | ✓ |   |
| 37 | E2E AI 抽取 | POST | `/api/ai/extract?task_id=E2E-1789444041` | 200 | 200 | 961.7ms | ✓ |   |
| 38 | E2E 内勤退回(状态 1→7) | PUT | `/api/chat/tasks/E2E-1789444041/status` | 200 | 200 | 14.0ms | ✓ | 必须填写退回原因  |
| 39 | E2E 退回状态下留言 | POST | `/api/chat/tasks/E2E-1789444041/comments` | 200 | 200 | 10.0ms | ✓ |   |
| 40 | E2E 客户再次提交(7→2) | POST | `/api/chat/messages` | 200 | 200 | 9.0ms | ✓ |   |
| 41 | E2E 完成任务 | PUT | `/api/chat/tasks/E2E-1789444041/status` | 200 | 200 | 8.0ms | ✓ | 状态 3 不在 COMMENTABLE, 不要求 reject_reason  |
| 42 | E2E 验证留言累计 | GET | `/api/chat/tasks/E2E-1789444041/comments` | 200 | 200 | 15.0ms | ✓ | 状态=3, 应返回空  |
| 43 | E2E 已作废后改状态失败 | PUT | `/api/chat/tasks/E2E-1789444041/status` | 200 | 200 | 16.7ms | ✓ | 改为 8 (作废)  |
| 44 | E2E 作废后无法改回 | PUT | `/api/chat/tasks/E2E-1789444041/status` | 400 | 400 | 29.3ms | ✓ | 已作废(8)后状态变更应 400  |

## 失败用例详情

无失败用例
