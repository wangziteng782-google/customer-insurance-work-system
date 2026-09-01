"""客户端 API 层"""
import requests

# 后端 API 地址，按实际部署修改
BASE_URL = "http://127.0.0.1:8000"


def create_new_policy(data: dict) -> dict:
    """提交一条新投"""
    resp = requests.post(f"{BASE_URL}/api/new-policies", json=data, timeout=5)
    resp.raise_for_status()
    return resp.json()


def update_new_policy(policy_id: int, data: dict) -> dict:
    """编辑更新新投"""
    resp = requests.put(f"{BASE_URL}/api/new-policies/{policy_id}", json=data, timeout=5)
    resp.raise_for_status()
    return resp.json()


def list_new_policies(skip: int = 0, limit: int = 10) -> list[dict]:
    """拉取新投列表（分页）"""
    resp = requests.get(
        f"{BASE_URL}/api/new-policies", params={"skip": skip, "limit": limit}, timeout=3
    )
    resp.raise_for_status()
    return resp.json()


def create_endorsement(data: dict) -> dict:
    """提交一条批改"""
    resp = requests.post(f"{BASE_URL}/api/endorsements", json=data, timeout=5)
    resp.raise_for_status()
    return resp.json()


def update_endorsement(endorsement_id: int, data: dict) -> dict:
    """编辑更新批改"""
    resp = requests.put(f"{BASE_URL}/api/endorsements/{endorsement_id}", json=data, timeout=5)
    resp.raise_for_status()
    return resp.json()


def ai_recognize(text: str) -> dict:
    """调用后端 AI 识别客户信息

    Args:
        text: 客户对话文本

    Returns:
        识别出的字段 dict，例如：
        {"company_name": "XX公司", "insurance_type": "意外险", ...}
    """
    if not text or not text.strip():
        return {}

    try:
        resp = requests.post(
            f"{BASE_URL}/api/ai/recognize",
            json={"text": text},
            timeout=60  # AI 识别可能需要较长时间
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"AI 识别失败: {e}")
        return {}


def check_backend() -> bool:
    """检查后端是否可用"""
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


# ── 聊天记录 API ──

def list_chat_tasks(skip: int = 0, limit: int = 50) -> list[dict]:
    """获取任务列表（左侧面板）"""
    resp = requests.get(
        f"{BASE_URL}/api/chat/tasks",
        params={"skip": skip, "limit": limit},
        timeout=3,
    )
    resp.raise_for_status()
    return resp.json()


def list_chat_messages(task_id: str) -> list[dict]:
    """获取某任务的所有聊天记录"""
    resp = requests.get(
        f"{BASE_URL}/api/chat/messages",
        params={"task_id": task_id},
        timeout=3,
    )
    resp.raise_for_status()
    return resp.json()


def create_chat_message(task_id: str, content: str, msg_type: str = "user",
                        file_paths: list[str] | None = None,
                        creator: str | None = None,
                        user_id: int | None = None,
                        insurance_company: str | None = None) -> dict:
    """新增一条聊天记录"""
    payload = {
        "task_id": task_id,
        "content": content,
        "msg_type": msg_type,
        "file_paths": file_paths,
        "creator": creator,
        "user_id": user_id,
        "insurance_company": insurance_company,
    }
    resp = requests.post(f"{BASE_URL}/api/chat/messages", json=payload, timeout=5)
    resp.raise_for_status()
    return resp.json()


def upload_files(task_id: str, file_paths: list[str]) -> dict:
    """上传文件到后端"""
    import os
    files = []
    for fp in file_paths:
        if os.path.exists(fp):
            files.append(("files", (os.path.basename(fp), open(fp, "rb"))))
    if not files:
        return {"file_paths": []}
    resp = requests.post(
        f"{BASE_URL}/api/chat/upload",
        data={"task_id": task_id},
        files=files,
        timeout=30,
    )
    resp.raise_for_status()
    # 关闭文件
    for _, (_, f) in files:
        f.close()
    return resp.json()
