<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { fetchMessages, fileUrl, isImage, extractInsuranceCompany, type ChatTask, type ChatMessage } from '../api';
import AiExtractModal from './AiExtractModal.vue';

const props = defineProps<{
  tasks: ChatTask[];
}>();

const emit = defineEmits<{
  messagesLoaded: [msgs: ChatMessage[]];
}>();

// 每个任务的消息和分页状态
const taskDataMap = ref<Map<string, {
  messages: ChatMessage[];
  page: number;
  loaded: boolean;
}>>(new Map());

const pageSize = 10;

const allMessages = computed(() => {
  const all: ChatMessage[] = [];
  for (const data of taskDataMap.value.values()) {
    all.push(...data.messages);
  }
  return all;
});

watch(() => props.tasks, async (tasks) => {
  if (!tasks.length) {
    taskDataMap.value = new Map();
    return;
  }
  // 加载每个任务的消息
  const newMap = new Map<string, { messages: ChatMessage[]; page: number; loaded: boolean }>();
  for (const t of tasks) {
    const existing = taskDataMap.value.get(t.task_id);
    if (existing) {
      newMap.set(t.task_id, existing);
    } else {
      newMap.set(t.task_id, { messages: [], page: 1, loaded: false });
    }
  }
  taskDataMap.value = newMap;

  // 异步加载未加载的任务
  for (const t of tasks) {
    const data = taskDataMap.value.get(t.task_id);
    if (data && !data.loaded) {
      try {
        const msgs = await fetchMessages(t.task_id);
        data.messages = msgs;
        data.loaded = true;
      } catch (e) {
        console.error('加载消息失败:', t.task_id, e);
      }
    }
  }
  emit('messagesLoaded', allMessages.value);
}, { immediate: true, deep: true });

function getCompany(task: ChatTask): string {
  return task.insurance_company || task.customer_company || '-';
}

function getPagedMessages(taskId: string) {
  const data = taskDataMap.value.get(taskId);
  if (!data) return [];
  const start = (data.page - 1) * pageSize;
  return data.messages.slice(start, start + pageSize);
}

function getTotalPages(taskId: string): number {
  const data = taskDataMap.value.get(taskId);
  if (!data) return 1;
  return Math.max(1, Math.ceil(data.messages.length / pageSize));
}

function getImageCount(taskId: string): number {
  const data = taskDataMap.value.get(taskId);
  if (!data) return 0;
  return data.messages.reduce((n, m) => n + (m.file_paths?.filter(isImage).length || 0), 0);
}

function fmt(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

function changePage(taskId: string, delta: number) {
  const data = taskDataMap.value.get(taskId);
  if (!data) return;
  const maxPage = getTotalPages(taskId);
  data.page = Math.max(1, Math.min(maxPage, data.page + delta));
}

// 图片预览
const previewImage = ref<string | null>(null);

function openPreview(url: string) {
  previewImage.value = url;
}

function closePreview() {
  previewImage.value = null;
}

// AI提取弹窗
const showExtractModal = ref(false);
const currentExtractTask = ref<ChatTask | null>(null);

function handleAiExtract(task: ChatTask) {
  currentExtractTask.value = task;
  showExtractModal.value = true;
}

// OCR识别（前端样式预览，接口待接）
function handleOcr(taskId: string) {
  alert('OCR图片识别功能开发中\n任务: ' + taskId);
}
</script>

<template>
  <section class="work-panel">
    <!-- 顶部栏 -->
    <header class="work-header">
      <div class="header-left">
        <span class="header-title">
          {{ tasks.length ? getCompany(tasks[0]) : '工单详情' }}
        </span>
        <span v-if="tasks.length" class="header-badge">{{ tasks.length }} 个任务</span>
        <span v-if="tasks.length" class="header-badge alt">{{ allMessages.length }} 条记录</span>
      </div>
    </header>

    <!-- 内容区 -->
    <div class="work-body">
      <!-- 空状态 -->
      <div v-if="!tasks.length" class="empty-state">
        <p>从左侧选择保险公司查看工单</p>
      </div>

      <!-- 任务卡片列表 -->
      <div v-else class="card-list">
        <div v-for="task in tasks" :key="task.task_id" class="work-card">
          <!-- 卡片头部 -->
          <div class="card-head">
            <div class="head-main">
              <span class="company-name">{{ task.customer_company }}</span>
              <span v-if="task.business_type === 1" class="type-badge new">新投</span>
              <span v-else-if="task.business_type === 2" class="type-badge edit">批改</span>
              <span class="meta-id">{{ task.task_id }}</span>
            </div>
            <div class="head-aside">
              <span class="aside-time">{{ fmt(task.created_at) }}</span>
            </div>
          </div>

          <!-- 信息面板 -->
          <div class="card-info">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">保险公司</span>
                <span class="info-value">{{ getCompany(task) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">创建人</span>
                <span class="info-value">{{ task.creator_name || task.creator || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">创建时间</span>
                <span class="info-value">{{ fmt(task.created_at) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">附件图片</span>
                <span class="info-value highlight">{{ getImageCount(task.task_id) }} 张</span>
              </div>
            </div>
          </div>

          <!-- 状态流转 -->
          <div class="card-status-bar">
            <div class="status-flow">
              <div class="status-step active">
                <span class="step-dot"></span>
                <span class="step-label">待处理</span>
              </div>
              <div class="status-line"></div>
              <div class="status-step">
                <span class="step-dot"></span>
                <span class="step-label">处理中</span>
              </div>
              <div class="status-line"></div>
              <div class="status-step">
                <span class="step-dot"></span>
                <span class="step-label">已完成</span>
              </div>
            </div>
          </div>

          <!-- 操作栏：AI提取 + OCR识别 -->
          <div class="card-actions">
            <button class="action-btn ai" @click="handleAiExtract(task)">
              <span class="btn-icon">AI</span>
              <span class="btn-text">智能提取</span>
            </button>
            <button class="action-btn ocr" @click="handleOcr(task.task_id)" :disabled="!getImageCount(task.task_id)">
              <span class="btn-icon">OCR</span>
              <span class="btn-text">图片识别</span>
              <span v-if="getImageCount(task.task_id)" class="btn-badge">{{ getImageCount(task.task_id) }}</span>
            </button>
          </div>

          <!-- 沟通记录 -->
          <div class="card-records">
            <div class="records-head">
              <div class="records-title">
                <span class="title-bar"></span>
                <span>提单记录</span>
                <span class="records-count">{{ taskDataMap.get(task.task_id)?.messages.length || 0 }} 条</span>
              </div>
            </div>

            <!-- 加载中 -->
            <div v-if="!taskDataMap.get(task.task_id)?.loaded" class="records-loading">
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
            </div>

            <!-- 记录横向排列 -->
            <div v-else class="record-row">
              <template v-for="msg in getPagedMessages(task.task_id)" :key="msg.id">
                <!-- 该消息的所有图片 -->
                <div v-for="(img, i) in (msg.file_paths?.filter(isImage) || [])" :key="'img-'+msg.id+'-'+i" class="record-card image-card">
                  <img
                    :src="fileUrl(img)"
                    class="rc-img-full"
                    @click="openPreview(fileUrl(img))"
                  />
                  <div class="rc-img-overlay">
                    <span class="rc-creator">{{ msg.creator_name || msg.creator || '匿名' }}</span>
                    <span class="rc-time">{{ fmt(msg.created_at) }}</span>
                  </div>
                </div>
                <!-- 该消息的文字 -->
                <div v-if="msg.content" class="record-card text-card">
                  <div class="rc-head">
                    <span class="rc-creator">{{ msg.creator_name || msg.creator || '匿名' }}</span>
                  </div>
                  <div class="rc-content">{{ msg.content }}</div>
                  <div class="rc-time-bottom">{{ fmt(msg.created_at) }}</div>
                </div>
              </template>
            </div>

            <!-- 无记录 -->
            <div v-if="taskDataMap.get(task.task_id)?.loaded && !getPagedMessages(task.task_id).length" class="no-records">
              暂无沟通记录
            </div>

            <!-- 分页 -->
            <div v-if="getTotalPages(task.task_id) > 1" class="card-page">
              <button class="pg-btn" :disabled="(taskDataMap.get(task.task_id)?.page || 1) <= 1" @click="changePage(task.task_id, -1)">
                ← 上一页
              </button>
              <span class="pg-info">{{ taskDataMap.get(task.task_id)?.page || 1 }} / {{ getTotalPages(task.task_id) }}</span>
              <button class="pg-btn" :disabled="(taskDataMap.get(task.task_id)?.page || 1) >= getTotalPages(task.task_id)" @click="changePage(task.task_id, 1)">
                下一页 →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <div v-if="previewImage" class="img-preview" @click="closePreview">
      <div class="preview-overlay"></div>
      <button class="preview-close" @click="closePreview">✕</button>
      <img :src="previewImage" class="preview-img" @click.stop />
    </div>

    <!-- AI提取弹窗 -->
    <AiExtractModal
      v-if="showExtractModal && currentExtractTask"
      :task="currentExtractTask"
      @close="showExtractModal = false"
      @submitted="showExtractModal = false"
    />
  </section>
</template>

<style scoped>
.work-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f3f6fa;
  min-width: 0;
}

.work-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: #fff;
  border-bottom: 1px solid #e8ecf0;
  flex-shrink: 0;
}

.header-left { display: flex; align-items: center; gap: 14px; }
.header-title { font-size: 20px; font-weight: 600; color: #1a202c; }
.header-badge {
  font-size: 14px; color: var(--primary);
  background: var(--primary-light);
  padding: 4px 12px; border-radius: 8px;
}
.header-badge.alt { color: #245fb5; background: #edf4ff; }

.work-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.empty-state {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--text-muted); font-size: 14px;
}

/* 卡片列表 */
.card-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* 工单卡片 */
.work-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  border: 1px solid #e8ecf0;
  overflow: hidden;
  position: relative;
  transition: box-shadow 0.25s ease;
}

.work-card:hover {
  box-shadow: 0 4px 16px rgba(22, 119, 255, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
}

/* 左侧档案彩条 */
.card-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #0f2b5c 0%, #1677ff 60%, #69b1ff 100%);
  border-radius: 12px 0 0 12px;
}

/* 卡片头部 */
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px 16px 28px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

.head-main {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.company-name {
  font-size: 19px;
  font-weight: 700;
  color: #1a202c;
}

.meta-id {
  font-size: 13px;
  font-family: monospace;
  color: #9ca3af;
  background: #f0f2f5;
  padding: 3px 10px;
  border-radius: 4px;
}

.type-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.type-badge.new {
  background: #e8f4ff;
  color: #1677ff;
}
.type-badge.edit {
  background: #fff7e6;
  color: #fa8c16;
}

.head-aside {
  display: flex;
  align-items: center;
  gap: 14px;
}

.aside-time {
  font-size: 14px;
  color: #9ca3af;
}

/* 信息面板 */
.card-info {
  padding: 10px 24px 10px 28px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 13px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 15px;
  color: #3a3a4a;
  font-weight: 500;
}

.info-value.highlight {
  color: #1677ff;
  font-weight: 600;
}

/* 状态流转条 */
.card-status-bar {
  padding: 10px 24px 10px 28px;
  border-bottom: 1px solid #f0f2f5;
  background: #fff;
}

.status-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.status-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  position: relative;
}

.step-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #d9d9d9;
  background: #fff;
  transition: all 0.3s;
}

.status-step.active .step-dot {
  border-color: #1677ff;
  background: #1677ff;
  box-shadow: 0 0 0 4px rgba(22, 119, 255, 0.15);
}

.status-step.done .step-dot {
  border-color: #52c41a;
  background: #52c41a;
}

.step-label {
  font-size: 13px;
  color: #9ca3af;
  font-weight: 500;
  white-space: nowrap;
}

.status-step.active .step-label {
  color: #1677ff;
  font-weight: 600;
}

.status-step.done .step-label {
  color: #52c41a;
}

.status-line {
  flex: 1;
  height: 2px;
  background: #e8ecf0;
  margin: 0 8px;
  margin-bottom: 22px;
  min-width: 40px;
}

.status-line.active {
  background: linear-gradient(90deg, #1677ff, #69b1ff);
}

/* 操作栏 */
.card-actions {
  display: flex;
  gap: 10px;
  padding: 10px 24px 10px 28px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.action-btn.ai {
  background: linear-gradient(135deg, #1677ff, #4096ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.25);
}

.action-btn.ai:hover {
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.35);
  transform: translateY(-1px);
}

.action-btn.ocr {
  background: #fff;
  color: #1677ff;
  border: 1.5px solid #1677ff;
}

.action-btn.ocr:hover:not(:disabled) {
  background: #e8f4ff;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
}

.action-btn.ocr .btn-icon {
  background: #e8f4ff;
  color: #1677ff;
}

.btn-text {
  font-weight: 500;
}

.btn-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.25);
}

.action-btn.ocr .btn-badge {
  background: #1677ff;
  color: #fff;
}

/* 沟通记录 */
.card-records { padding: 0; }

.records-head {
  padding: 10px 24px 10px 28px;
  border-bottom: 1px solid #f0f2f5;
  background: #fff;
}

.records-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #0f2b5c;
}

.title-bar {
  width: 3px;
  height: 14px;
  background: linear-gradient(180deg, #1677ff, #69b1ff);
  border-radius: 2px;
}

.records-count {
  font-size: 12px;
  font-weight: 400;
  color: #9ca3af;
  background: #f0f2f5;
  padding: 1px 8px;
  border-radius: 8px;
}

.records-loading {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 32px;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1677ff;
  animation: pulse 1.4s ease-in-out infinite;
}

.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* 提单记录 - 横向排列 */
.record-row {
  display: flex;
  gap: 8px;
  padding: 10px 24px 12px 28px;
  overflow-x: auto;
}

/* 图片类型记录 - 大图铺满卡片 */
.image-card {
  flex: 0 0 140px;
  height: 140px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.rc-img-full {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s;
}

.image-card:hover .rc-img-full {
  transform: scale(1.05);
}

.rc-img-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 6px 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.image-card .rc-creator {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.image-card .rc-time {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
}

/* 文字类型记录 */
.text-card {
  flex: 0 0 160px;
  background: #fafbfc;
  border: 1px solid #e8ecf0;
  border-radius: 6px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 80px;
}

.rc-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.text-card .rc-creator {
  font-size: 12px;
  font-weight: 600;
  color: #3a3a4a;
}

.rc-content {
  font-size: 12px;
  line-height: 1.5;
  color: #3a3a4a;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

.rc-time-bottom {
  font-size: 10px;
  color: #9ca3af;
  text-align: right;
  margin-top: auto;
}

.no-records {
  padding: 36px 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

/* 分页 */
.card-page {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 14px 24px 14px 28px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
}

.pg-btn {
  height: 34px;
  padding: 0 18px;
  border: 1px solid #e0e4e8;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}
.pg-btn:hover:not(:disabled) { border-color: #1677ff; color: #1677ff; background: #f0f7ff; }
.pg-btn:disabled { color: #d0d0d0; border-color: #f0f0f0; cursor: not-allowed; }
.pg-info { font-size: 14px; color: #8c8c8c; font-weight: 500; }

/* 图片预览弹窗 */
.img-preview {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
}

.preview-close {
  position: absolute;
  top: 24px;
  right: 28px;
  z-index: 10;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  transition: background 0.2s;
}

.preview-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.preview-img {
  position: relative;
  z-index: 10;
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
</style>
