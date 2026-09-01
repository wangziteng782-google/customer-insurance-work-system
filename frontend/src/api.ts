// API 客户端 - 与后端 FastAPI 通信
const BASE_URL = 'http://localhost:8000';

export interface ChatTask {
  task_id: string;
  first_content: string;
  msg_count: number;
  insurance_company: string | null;
  creator: string | null;
  creator_name: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  task_id: string;
  content: string;
  msg_type: 'user' | 'system';
  file_paths: string[] | null;
  creator: string | null;
  creator_name: string | null;
  created_at: string;
}

export async function fetchTasks(skip = 0, limit = 50): Promise<ChatTask[]> {
  const res = await fetch(`${BASE_URL}/api/chat/tasks?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error(`获取任务列表失败: ${res.status}`);
  return res.json();
}

export async function fetchMessages(taskId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE_URL}/api/chat/messages?task_id=${taskId}`);
  if (!res.ok) throw new Error(`获取消息失败: ${res.status}`);
  return res.json();
}

export function fileUrl(path: string): string {
  if (path.startsWith('http')) return path;
  return `${BASE_URL}/${path.replace(/^\//, '')}`;
}

export const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'];

export function isImage(path: string): boolean {
  return IMAGE_EXTS.some(ext => path.toLowerCase().endsWith(ext));
}

// 保险公司列表（用于从 content 提取）
export const INSURANCE_COMPANIES = [
  '人保财险', '平安保险', '太平洋保险', '国寿财险',
  '阳光保险', '新华保险', '泰康保险', '太平保险',
];

// 从 content 中提取保险公司名称
export function extractInsuranceCompany(content: string): string | null {
  for (const company of INSURANCE_COMPANIES) {
    if (content.includes(company)) return company;
  }
  return null;
}
