/**
 * 客户端 API 层 — 与 client/api.py 完全对应
 * 后端无需任何改动，接口、参数、认证方式全部保持一致
 */

// 后端 API 地址，按实际部署修改（与 client/api.py 中 BASE_URL 一致）
export const BASE_URL = "http://192.168.1.9:8001";

// token 持久化 key（PySide 版存 ~/.insurance_token，这里用 localStorage 等价实现）
const TOKEN_KEY = "insurance_token";

let onUnauthorized = null;

/** 注册 401 回调（用于跳转回登录页） */
export function setOnUnauthorized(fn) {
  onUnauthorized = fn;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  const t = getToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  return h;
}

/** 带超时的 fetch */
async function fetchTimeout(url, options = {}, timeout = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function handle401(resp) {
  if (resp.status === 401) {
    clearToken();
    if (onUnauthorized) onUnauthorized();
    return true;
  }
  return false;
}

/** 相对路径转完整 URL（图片/附件显示用） */
export function toUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${BASE_URL}/${String(path).replace(/^\/+/, "")}`;
}

// ── 登录 / 后端检测 ──

/** 登录（手机号 + 密码），成功保存 token */
export async function login(phone, password) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/users/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ phone, password }),
    },
    5000
  );
  if (resp.status === 401) throw new Error("手机号或密码错误");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  saveToken(data.token);
  return data;
}

/** 检查后端是否可用 */
export async function checkBackend() {
  try {
    const resp = await fetchTimeout(`${BASE_URL}/`, {}, 2000);
    return resp.ok;
  } catch {
    return false;
  }
}

// ── 聊天记录 API ──

/** 获取任务列表（左侧面板） */
export async function listChatTasks(skip = 0, limit = 50) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/tasks?skip=${skip}&limit=${limit}`,
    { headers: authHeaders() },
    3000
  );
  if (handle401(resp)) return [];
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 获取当前用户自己的任务列表 */
export async function listMyChatTasks(userId, skip = 0, limit = 50) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/tasks/mine?user_id=${userId}&skip=${skip}&limit=${limit}`,
    { headers: authHeaders() },
    3000
  );
  if (handle401(resp)) return [];
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 获取某任务的所有聊天记录 */
export async function listChatMessages(taskId) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/messages?task_id=${encodeURIComponent(taskId)}`,
    { headers: authHeaders() },
    3000
  );
  if (handle401(resp)) return [];
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 新增一条聊天记录 */
export async function createChatMessage(payload) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/messages`,
    {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(payload),
    },
    5000
  );
  if (handle401(resp)) throw new Error("登录已过期，请重新登录");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 解析后端错误响应体，取出 detail 文案 */
function parseErrorDetail(text, status) {
  try {
    const data = JSON.parse(text || "{}");
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length) {
      return data.detail[0]?.msg || `HTTP ${status}`;
    }
  } catch {
    /* 非 JSON 响应 */
  }
  return `HTTP ${status}`;
}

/** 当前进行中的上传请求（供取消使用） */
let activeUploadXhr = null;

/** 取消正在进行的上传 */
export function abortUpload() {
  if (activeUploadXhr) {
    try {
      activeUploadXhr.abort();
    } catch {
      /* ignore */
    }
    activeUploadXhr = null;
  }
}

/**
 * 上传文件到后端（multipart，与 client/api.py upload_files 接口一致）
 * 使用 XMLHttpRequest 以获得真实上传进度并支持取消
 * @param {string} taskId
 * @param {File[]} files
 * @param {(percent: number) => void} [onProgress]
 */
export function uploadFiles(taskId, files, onProgress) {
  return new Promise((resolve, reject) => {
    if (!files || !files.length) {
      resolve({ file_paths: [] });
      return;
    }
    const xhr = new XMLHttpRequest();
    activeUploadXhr = xhr;
    const finish = () => {
      if (activeUploadXhr === xhr) activeUploadXhr = null;
    };

    xhr.open("POST", `${BASE_URL}/api/chat/upload`, true);
    xhr.timeout = 180000; // 3 分钟（大文件上传留足时间）
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) {
        onProgress(Math.min(99, Math.round((e.loaded / e.total) * 100)));
      }
    };

    xhr.onload = () => {
      finish();
      if (xhr.status === 401) {
        clearToken();
        if (onUnauthorized) onUnauthorized();
        reject(new Error("登录已过期，请重新登录"));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        // 后端会返回 {"detail": "文件过大：xxx，最大允许 50MB"}，透出给用户
        reject(new Error(parseErrorDetail(xhr.responseText, xhr.status)));
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText || "{}"));
      } catch {
        resolve({ file_paths: [] });
      }
    };
    xhr.onerror = () => {
      finish();
      reject(new Error("网络错误"));
    };
    xhr.ontimeout = () => {
      finish();
      reject(new Error("上传超时"));
    };
    xhr.onabort = () => {
      finish();
      const err = new Error("已取消上传");
      err.cancelled = true;
      reject(err);
    };

    const fd = new FormData();
    fd.append("task_id", taskId);
    for (const f of files) fd.append("files", f, f.name);
    xhr.send(fd);
  });
}

// ── 用户认证 API ──

/** 获取用户列表 */
export async function listUsers() {
  const resp = await fetchTimeout(`${BASE_URL}/api/users`, {
    headers: authHeaders(),
  }, 3000);
  if (handle401(resp)) return [];
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 修改密码 */
export async function changePassword(userId, oldPassword, newPassword) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/users/${userId}/password`,
    {
      method: "PUT",
      headers: {
        ...authHeaders(false),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ old_password: oldPassword, new_password: newPassword }),
    },
    5000
  );
  if (handle401(resp)) throw new Error("登录已过期，请重新登录");
  if (resp.status === 400 || resp.status === 401 || resp.status === 404) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── 任务留言 API ──

/** 获取任务留言列表 */
export async function listTaskComments(taskId) {
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/tasks/${encodeURIComponent(taskId)}/comments`,
    { headers: authHeaders() },
    3000
  );
  if (handle401(resp)) return [];
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** 新增留言 */
export async function addTaskComment(taskId, content, authorName = null, authorId = null) {
  const body = { content };
  if (authorName !== null && authorName !== undefined) body.author_name = authorName;
  if (authorId !== null && authorId !== undefined) body.author_id = authorId;
  const resp = await fetchTimeout(
    `${BASE_URL}/api/chat/tasks/${encodeURIComponent(taskId)}/comments`,
    {
      method: "POST",
      headers: {
        ...authHeaders(false),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams(body),
    },
    5000
  );
  if (handle401(resp)) throw new Error("登录已过期，请重新登录");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── AI 识别 API（备用，与 client/api.py 保持一致） ──

/** 调用后端 AI 识别客户信息 */
export async function aiRecognize(text) {
  if (!text || !text.trim()) return {};
  try {
    const resp = await fetchTimeout(
      `${BASE_URL}/api/ai/recognize`,
      {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ text }),
      },
      60000
    );
    if (handle401(resp)) return {};
    if (!resp.ok) return {};
    return resp.json();
  } catch (e) {
    console.error("AI 识别失败:", e);
    return {};
  }
}
