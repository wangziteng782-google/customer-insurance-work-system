<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { isImage, extractInsuranceCompany, type ChatTask, type ChatMessage } from '../api';

const props = defineProps<{
  tasks: ChatTask[];
  messages: ChatMessage[];
}>();

const summarizing = ref(false);
const summary = ref('');
const ocrLoading = ref(false);

const primaryTask = computed(() => props.tasks[0] || null);

watch(() => props.tasks, () => {
  summary.value = '';
});

const imageCount = computed(() => {
  return props.messages.reduce((n, m) => n + (m.file_paths?.filter(isImage).length || 0), 0);
});

async function runSummary() {
  if (!props.messages.length) return;
  summarizing.value = true;
  try {
    await new Promise(r => setTimeout(r, 800));
    const allText = props.messages.map(m => m.content).filter(Boolean).join('\n');
    summary.value = `【AI 汇总预览】\n\n当前共 ${props.tasks.length} 个任务，${props.messages.length} 条消息。\n\n${allText.slice(0, 300)}${allText.length > 300 ? '...' : ''}`;
  } finally {
    summarizing.value = false;
  }
}

async function runOcr() {
  const images = props.messages.flatMap(m => m.file_paths || []).filter(isImage);
  if (!images.length) return;
  ocrLoading.value = true;
  try {
    await new Promise(r => setTimeout(r, 1000));
    alert(`已识别 ${images.length} 张图片（功能开发中）`);
  } finally {
    ocrLoading.value = false;
  }
}
</script>

<template>
  <aside class="summary-panel">
    <div class="panel-header">
      <h2 class="panel-title">智能助手</h2>
    </div>

    <div class="panel-body">
      <!-- AI 汇总 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">AI 汇总</span>
        </div>
        <p class="card-desc">将对话内容自动整理为结构化保单信息</p>
        <button class="action-btn primary" :disabled="summarizing || !messages.length" @click="runSummary">
          {{ summarizing ? '汇总中...' : '开始汇总' }}
        </button>
        <div v-if="summary" class="summary-output">
          <pre>{{ summary }}</pre>
        </div>
      </div>

      <!-- OCR 识别 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">OCR 识别</span>
        </div>
        <p class="card-desc">从上传的图片中提取文字信息</p>
        <button class="action-btn outline" :disabled="ocrLoading || !messages.length" @click="runOcr">
          {{ ocrLoading ? '识别中...' : `识别图片 (${imageCount})` }}
        </button>
      </div>

      <!-- 任务信息 -->
      <div class="card info-card">
        <div class="card-header">
          <span class="card-title">任务信息</span>
        </div>
        <dl class="info-list">
          <dt>任务数</dt>
          <dd>{{ tasks.length }} 个</dd>
          <dt>总消息</dt>
          <dd>{{ messages.length }} 条</dd>
          <dt>保险公司</dt>
          <dd>{{ primaryTask?.insurance_company || extractInsuranceCompany(primaryTask?.first_content || '') || '-' }}</dd>
          <dt>创建人</dt>
          <dd>{{ primaryTask?.creator_name || primaryTask?.creator || '-' }}</dd>
          <dt>图片数</dt>
          <dd>{{ imageCount }} 张</dd>
        </dl>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.summary-panel {
  width: 280px;
  min-width: 280px;
  height: 100%;
  background: #fff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.panel-header { padding: 18px 18px 10px; border-bottom: 1px solid #f0f0f0; }
.panel-title { font-size: 17px; font-weight: 700; color: var(--primary); margin: 0; }

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card {
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

.card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.card-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.card-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; line-height: 1.5; }

.action-btn {
  width: 100%; height: 36px; border-radius: 6px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.2s; border: none;
}
.action-btn.primary { background: var(--primary); color: #fff; }
.action-btn.primary:hover:not(:disabled) { background: #4096ff; }
.action-btn.outline { background: #fff; color: var(--primary); border: 1px solid var(--primary); }
.action-btn.outline:hover:not(:disabled) { background: var(--primary-light); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.summary-output { margin-top: 12px; padding: 12px; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; }
.summary-output pre { font-size: 13px; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; }

.info-card { background: #f8f9fa; }
.info-list { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 8px 14px; }
.info-list dt { font-size: 13px; color: var(--text-muted); white-space: nowrap; }
.info-list dd { font-size: 13px; color: var(--text-primary); margin: 0; word-break: break-all; }
</style>
