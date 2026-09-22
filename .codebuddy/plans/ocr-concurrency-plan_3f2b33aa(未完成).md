---
name: ocr-concurrency-plan
overview: 解决内勤页 OCR 识别在多人同时请求时的排队/变慢问题：后端加"结果缓存 + 串行队列 + 启动预热"，前端改成逐张请求、识别出一张显示一张并显示进度与排队。按 9 人同时使用的最坏情况设计，不引入新依赖、不改数据库。
todos:
  - id: backend-cache
    content: 在 ocr_service.py 实现按图片 URL 的结果缓存与 single-flight 去重（标准库，含天花板注释）
    status: pending
  - id: backend-serialize
    content: 实现全局串行锁、等待计数与启动预热 warmup_ocr，并在 main.py 起 daemon 线程调用
    status: pending
    dependencies:
      - backend-cache
  - id: backend-route
    content: OCR 路由加登录鉴权、新增 status 接口，recognize 改走缓存版本且保持多 URL 兼容
    status: pending
    dependencies:
      - backend-serialize
  - id: frontend-stream
    content: 前端 ocrStart 改为逐张请求逐张渲染，加占位文案、单张超时与单选重试，并复用现有 textarea
    status: pending
    dependencies:
      - backend-route
  - id: verify-load
    content: 复现压测：缓存命中、并发去重、串行下界、排队计数、鉴权与回归；用 [skill:ponytail] 复核测试结论，测完清理临时脚本与七牛测试对象
    status: pending
    dependencies:
      - frontend-stream
  - id: review-diff
    content: 用 [skill:ponytail-review] 审阅最终改动，删掉多余复杂度并确认无回归
    status: pending
    dependencies:
      - verify-load
---

## 场景与问题

内勤页的「OCR 识别」在**多人同时使用**时会互相拖死。经实测（本机 i5-10400 / 6 核 12 线程 / 24GB，9 个内勤账号）：

```
单张识别      1.49s，整机 CPU 平均 65%（约 4/6 核）
3 张并发      4.23s  ≈ 3×1.49s
6 张并发      8.81s  ≈ 6×1.49s     → 完全串行，吞吐天花板约 0.67 张/秒
同一张图两次  1.51s / 1.53s        → 没有缓存，重复请求重复算
引擎内存      684MB → 预热后 1063MB → 3 张并发后 1887MB
引擎加载      懒加载（后台空闲进程仅 82MB）→ 重启后第一个人要等 6~35 秒
```

结论：OCR 是**串行资源**，单张已吃掉约 4 个核，所以**加进程/多 worker 没有收益**（只会互抢 CPU 且内存翻倍），实测已排除。9 人 × 每人 6 张 = 54 张 ≈ **81 秒**是串行下界，无法靠硬件消除，只能：少算、公平、可见。

## 现状交互的三个放大问题

1. 一个请求带全部图片（一个人连续占用引擎 6×1.5s），别人全程干等
2. 前端 `authFetch` 没有超时、没有进度 → 用户以为卡死就狂点重试，形成重试风暴
3. 结果只按浏览器 localStorage 缓存，换个人看同一个任务要重算一遍

## 目标

- 9 人同时使用时不互相拖死，且**总耗时不超过串行下界**（不恶化）
- 重复图片不再重复计算；多人同时请求同一张图只计算一次
- 重启后不再有第一个请求长时间等待
- **保持现有 OCR 弹窗交互**，但结果**逐张出现**：识别出一张显示一张，直到全部完成；单张失败可单独重试

## 边界

不改数据库结构、不引入新依赖（标准库解决）、多图片 URL 的老接口保持向后兼容。

## 设计原则

OCR 是串行资源，追求「少算 + 公平 + 可见」，不追求并行。全部用标准库实现，零新增依赖。

## 方案组成

### 1. 结果缓存（收益最大）

图片七牛 key 含随机段且永不覆盖（`qiniu.py` 的 `upload_bytes` 用 `insurance/{task_id}/{uuid6}/{原名}`），因此**按图片 URL 缓存识别结果是安全的**，可近似永久缓存。

- 位置：`backend/cit_api/service/ocr_service.py`，包一层 `_recognize_cached(image_url)`
- 用 `functools.lru_cache` 的思路，但需要自定义（要配合 single-flight），实现为模块级 `OrderedDict` + `_CACHE_LOCK`，上限 2000 条，LRU 淘汰
- 缓存内容存 **JSON 字符串**（不可变、线程安全、返回前 `json.loads`），避免缓存的可变 dict 被调用方改坏
- 只缓存函数正常返回的 `(data, error)`；`_fetch_for_ocr` 抛异常（网络失败）不缓存

### 2. single-flight 去重（同一张图并发只算一次）

模块级 `_INFLIGHT: dict[url, Future]`：抢到 `Future` 的线程负责计算并 `set_result`，其余线程 `future.result()` 等结果。命中缓存直接返回，不进 single-flight。

### 3. 全局串行 + 等待计数

- `_ENGINE_LOCK = threading.Lock()` 包住引擎推理；实测本就串行，加锁只是把「操作系统随机调度」变成「明确排队」，吞吐不降
- 顺带消除线程池被占满的风险（FastAPI 同步接口跑在线程池，9 个长请求会挤占其他接口）
- `_WAITING` 计数器（进入前 +1、退出后 -1）用于反馈排队情况
- 用 `ponytail:` 注释标明天花板：进程内锁，多实例部署时各自串行、各自缓存

### 4. 启动预热

`main.py` 已建 `app` 后，起一个 daemon 线程调 `warmup_ocr()`（`ocr_service` 新增）：`get_engine().initialize()` 加一次极小图的推理（实测首次推理会额外分配约 380MB，预热同时消除这段延迟）。异常只记日志，不影响服务启动。

### 5. OCR 路由加固

- `backend/cit_api/router/ocr_router.py` 的 router 加 `dependencies=[Depends(get_current_user)]`，与 chat、dropdown 路由一致；内勤页用 `authFetch` 已带 token，零改动兼容
- 新增极简 `GET /api/ocr/status` 返回 `{busy, waiting}`，供前端显示「前方还有 N 张」

### 6. 前端逐张流式（用户明确要求的交互）

`frontend/js/app.js` 的 `ocrStart()` 改为**逐张请求**：

- 保留 `ocrResults` 数组结构（下标即图片序号），先把 N 条占位写入「第 N 张识别中…」，每返回一张就覆盖对应下标并重渲染，形成"识别一张显示一张"
- 每张单独 POST `image_urls: [单个url]`（后端接口契约不变，老的多 URL 调用仍可用）
- 单张失败只标记该行失败，不中断后续；该行提供「重试」按钮，只重发这一张
- 每张加超时（AbortController，上限放宽到 180 秒，因为队尾等待本身可能接近串行下界）与排队提示
- `ocrSetResultText()` 改为**复用已存在的 textarea**（仅首次创建），避免流式刷新时反复重建导致光标丢失与输入被清掉
- 复用现有 `ocrFillResult()` 的拼接与 `ocrSaveText()` 落缓存逻辑，不新写渲染路径

## 关键代码结构

```python
# ocr_service.py（新增）
_ENGINE_LOCK = threading.Lock()      # 全局串行
_WAITING = 0                         # 排队人数（加锁读写）
_INFLIGHT: dict                      # url 到 Future，同一张图只算一次
_CACHE: OrderedDict                  # url 到 JSON 文本，LRU 上限 2000

def recognize_id_card_cached(image_url): ...   # 缓存 加 single-flight 加 串行
def ocr_status(): return {"busy": _ENGINE_LOCK.locked(), "waiting": _WAITING}
def warmup_ocr(): ...                          # 启动预热，异常只记日志
```

## 目录结构（只列改动文件）

```
customer-insurance-work-system/
├── backend/cit_api/
│   ├── service/ocr_service.py   # [MODIFY] 结果缓存、single-flight 去重、全局串行锁、等待计数、warmup_ocr
│   ├── router/ocr_router.py     # [MODIFY] 加登录鉴权；新增 GET /api/ocr/status；recognize 走缓存版本
│   └── main.py                  # [MODIFY] 启动 daemon 线程预热 OCR 引擎
└── frontend/js/app.js           # [MODIFY] ocrStart 改逐张请求逐张渲染；占位与单选重试；单张超时；
                                 #           ocrSetResultText 复用现有 textarea
```

## 验证方法（改造后必须复现，沿用同样的测量方式）

1. 缓存：同一 URL 连识别两次，第二次小于 0.2 秒
2. 去重：9 线程并发请求同一 URL，总耗时应约 1.5 秒而非约 13.5 秒；用 monkeypatch 计数确认引擎只被调用 1 次
3. 串行下界：3 人 × 3 张（9 张不同图）并发，总耗时应约 13.5 秒且无错误，不劣化
4. 排队：批量进行中请求 `/api/ocr/status`，busy 为真且 waiting 大于 0
5. 预热：重启后约 15 秒内进程内存应升到 600MB 以上，首个请求不再等模型
6. 前端流式：临时上传 3 张图到七牛、用临时预览页驱动识别，截图确认逐张出现与失败重试
7. 鉴权：不带 token 请求 `/api/ocr/recognize` 返回 401
8. 回归：老的多 URL 一次请求仍可用

测试用的临时脚本、临时预览页与七牛测试对象必须全部清理。

## 明确不做（附实测理由）

| 跳过项 | 理由 |
| --- | --- |
| 多进程 / 多 uvicorn worker | 单张已占约 4/6 核，加进程只互抢 CPU，内存还翻倍（单引擎峰值 1.9GB） |
| 任务队列子系统（异步 job 加轮询页） | 用户明确保持现有弹窗交互，改为逐张流式即可满足「一张一张出现」 |
| Redis / Celery / 消息队列 | 单机单进程，进程内缓存与锁已覆盖 |
| 换更小模型 / 降精度 / GPU | 牺牲识别准确率；机器无 GPU |
| 改数据库存识别结果 | URL 缓存已等价覆盖，且免去表结构与失效逻辑 |


## Agent Extensions

### Skill

- **ponytail**
- Purpose: 审阅本次实现与测试结论是否符合「最小且正确」：确认只用标准库、没有为假想需求引入子系统，并复核实测方法（串行锁定、缓存去重、并发下界）是否成立
- Expected outcome: 给出逐条裁决（保留 / 删除 / 换成标准库等价物）、标注必须保留的天花板注释，并确认「不加进程」的结论有实测支撑

- **ponytail-review**
- Purpose: 对最终改动做一次「过度设计」专项审查，只找可删项与可替换项
- Expected outcome: 输出一行一条的删减清单；确认无死代码、无单实现的抽象、无多余的配置项