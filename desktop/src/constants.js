/**
 * 常量与格式化工具
 */

/** 任务状态映射 */
export const STATUS_MAP = {
  1: { label: "进行中", fg: "#fa8c16", bg: "#fff7e6", color: "#fa8c16" },
  2: { label: "待确认", fg: "#1677ff", bg: "#e8f4ff", color: "#1677ff" },
  3: { label: "已做单", fg: "#52c41a", bg: "#f6ffed", color: "#52c41a" },
  4: { label: "已递交", fg: "#13c2c2", bg: "#e6fffb", color: "#13c2c2" },
  5: { label: "对公认款", fg: "#722ed1", bg: "#f9f0ff", color: "#722ed1" },
  6: { label: "二维码", fg: "#eb2f96", bg: "#fff0f6", color: "#eb2f96" },
  7: { label: "待补充", fg: "#fa541c", bg: "#fff2e8", color: "#fa541c" },
  8: { label: "已作废", fg: "#8c8c8c", bg: "#f5f5f5", color: "#8c8c8c" },
  9: { label: "待递交", fg: "#1677ff", bg: "#e8f4ff", color: "#1677ff" },
};

export const UNKNOWN_STATUS = {
  label: "未知",
  fg: "#8c8c8c",
  bg: "#f5f5f5",
  color: "#8c8c8c",
};

export function statusInfo(status) {
  return STATUS_MAP[status] || UNKNOWN_STATUS;
}

/** 保单类型：1新投 / 2批改 */
export function taskTypeLabel(businessType) {
  return businessType === 2 ? "批改" : "新投";
}

/** 用户角色：0管理员/1客服(提单人)/2内勤(做单人) */
export const ROLE_MAP = {
  0: "管理员",
  1: "客服",
  2: "保险内勤",
};

export function roleLabel(role) {
  if (role === null || role === undefined) return "用户";
  return ROLE_MAP[role] || "用户";
}

/** 支持的图片扩展名 */
export const IMAGE_EXTS = new Set([
  ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
]);

/** 上传文件过滤器 */
export const UPLOAD_ACCEPT =
  ".png,.jpg,.jpeg,.bmp,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv";

/** 后端允许的扩展名（与 backend/cit_api/router/message_router.py ALLOWED_EXTS 一致） */
export const ALLOWED_EXTS = new Set([
  ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
  ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv",
]);

/** 单文件大小上限（与后端 MAX_FILE_SIZE 一致：50MB） */
export const MAX_UPLOAD_SIZE = 50 * 1024 * 1024;

export const MAX_UPLOAD_LABEL = "50MB";

/**
 * 上传前预校验（大小 + 类型），返回错误文案，通过则返回空字符串
 * 规则与后端保持一致，避免把文件传上去才被 400 拒绝
 */
export function validateUploadFile(file, name) {
  const displayName = name || file.name || "文件";
  if (file.size > MAX_UPLOAD_SIZE) {
    return `文件过大：${displayName}（${fmtSize(file.size)}），单个文件最大允许 ${MAX_UPLOAD_LABEL}`;
  }
  const ext = extOf(displayName);
  if (ext && !ALLOWED_EXTS.has(ext)) {
    return `不支持的文件类型：${ext}`;
  }
  return "";
}

/** 附件类型图标 */
const FILE_ICONS = {
  ".pdf": "📕",
  ".doc": "📘",
  ".docx": "📘",
  ".xls": "📗",
  ".xlsx": "📗",
  ".txt": "📄",
  ".csv": "📊",
};

export function fileIcon(path) {
  return FILE_ICONS[extOf(path)] || "📎";
}

export function extOf(path) {
  if (!path) return "";
  const clean = String(path).split("?")[0].split("#")[0];
  const dot = clean.lastIndexOf(".");
  return dot >= 0 ? clean.slice(dot).toLowerCase() : "";
}

/** 文件名（去掉 URL 路径，并把 URL 转义解回原名） */
export function baseName(path) {
  if (!path) return "";
  const clean = String(path).split("?")[0];
  const parts = clean.split("/");
  const raw = parts[parts.length - 1] || clean;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw; // 名字里带 % 等非法转义时原样返回，避免抛异常
  }
}

export function isImagePath(path) {
  return IMAGE_EXTS.has(extOf(path));
}

/**
 * 完整日期时间：YYYY-MM-DD HH:mm:ss
 * 后端返回 ISO 格式（2026-09-17T09:48:37），替换 T 并截取 19 位
 */
export function fmtDateTime(dt) {
  if (!dt) return "-";
  return String(dt).slice(0, 19).replace("T", " ");
}

/** 仅日期：YYYY-MM-DD */
export function fmtDate(dt) {
  if (!dt) return "-";
  return String(dt).slice(0, 10);
}

/** 消息分隔线时间文案：今天 / 昨天 / YYYY-MM-DD */
export function fmtDivider(dt) {
  if (!dt) return "";
  const s = String(dt).slice(0, 19).replace("T", " ");
  const day = s.slice(0, 10);
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  if (day === today) return `今天 ${s.slice(11, 16)}`;
  const y = new Date(now.getTime() - 86400000);
  const yesterday = `${y.getFullYear()}-${pad(y.getMonth() + 1)}-${pad(y.getDate())}`;
  if (day === yesterday) return `昨天 ${s.slice(11, 16)}`;
  return s.slice(0, 16);
}

/** 文件大小格式化 */
export function fmtSize(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** 长文件名中间省略，保留扩展名（如：保单原件扫描…final.pdf） */
export function truncateMiddle(str, max = 20) {
  if (!str || str.length <= max) return str;
  const tail = 8; // 保留尾部字符数（含扩展名）
  const head = max - tail - 1;
  return str.slice(0, head) + "…" + str.slice(-tail);
}
