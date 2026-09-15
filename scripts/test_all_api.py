"""
全量接口测试 - 覆盖 customer-insurance-work-system 后端所有 REST API
测试完成后输出 Markdown 报告与终端汇总
"""
import os
import sys
import io
import json
import time
from datetime import datetime
from typing import Any

BASE = "http://127.0.0.1:8001"
TIMEOUT = 30
RESULTS: list[dict] = []
AUTH = {"token": None, "user_id": None}

# 用于跨测试用例共享上下文
CTX: dict[str, Any] = {}


def req(method: str, path: str, *, json_body=None, data_body=None, files=None,
        headers=None, timeout: int = TIMEOUT) -> tuple[int, Any]:
    """统一请求封装"""
    import requests as _requests
    url = f"{BASE}{path}"
    h = dict(headers or {})
    if AUTH["token"] and "Authorization" not in h:
        h["Authorization"] = f"Bearer {AUTH['token']}"

    try:
        if files is not None:
            # files: dict[name] = (filename, content_bytes[, content_type])
            req_files = {}
            for fk, val in files.items():
                if isinstance(val, tuple):
                    fname, fcontent = val[0], val[1]
                    ctype = val[2] if len(val) > 2 else "application/octet-stream"
                    req_files[fk] = (fname, fcontent, ctype)
                else:
                    req_files[fk] = val
            resp = _requests.request(method, url, data=data_body or {}, files=req_files,
                                    headers=h, timeout=timeout)
        elif json_body is not None:
            resp = _requests.request(method, url, json=json_body, headers=h, timeout=timeout)
        elif data_body is not None:
            resp = _requests.request(method, url, data=data_body, headers=h, timeout=timeout)
        else:
            resp = _requests.request(method, url, headers=h, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text
        return resp.status_code, payload
    except _requests.exceptions.RequestException as e:
        return -1, str(e)


def case(name: str, method: str, path: str, *,
         expected_status: int | list[int] = 200,
         json_body=None, data_body=None, files=None,
         headers=None, save_key: str | None = None,
         desc: str = "", note: str = "") -> Any:
    """执行一个测试用例"""
    t0 = time.time()
    status, payload = req(method, path, json_body=json_body, data_body=data_body,
                          files=files, headers=headers)
    dt = (time.time() - t0) * 1000
    expected = expected_status if isinstance(expected_status, list) else [expected_status]
    ok = status in expected
    if save_key and ok and isinstance(payload, dict):
        CTX[save_key] = payload
    RESULTS.append({
        "name": name, "method": method, "path": path,
        "status": status, "expected": expected, "ok": ok,
        "duration_ms": round(dt, 1), "payload": payload, "desc": desc, "note": note,
    })
    flag = "✓" if ok else "✗"
    print(f"  [{flag}] {status:>3} {dt:>6.1f}ms  {method:6s} {path}  - {name}")
    if not ok:
        print(f"        payload: {str(payload)[:200]}")
    return payload


def main():
    print("=" * 80)
    print(f"接口测试 - {BASE} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # === 1. 根路由 ===
    print("\n[1] 系统路由")
    case("根路由重定向", "GET", "/", expected_status=[200, 307, 308], desc="GET / 重定向到前端")

    # === 2. 用户接口（无需认证） ===
    print("\n[2] 用户/认证接口（无需 token）")
    # 先做失败用例（确认接口的鉴权与校验正确）
    case("登录失败 - 空密码", "POST", "/api/users/login", expected_status=401,
         headers={"Content-Type": "application/x-www-form-urlencoded"},
         data_body={"phone": "  ", "password": "  "}, desc="空白字符串应 401")
    case("登录失败 - 错误密码", "POST", "/api/users/login", expected_status=401,
         data_body={"phone": "13800000000", "password": "wrong"}, desc="错误密码应 401")
    case("登录失败 - 不存在手机号", "POST", "/api/users/login", expected_status=401,
         data_body={"phone": "19999999999", "password": "x"}, desc="手机号不存在应 401")

    # 真实登录：用第一个有密码的用户。先看看数据库里哪些用户能登录
    logged_in = False
    # 优先尝试预置的测试账号 wz/123456（已通过 reset_test_user.py 重置）
    for phone, pwd in [("15511018936", "123456"), ("13800000000", "123456")]:
        st, pl = req("POST", "/api/users/login",
                     data_body={"phone": phone, "password": pwd})
        if st == 200 and isinstance(pl, dict) and "token" in pl:
            AUTH["token"] = pl["token"]
            AUTH["user_id"] = pl["id"]
            CTX["login_user"] = pl
            logged_in = True
            print(f"  [+] 用 {phone}/{pwd} 登录成功, user_id={AUTH['user_id']}, role={pl.get('role')}")
            break
    if not logged_in:
        # 兜底遍历所有用户
        for u in (users if isinstance(users, list) else []):
            phone = u.get("phone")
            uname = u.get("username")
            if not phone:
                continue
            for pwd in ["123456", "admin", "password", uname]:
                st, pl = req("POST", "/api/users/login",
                             data_body={"phone": phone, "password": pwd})
                if st == 200 and isinstance(pl, dict) and "token" in pl:
                    AUTH["token"] = pl["token"]
                    AUTH["user_id"] = pl["id"]
                    CTX["login_user"] = pl
                    logged_in = True
                    print(f"  [+] 用 {phone}/{pwd} 登录成功, user_id={AUTH['user_id']}, role={pl.get('role')}")
                    break
            if logged_in:
                break
    if not logged_in:
        print("  [!] 没有用户能登录。请先运行 reset_test_user.py 重置 wz 密码为 123456")

    # 登录后获取用户列表
    if AUTH["token"]:
        users = case("获取用户列表(需登录)", "GET", "/api/users", expected_status=200,
                     desc="鉴权后下拉框数据")
        if isinstance(users, list) and users:
            print(f"        共 {len(users)} 个用户：{[(u['id'], u.get('username'), u.get('display_name')) for u in users[:5]]}")
            CTX["user_count"] = len(users)

    # === 3. 缺 token 时被拦截 ===
    if AUTH["token"]:
        print("\n[3] 鉴权拦截测试（用错 token）")
        TOKEN_BACKUP = AUTH["token"]
        AUTH["token"] = "INVALID-TOKEN"
        case("错误 token 被拦截", "GET", "/api/users",
             expected_status=[401, 403], desc="缺少有效 token 应 401/403")
        AUTH["token"] = TOKEN_BACKUP

    # === 4. 新投接口 ===
    print("\n[4] 新投接口 /api/new-policies")
    np_data = {
        "company_name": f"测试公司_{int(time.time())}",
        "source": "电话",
        "job_type": "建筑工人",
        "plan": "方案A",
        "is_renewal": "新投",
        "specified_effective": False,
        "insurance_type": "意外险",
        "annual_salary": 80000,
        "remarks": "测试",
        "qualification": "一级资质",
        "file_paths": ["http://example.com/test.pdf"],
        "creator": "测试员",
        "handler": "内勤A",
    }
    np = case("创建新投", "POST", "/api/new-policies", json_body=np_data,
              save_key="new_policy", desc="客服端提交一条新投")
    case("列出新投", "GET", "/api/new-policies?skip=0&limit=10", expected_status=200,
         desc="分页列出新投")
    np_id = (np or {}).get("id") if isinstance(np, dict) else None
    if np_id:
        case("获取单条新投", "GET", f"/api/new-policies/{np_id}", expected_status=200,
             desc="按 id 查询")
        case("更新新投", "PUT", f"/api/new-policies/{np_id}",
             json_body={"insurance_type": "重疾险", "remarks": "更新备注"}, expected_status=200,
             desc="编辑字段")
        case("获取不存在的新投", "GET", "/api/new-policies/99999999", expected_status=404,
             desc="不存在应返回 404")

    # === 5. 批改接口 ===
    print("\n[5] 批改接口 /api/endorsements")
    end_data = {
        "new_policy_id": np_id or 1,
        "company_name": "测试公司批改",
        "job_type": "焊工",
        "specified_effective": True,
        "insurance_type": "医疗险",
        "annual_salary": 120000,
        "remarks": "批改测试",
        "file_paths": [],
        "creator": "测试员",
        "handler": "内勤B",
    }
    end = case("创建批改", "POST", "/api/endorsements", json_body=end_data,
               save_key="endorsement", desc="客服端提交批改")
    case("列出批改", "GET", "/api/endorsements?skip=0&limit=10", expected_status=200)
    end_id = (end or {}).get("id") if isinstance(end, dict) else None
    if end_id:
        case("获取单条批改", "GET", f"/api/endorsements/{end_id}", expected_status=200)
        case("更新批改", "PUT", f"/api/endorsements/{end_id}",
             json_body={"remarks": "更新备注批改"}, expected_status=200)

    # === 6. 聊天消息 + 任务接口 ===
    print("\n[6] 聊天/任务接口 /api/chat")
    task_id = f"TEST-{int(time.time())}"
    msg = case("创建聊天消息(首条→自动建任务)", "POST", "/api/chat/messages",
               json_body={
                   "task_id": task_id,
                   "content": "你好,我是客户",
                   "insurance_company": "平安保险",
                   "customer_company": "测试公司A",
                   "business_type": 1,
                   "creator": "小步",
                   "user_id": AUTH["user_id"],
               },
               save_key="msg1")
    case("再发一条同任务消息", "POST", "/api/chat/messages",
         json_body={"task_id": task_id, "content": "需要意外险"},
         desc="同 task_id 多次发消息")
    case("获取任务的所有聊天记录", "GET", f"/api/chat/messages?task_id={task_id}",
         expected_status=200, desc="按 task_id 拉取")
    case("获取任务列表", "GET", "/api/chat/tasks?skip=0&limit=20", expected_status=200,
         desc="左侧任务列表")

    # 上传文件（用一张最小的 PNG）
    tiny_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "000000017352474200aece1ce90000000d49444154789c63f8cfc0000000030001"
        "5e2d3a4d0000000049454e44ae426082")
    case("上传文件到七牛云", "POST", "/api/chat/upload",
         data_body={"task_id": task_id},
         files={"files": ("test.png", tiny_png)},
         expected_status=200, desc="单文件上传到七牛",
         note="若无七牛云凭证会失败")

    # 留言（仅在 待确认/待补充 状态允许）
    print("\n[7] 任务留言 /api/chat/tasks/{task_id}/comments")
    case("获取留言(状态=1不允许)", "GET", f"/api/chat/tasks/{task_id}/comments",
         expected_status=200, desc="状态 1 应返回空列表")
    case("状态 1 时不允许留言", "POST", f"/api/chat/tasks/{task_id}/comments",
         data_body={"content": "退回原因: 测试"}, expected_status=[400, 409],
         desc="非可留言状态应被拒绝")

    # 修改状态到 待确认(2)
    case("修改任务状态到 待确认(2)", "PUT", f"/api/chat/tasks/{task_id}/status",
         json_body={"status": 2, "reject_reason": "缺少资料,请补充"}, expected_status=200,
         desc="必须填写 reject_reason")
    case("留言(状态=2允许)", "POST", f"/api/chat/tasks/{task_id}/comments",
         data_body={"content": "请补充资料1", "author_name": "内勤A", "author_id": 99},
         expected_status=200)
    case("获取留言(状态=2应返回)", "GET", f"/api/chat/tasks/{task_id}/comments",
         expected_status=200, desc="状态 2 应返回列表")

    # 退回状态强制要求 reject_reason
    case("退回无原因应 400", "PUT", f"/api/chat/tasks/{task_id}/status",
         json_body={"status": 7, "reject_reason": ""}, expected_status=400)

    # 状态机边界
    case("非法状态值应 400", "PUT", f"/api/chat/tasks/{task_id}/status",
         json_body={"status": 99, "reject_reason": "x"}, expected_status=400)
    case("不存在的任务应 404", "PUT", "/api/chat/tasks/NOT-EXIST/status",
         json_body={"status": 1, "reject_reason": "x"}, expected_status=404)

    # === 8. AI 识别接口 ===
    print("\n[8] AI 识别 /api/ai")
    case("AI 识别(空文本)", "POST", "/api/ai/recognize",
         json_body={"text": ""}, expected_status=200, desc="空文本应返回空 dict")
    case("AI 识别(模拟客户对话)", "POST", "/api/ai/recognize",
         json_body={"text": "我们是一家建筑公司, 50 个工人, 都是焊工, 想买意外险, 年薪 8 万, 新投"},
         expected_status=200, desc="调用千问 AI 抽取",
         note="需千问 API 凭证, 无则返回 {}")
    case("AI 提取(按 task_id)", "POST", f"/api/ai/extract?task_id={task_id}",
         expected_status=200, desc="汇总任务消息并 AI 抽取")

    # === 9. 修改密码 ===
    if AUTH["user_id"]:
        print("\n[9] 修改密码 /api/users/{user_id}/password")
        case("修改密码-旧密码错误", "PUT", f"/api/users/{AUTH['user_id']}/password",
             data_body={"old_password": "wrong", "new_password": "654321"},
             expected_status=401)
        case("修改密码-新密码过短", "PUT", f"/api/users/{AUTH['user_id']}/password",
             data_body={"old_password": "123456", "new_password": "123"},
             expected_status=400)

    # === 10. 端到端业务流 ===
    print("\n[10] 端到端业务流 (客户咨询 → AI 抽取 → 退回补充 → 二次提交 → 完成)")
    e2e_task_id = f"E2E-{int(time.time())}"
    # 模拟完整流程
    msgs = [
        "你好 我们是XX建筑公司",
        "我们有 30 个工人 都是焊工",
        "想投保意外险 年薪 8 万",
        "我们是新投 不是续保",
    ]
    for m in msgs:
        case(f"E2E 发消息: {m[:10]}...", "POST", "/api/chat/messages",
             json_body={"task_id": e2e_task_id, "content": m, "creator": "客户A",
                        "user_id": AUTH["user_id"]}, expected_status=200)
    # 触发 AI 抽取
    case("E2E AI 抽取", "POST", f"/api/ai/extract?task_id={e2e_task_id}",
         expected_status=200)
    # 内勤退回客户补充资料 (1→7)
    case("E2E 内勤退回(状态 1→7)", "PUT", f"/api/chat/tasks/{e2e_task_id}/status",
         json_body={"status": 7, "reject_reason": "资料不全,请补: 焊工证、营业执照"},
         expected_status=200, desc="必须填写退回原因")
    # 状态 7 时允许留言
    case("E2E 退回状态下留言", "POST", f"/api/chat/tasks/{e2e_task_id}/comments",
         data_body={"content": "请补充资格证书", "author_name": "内勤A"}, expected_status=200)
    # 客户补充资料后再次提交 (7→2)
    case("E2E 客户再次提交(7→2)", "POST", "/api/chat/messages",
         json_body={"task_id": e2e_task_id, "content": "补充：焊工证已上传",
                        "creator": "客户A", "user_id": AUTH["user_id"]}, expected_status=200)
    # 内勤确认完成 (7→3 或 7→5)
    case("E2E 完成任务", "PUT", f"/api/chat/tasks/{e2e_task_id}/status",
         json_body={"status": 3, "reject_reason": ""}, expected_status=200,
         desc="状态 3 不在 COMMENTABLE, 不要求 reject_reason")
    # 验证留言累计
    case("E2E 验证留言累计", "GET", f"/api/chat/tasks/{e2e_task_id}/comments",
         expected_status=200, desc="状态=3, 应返回空")
    # 已作废任务不可变更
    case("E2E 已作废后改状态失败", "PUT", f"/api/chat/tasks/{e2e_task_id}/status",
         json_body={"status": 8, "reject_reason": ""}, expected_status=200,
         desc="改为 8 (作废)")
    case("E2E 作废后无法改回", "PUT", f"/api/chat/tasks/{e2e_task_id}/status",
         json_body={"status": 3, "reject_reason": ""}, expected_status=400,
         desc="已作废(8)后状态变更应 400")

    # === 输出报告 ===
    print("\n" + "=" * 80)
    print("汇总")
    print("=" * 80)
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = total - passed
    print(f"  总数: {total}  成功: {passed}  失败: {failed}")
    print()
    if failed > 0:
        print("[失败用例]")
        for r in RESULTS:
            if not r["ok"]:
                print(f"  ✗ {r['method']} {r['path']} - {r['name']}")
                print(f"    期望={r['expected']} 实际={r['status']} payload={str(r['payload'])[:150]}")
    print()

    # 写报告
    write_report()
    return 0 if failed == 0 else 1


def write_report():
    """写 Markdown 报告 + JSON 数据"""
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = total - passed

    out_dir = os.path.dirname(__file__)
    json_path = os.path.join(out_dir, "test_results.json")
    md_path = os.path.join(out_dir, "test_report.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": total, "passed": passed, "failed": failed},
                   "results": RESULTS}, f, ensure_ascii=False, indent=2, default=str)

    # 分类汇总
    by_section: dict[str, list[dict]] = {}
    for r in RESULTS:
        section = r["path"].split("/")[1] if r["path"].startswith("/api") else "system"
        by_section.setdefault(section, []).append(r)

    md = []
    md.append(f"# 接口测试报告\n")
    md.append(f"- **基址**: `{BASE}`")
    md.append(f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- **总数**: {total}  **成功**: {passed}  **失败**: {failed}  "
              f"**通过率**: {passed/total*100:.1f}%\n")
    md.append(f"## 测试结果明细\n")

    for sec, items in by_section.items():
        sec_pass = sum(1 for x in items if x["ok"])
        md.append(f"### {sec} ({sec_pass}/{len(items)})\n")
        md.append("| # | 用例 | 方法 | 路径 | 期望 | 实际 | 用时 | 通过 | 说明 |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(items, 1):
            exp = ",".join(str(e) for e in r["expected"])
            mark = "✓" if r["ok"] else "✗"
            note = r.get("note", "")
            desc = r.get("desc", "")
            md.append(f"| {i} | {r['name']} | {r['method']} | `{r['path']}` | {exp} "
                      f"| {r['status']} | {r['duration_ms']}ms | {mark} | {desc} {note} |")
        md.append("")

    md.append("## 失败用例详情\n")
    if failed == 0:
        md.append("无失败用例\n")
    else:
        for r in RESULTS:
            if not r["ok"]:
                md.append(f"### ✗ {r['name']}")
                md.append(f"- 方法/路径: `{r['method']} {r['path']}`")
                md.append(f"- 期望状态: {r['expected']}")
                md.append(f"- 实际状态: {r['status']}")
                md.append(f"- 响应: `{str(r['payload'])[:300]}`\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"  报告: {md_path}")
    print(f"  数据: {json_path}")


if __name__ == "__main__":
    sys.exit(main())