"""客户端 API 层"""
import os
import requests

# 后端 API 地址，按实际部署修改
BASE_URL = "http://192.168.1.9:8001"

# token 存储路径：C:\Users\用户名\.insurance_token
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".insurance_token")

# 全局 token，启动时从文件加载
_token = None


def _load_token():
    """启动时从文件加载 token"""
    global _token
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                _token = f.read().strip()
    except Exception:
        _token = None


def _save_token(token):
    """登录成功后保存 token 到文件"""
    global _token
    _token = token
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception:
        pass


def _clear_token():
    """退出登录时删除 token 文件"""
    global _token
    _token = None
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass


def _get_auth_headers():
    """获取带认证的请求头（JSON 请求用）"""
    h = {"Content-Type": "application/json"}
    if _token:
        h["Authorization"] = f"Bearer {_token}"
    return h


def _get_auth_headers_multipart():
    """获取带认证的请求头（文件上传用，不设置 Content-Type）"""
    h = {}
    if _token:
        h["Authorization"] = f"Bearer {_token}"
    return h


def _handle_401():
    """401 时清除 token"""
    _clear_token()


def login(phone: str, password: str) -> dict:
    """登录（手机号 + 密码）"""
    resp = requests.post(
        f"{BASE_URL}/api/users/login",
        data={"phone": phone, "password": password},
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    _save_token(data.get("token"))
    return data


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
        headers=_get_auth_headers(),
        timeout=3,
    )
    if resp.status_code == 401:
        _handle_401()
        return []
    resp.raise_for_status()
    return resp.json()


def list_chat_messages(task_id: str) -> list[dict]:
    """获取某任务的所有聊天记录"""
    resp = requests.get(
        f"{BASE_URL}/api/chat/messages",
        params={"task_id": task_id},
        headers=_get_auth_headers(),
        timeout=3,
    )
    if resp.status_code == 401:
        _handle_401()
        return []
    resp.raise_for_status()
    return resp.json()


def create_chat_message(task_id: str, content: str,
                        file_paths: list[str] | None = None,
                        creator: str | None = None,
                        user_id: int | None = None,
                        insurance_company: str | None = None,
                        business_type: int | None = None,
                        customer_company: str | None = None) -> dict:
    """新增一条聊天记录"""
    payload = {
        "task_id": task_id,
        "content": content,
        "file_paths": file_paths,
        "creator": creator,
        "user_id": user_id,
        "insurance_company": insurance_company,
        "business_type": business_type,
        "customer_company": customer_company,
    }
    resp = requests.post(
        f"{BASE_URL}/api/chat/messages",
        json=payload,
        headers=_get_auth_headers(),
        timeout=5,
    )
    if resp.status_code == 401:
        _handle_401()
        raise Exception("登录已过期，请重新登录")
    if resp.status_code != 200:
        print(f"[API] 响应 {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def upload_files(task_id: str, file_paths: list[str]) -> dict:
    """上传文件到后端"""
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
        headers=_get_auth_headers_multipart(),
        timeout=30,
    )
    # 关闭文件
    for _, (_, f) in files:
        f.close()
    if resp.status_code == 401:
        _handle_401()
        raise Exception("登录已过期，请重新登录")
    resp.raise_for_status()
    return resp.json()


# ── 用户认证 API ──

def list_users() -> list[dict]:
    """获取用户列表"""
    resp = requests.get(
        f"{BASE_URL}/api/users",
        headers=_get_auth_headers(),
        timeout=3,
    )
    if resp.status_code == 401:
        _handle_401()
        return []
    resp.raise_for_status()
    return resp.json()


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    resp = requests.put(
        f"{BASE_URL}/api/users/{user_id}/password",
        data={"old_password": old_password, "new_password": new_password},
        headers=_get_auth_headers(),
        timeout=5,
    )
    if resp.status_code == 401:
        _handle_401()
        raise Exception("登录已过期，请重新登录")
    resp.raise_for_status()
    return resp.json()


# ── 任务留言 API ──

def list_task_comments(task_id: str) -> list[dict]:
    """获取任务留言列表"""
    resp = requests.get(
        f"{BASE_URL}/api/chat/tasks/{task_id}/comments",
        headers=_get_auth_headers(),
        timeout=3,
    )
    if resp.status_code == 401:
        _handle_401()
        return []
    resp.raise_for_status()
    return resp.json()


def add_task_comment(task_id: str, content: str,
                     author_name: str | None = None,
                     author_id: int | None = None) -> dict:
    """新增留言"""
    data = {"content": content}
    if author_name is not None:
        data["author_name"] = author_name
    if author_id is not None:
        data["author_id"] = author_id
    resp = requests.post(
        f"{BASE_URL}/api/chat/tasks/{task_id}/comments",
        data=data,
        headers=_get_auth_headers(),
        timeout=5,
    )
    if resp.status_code == 401:
        _handle_401()
        raise Exception("登录已过期，请重新登录")
    resp.raise_for_status()
    return resp.json()


# ── AI 识别 API ──

def ai_recognize(text: str) -> dict:
    """调用后端 AI 识别客户信息"""
    if not text or not text.strip():
        return {}
    try:
        resp = requests.post(
            f"{BASE_URL}/api/ai/recognize",
            json={"text": text},
            headers=_get_auth_headers(),
            timeout=60,
        )
        if resp.status_code == 401:
            _handle_401()
            return {}
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"AI 识别失败: {e}")
        return {}


# ── 启动时加载 token ──

_load_token()
