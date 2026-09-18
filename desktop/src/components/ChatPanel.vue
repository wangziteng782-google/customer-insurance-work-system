<template>
  <div class="chat-panel">
    <!-- 顶部任务头 -->
    <div class="chat-top-bar">
      <template v-if="currentTaskId">
        <span class="task-company" :title="customerCompany">
          {{ customerCompany || "未填写客户公司" }}
        </span>
        <span class="status-badge" :style="badgeStyle">
          {{ statusInfo(taskStatus).label }}
        </span>
        <span class="meta">{{ taskMsgCount }} 条消息</span>
      </template>
      <template v-else-if="insuranceCompany">
        <span class="task-company">{{ insuranceCompany }} · {{ taskTypeLabel(policyType) }}</span>
        <span class="meta">新保单收集中</span>
      </template>
      <span v-else class="task-company muted">当前任务：未选择</span>

      <span class="spacer"></span>
      <button
        class="new-btn"
        :disabled="uploading"
        @click="showNewPolicy = true"
      >
        开启新保单收集
      </button>
    </div>

    <!-- 消息列表 -->
    <div ref="scrollEl" class="msg-scroll" @scroll="onScroll">
      <div class="msg-list">
        <!-- 空状态引导 -->
        <div v-if="showEmptyState" class="empty-state">
          <div class="empty-title">还没有选择保单</div>
          <div class="empty-sub">
            从左侧列表选择一笔保单查看沟通记录<br />
            或点击右上角「开启新保单收集」创建新任务
          </div>
        </div>

        <div v-else-if="loadingHistory" class="loading-hint">加载消息中...</div>

        <template v-else>
          <ChatMessage
            v-for="(m, i) in messages"
            :key="i"
            :content="m.content"
            :file-paths="m.filePaths"
            :is-handler="m.type === 'handler'"
            @view-image="openViewer"
          />
        </template>
      </div>

      <!-- 新消息浮动提示 -->
      <transition name="pop">
        <button v-if="hasNewBelow" class="new-msg-btn" @click="jumpToBottom">
          ↓ 新消息
        </button>
      </transition>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-bar">
        <div class="upload-track">
          <div
            class="upload-fill"
            :style="{ width: (uploadPercent ?? 0) + '%' }"
          ></div>
        </div>
        <span class="upload-text">上传中 {{ uploadPercent ?? 0 }}%</span>
        <button class="upload-cancel" @click="cancelUpload">取消</button>
      </div>

      <div
        class="input-frame"
        :class="{
          drag: dragActive && inputEnabled,
          disabled: !inputEnabled,
          expanded: inputExpanded,
        }"
        @dragenter="onDragEnter"
        @dragover.prevent
        @dragleave="onDragLeave"
        @drop.prevent="onDrop"
      >
        <!-- 附件胶囊 -->
        <div v-if="pendingFiles.length" class="attach-row">
          <div
            v-for="(f, i) in pendingFiles"
            :key="f.key"
            class="attach-chip"
            :title="f.name"
          >
            <img v-if="f.isImage" :src="f.url" class="chip-thumb" />
            <span v-else class="chip-icon">{{ f.icon }}</span>
            <span class="chip-meta">
              <span class="chip-name">{{ f.shortName }}</span>
              <span class="chip-size">{{ f.sizeText }}</span>
            </span>
            <button class="chip-del" title="移除" @click="removeFile(i)">
              ×
            </button>
          </div>
        </div>

        <!-- 拖拽提示 -->
        <div v-if="dragActive && inputEnabled" class="drag-hint">
          松开即可添加附件（单个文件不超过 {{ MAX_UPLOAD_LABEL }}）
        </div>

        <textarea
          ref="textareaEl"
          v-model="inputText"
          :disabled="!inputEnabled"
          :placeholder="
            inputEnabled
              ? '输入文字，可拖拽 / 粘贴图片或文件，Enter 发送，Ctrl+Enter 换行'
              : '请先选择左侧保单，或点击「开启新保单收集」'
          "
          @keydown="onKeydown"
          @paste="onPaste"
          @input="autoGrow"
        ></textarea>

        <div class="btn-row">
          <!-- 输入框放大 / 收起 -->
          <button
            class="expand-btn"
            :class="{ active: inputExpanded }"
            :title="inputExpanded ? '收起输入框' : '放大输入框（便于编写多行内容）'"
            @click="toggleExpand"
          >
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <polyline points="15 3 21 3 21 9" />
              <polyline points="9 21 3 21 3 15" />
              <line x1="21" y1="3" x2="14.5" y2="9.5" />
              <line x1="3" y1="21" x2="9.5" y2="14.5" />
            </svg>
          </button>
          <span class="spacer"></span>
          <button
            class="upload-btn"
            :disabled="!inputEnabled || uploading"
            :title="`支持图片 / 文档，单个文件不超过 ${MAX_UPLOAD_LABEL}`"
            @click="pickFiles"
          >
            ＋ 添加附件
          </button>
          <button
            class="send-btn"
            :disabled="!inputEnabled || uploading || !canSend"
            @click="onSend"
          >
            发送
          </button>
        </div>
      </div>

      <input
        ref="fileInput"
        type="file"
        multiple
        hidden
        :accept="UPLOAD_ACCEPT"
        @change="onFilePicked"
      />
    </div>

    <!-- 新建保单收集对话框 -->
    <NewPolicyDialog
      v-if="showNewPolicy"
      @close="showNewPolicy = false"
      @confirm="onNewPolicyConfirm"
    />

    <!-- 图片查看器 -->
    <ImageViewer
      v-if="viewer"
      :urls="viewer.urls"
      :index="viewer.index"
      @close="viewer = null"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import ChatMessage from "./ChatMessage.vue";
import NewPolicyDialog from "./NewPolicyDialog.vue";
import ImageViewer from "./ImageViewer.vue";
import {
  abortUpload,
  createChatMessage,
  listChatMessages,
  listTaskComments,
  uploadFiles,
} from "../api";
import {
  baseName,
  fileIcon,
  fmtSize,
  isImagePath,
  MAX_UPLOAD_LABEL,
  statusInfo,
  taskTypeLabel,
  truncateMiddle,
  UPLOAD_ACCEPT,
  validateUploadFile,
} from "../constants";
import { store, showToast } from "../store";

const emit = defineEmits(["task-created"]);

// ── 任务上下文 ──
const pendingFiles = ref([]);
const currentTaskId = ref("");
const insuranceCompany = ref("");
const policyType = ref(1);
const customerCompany = ref("");
const taskStatus = ref(1);
const taskMsgCount = ref(0);

const inputText = ref("");
const inputEnabled = ref(false);
const sending = ref(false);
const uploading = ref(false);
const uploadPercent = ref(null);
const loadingHistory = ref(false);
const dragActive = ref(false);
const dragDepth = ref(0);
const inputExpanded = ref(false); // 输入框放大模式
const showNewPolicy = ref(false);
const viewer = ref(null);
const messages = ref([]);
const stickToBottom = ref(true);
const hasNewBelow = ref(false);
let historyGen = 0;
let lastSnapshotKey = "";
let pollTimer = null;

const POLL_INTERVAL = 15000;

const scrollEl = ref(null);
const textareaEl = ref(null);
const fileInput = ref(null);

const badgeStyle = computed(() => {
  const s = statusInfo(taskStatus.value);
  return { color: s.fg, background: s.bg };
});

/** 未选择任何任务时的空状态 */
const showEmptyState = computed(
  () => !currentTaskId.value && !insuranceCompany.value && !messages.value.length
);

const canSend = computed(
  () => !!inputText.value.trim() || pendingFiles.value.length > 0
);

/** 判断是否停在底部附近 */
function onScroll() {
  const el = scrollEl.value;
  if (!el) return;
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  if (stickToBottom.value) hasNewBelow.value = false;
}

async function scrollToBottom() {
  await nextTick();
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight;
}

function jumpToBottom() {
  stickToBottom.value = true;
  hasNewBelow.value = false;
  scrollToBottom();
}

watch(
  () => messages.value.length,
  () => {
    if (stickToBottom.value) scrollToBottom();
    else hasNewBelow.value = true;
  }
);

// ── 任务 ID ──
function genTaskId() {
  const arr = new Uint8Array(4);
  crypto.getRandomValues(arr);
  return (
    "TK-" +
    Array.from(arr)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .toUpperCase()
  );
}

// ── 新建保单收集 ──
function onNewPolicyConfirm({ company, customerCompany: customer, type }) {
  showNewPolicy.value = false;
  insuranceCompany.value = company;
  policyType.value = type;
  customerCompany.value = customer;
  currentTaskId.value = "";
  taskStatus.value = 1;
  taskMsgCount.value = 0;
  clearMessages();
  inputEnabled.value = true;
  nextTick(() => textareaEl.value?.focus());
}

/** 切换任务 */
function setCurrentTask(task) {
  if (!task) {
    showNewPolicy.value = true;
    return;
  }
  currentTaskId.value = task.task_id || "";
  insuranceCompany.value = task.insurance_company || "";
  policyType.value = task.business_type || 1;
  customerCompany.value = task.customer_company || "";
  taskStatus.value = task.status ?? 1;
  taskMsgCount.value = task.msg_count || 0;
  clearMessages();
  // 详情接口仅在 待确认(2)/待补充(7) 状态返回留言；其余状态用列表数据兜底
  loadHistory(currentTaskId.value, task.comments || []);
  inputEnabled.value = true;
  nextTick(() => textareaEl.value?.focus());
}

function clearMessages() {
  messages.value = [];
  lastSnapshotKey = "";
  clearFiles();
  hasNewBelow.value = false;
}

/** 服务端数据指纹：消息/留言 id 集合 */
function snapshotKey(msgs, comments) {
  const m = msgs.map((x) => x.id).sort((a, b) => a - b).join(",");
  const c = comments.map((x) => x.id).sort((a, b) => a - b).join(",");
  return `${msgs.length}[${m}]|${comments.length}[${c}]`;
}

// ── 历史加载 ──
async function loadHistory(taskId, fallbackComments = []) {
  clearMessages();
  stickToBottom.value = true;
  loadingHistory.value = true;
  const gen = ++historyGen;
  try {
    const [msgs, comments] = await Promise.all([
      listChatMessages(taskId),
      listTaskComments(taskId),
    ]);
    if (gen !== historyGen) return;
    loadingHistory.value = false;
    const list =
      comments && comments.length ? comments : fallbackComments || [];
    renderHistory(msgs, list);
  } catch (e) {
    if (gen !== historyGen) return;
    loadingHistory.value = false;
    messages.value.push({
      type: "user",
      content: `加载失败: ${e.message}`,
      filePaths: null,
      createdAt: "",
    });
  }
}

/** 静默自动刷新（15s）：有新留言/消息才重渲染 */
async function refreshMessages() {
  const taskId = currentTaskId.value;
  if (!taskId || sending.value || uploading.value || loadingHistory.value) {
    return;
  }
  const gen = historyGen;
  try {
    const [msgs, comments] = await Promise.all([
      listChatMessages(taskId),
      listTaskComments(taskId),
    ]);
    if (gen !== historyGen || taskId !== currentTaskId.value) return;
    if (snapshotKey(msgs, comments) === lastSnapshotKey) return;
    renderHistory(msgs, comments);
  } catch (e) {
    console.error("自动刷新消息失败:", e);
  }
}

/** 渲染时间线：合并 + 排序 + 图片/文字重排 */
function renderHistory(msgs, comments) {
  lastSnapshotKey = snapshotKey(msgs, comments);
  const timeline = [];
  for (const m of msgs) {
    timeline.push(["user", m.created_at || "", m]);
  }
  for (const c of comments) {
    timeline.push(["handler", c.created_at || "", c]);
  }
  timeline.sort((a, b) => String(a[1]).localeCompare(String(b[1])));

  const reordered = [];
  let i = 0;
  while (i < timeline.length) {
    const curr = timeline[i];
    const nxt = i + 1 < timeline.length ? timeline[i + 1] : null;
    const isTextAfterImage =
      nxt &&
      curr[0] === "user" &&
      nxt[0] === "user" &&
      !curr[2].content &&
      curr[2].file_paths &&
      nxt[2].content &&
      !nxt[2].file_paths;
    if (isTextAfterImage) {
      reordered.push(nxt);
      reordered.push(curr);
      i += 2;
    } else {
      reordered.push(curr);
      i += 1;
    }
  }

  messages.value = reordered.map(([type, , data]) => ({
    type,
    content: data.content || "",
    filePaths: data.file_paths || null,
    createdAt: data.created_at || "",
  }));
}

// ── 待上传附件 ──
function addFile(file) {
  if (!file) return;
  const name = file.name || `剪贴板图片-${Date.now()}.png`;
  // 上传前校验（大小 / 类型，规则与后端一致），避免传上去才被 400 拒绝
  const err = validateUploadFile(file, name);
  if (err) {
    showToast(err, "error");
    return;
  }
  if (
    pendingFiles.value.some(
      (f) =>
        f.name === name &&
        f.file.size === file.size &&
        f.file.lastModified === file.lastModified
    )
  ) {
    return;
  }
  const isImage = isImagePath(name) || (file.type || "").startsWith("image/");
  pendingFiles.value.push({
    key: `${name}-${file.size}-${file.lastModified}-${Date.now()}`,
    file,
    name,
    isImage,
    icon: fileIcon(name),
    sizeText: fmtSize(file.size),
    shortName: truncateMiddle(baseName(name), 22),
    url: isImage ? URL.createObjectURL(file) : "",
  });
}

function removeFile(index) {
  const f = pendingFiles.value[index];
  if (f && f.url) URL.revokeObjectURL(f.url);
  pendingFiles.value.splice(index, 1);
}

function clearFiles() {
  for (const f of pendingFiles.value) {
    if (f.url) URL.revokeObjectURL(f.url);
  }
  pendingFiles.value = [];
}

onUnmounted(clearFiles);

// ── 轮询定时器 ──
onMounted(() => {
  pollTimer = setInterval(refreshMessages, POLL_INTERVAL);
});
onUnmounted(() => clearInterval(pollTimer));

// ── 文件选择 ──
function pickFiles() {
  fileInput.value?.click();
}

function onFilePicked(e) {
  for (const f of e.target.files || []) addFile(f);
  e.target.value = "";
}

// ── 拖拽 ──
function onDragEnter(e) {
  if (!inputEnabled.value) return;
  if (!e.dataTransfer?.types?.includes("Files")) return;
  dragDepth.value++;
  dragActive.value = true;
}

function onDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1);
  if (dragDepth.value <= 0) dragActive.value = false;
}

function onDrop(e) {
  dragDepth.value = 0;
  dragActive.value = false;
  if (!inputEnabled.value) return;
  for (const f of e.dataTransfer?.files || []) addFile(f);
}

// ── 粘贴 ──
function onPaste(e) {
  if (!inputEnabled.value) return;
  const dt = e.clipboardData;
  if (!dt) return;
  let added = false;
  for (const f of dt.files || []) {
    addFile(f);
    added = true;
  }
  if (!added) {
    for (const item of dt.items || []) {
      if (item.kind === "file") {
        const f = item.getAsFile();
        if (f && ((f.type || "").startsWith("image/") || isImagePath(f.name))) {
          addFile(
            new File([f], f.name || `剪贴板图片-${Date.now()}.png`, {
              type: f.type || "image/png",
            })
          );
          added = true;
        }
      }
    }
  }
  if (added) e.preventDefault();
}

// ── 键盘 ──
function onKeydown(e) {
  if (e.key === "Enter") {
    if (e.ctrlKey) {
      e.preventDefault();
      insertNewline();
      return;
    }
    e.preventDefault();
    onSend();
  }
}

function insertNewline() {
  const el = textareaEl.value;
  if (!el) {
    inputText.value += "\n";
    return;
  }
  const start = el.selectionStart;
  const end = el.selectionEnd;
  inputText.value =
    inputText.value.slice(0, start) + "\n" + inputText.value.slice(end);
  nextTick(() => {
    el.selectionStart = el.selectionEnd = start + 1;
    autoGrow();
  });
}

/** 输入框高度自适应（放大模式下允许更高） */
function autoGrow() {
  const el = textareaEl.value;
  if (!el) return;
  const max = inputExpanded.value ? 420 : 160;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, max)}px`;
}

/** 切换输入框放大 / 收起 */
function toggleExpand() {
  inputExpanded.value = !inputExpanded.value;
  nextTick(() => {
    autoGrow();
    textareaEl.value?.focus();
  });
}

// ── 发送 ──
function cancelUpload() {
  abortUpload();
}

async function onSend() {
  const text = inputText.value.trim();
  if (!text && !pendingFiles.value.length) return;

  sending.value = true;
  let newTaskId = null;
  if (!currentTaskId.value) {
    currentTaskId.value = genTaskId();
    newTaskId = currentTaskId.value;
  }

  // 有附件 → 上传
  let filePaths = [];
  if (pendingFiles.value.length) {
    uploading.value = true;
    uploadPercent.value = 0;
    let cancelled = false;
    try {
      const result = await uploadFiles(
        currentTaskId.value,
        pendingFiles.value.map((f) => f.file),
        (p) => (uploadPercent.value = p)
      );
      filePaths = result.file_paths || [];
    } catch (e) {
      if (e.cancelled) {
        cancelled = true;
        showToast("已取消上传", "info");
      } else {
        console.error("文件上传失败:", e);
        showToast(`文件上传失败: ${e.message}`, "error");
      }
    } finally {
      uploading.value = false;
      uploadPercent.value = null;
    }
    if (cancelled) {
      // 取消则中止本次发送，保留已输入内容与附件
      sending.value = false;
      return;
    }
  }

  // 本地乐观渲染
  const createdAt = new Date().toISOString();
  if (text || filePaths.length) {
    messages.value.push({
      type: "user",
      content: text,
      filePaths: filePaths.length ? filePaths : null,
      createdAt,
    });
  }

  // 保存到后端
  if (text || filePaths.length) {
    try {
      await createChatMessage({
        task_id: currentTaskId.value,
        content: text,
        file_paths: filePaths.length ? filePaths : null,
        creator: store.user?.display_name ?? null,
        user_id: store.user?.id ?? null,
        insurance_company: insuranceCompany.value,
        business_type: policyType.value,
        customer_company: customerCompany.value,
      });
      taskMsgCount.value += 1;
    } catch (e) {
      console.error("保存消息失败:", e);
      showToast(`保存消息失败: ${e.message}`, "error");
    }
  }

  if (newTaskId) emit("task-created", newTaskId);

  inputText.value = "";
  clearFiles();
  sending.value = false;
  nextTick(() => {
    autoGrow();
    textareaEl.value?.focus();
  });
}

// ── 图片查看 ──
function openViewer(urls, index) {
  viewer.value = { urls, index };
}

defineExpose({ setCurrentTask });
</script>

<style scoped>
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  position: relative;
}

/* ── 任务头 ── */
.chat-top-bar {
  height: 46px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--top-bg);
  border-bottom: 1px solid var(--border);
}
.task-company {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-company.muted {
  color: var(--text-muted);
  font-weight: 500;
}
.status-badge {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  padding: 1px 7px;
  line-height: 18px;
}
.meta {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.spacer {
  flex: 1;
}
.new-btn {
  width: 130px;
  height: 30px;
  flex: none;
  background: var(--primary);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  font-weight: bold;
}
.new-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}
.new-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

/* ── 消息区 ── */
.msg-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  background: #fafafa;
  position: relative;
}
.msg-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
}
.loading-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 24px 0;
}


/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}
.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.empty-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.8;
}

/* 新消息提示 */
.new-msg-btn {
  position: absolute;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  background: var(--primary);
  color: #fff;
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 14px;
  box-shadow: 0 2px 10px rgba(22, 119, 255, 0.35);
}
.new-msg-btn:hover {
  background: var(--primary-hover);
}
.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(6px);
}

/* ── 输入区 ── */
.input-area {
  flex-shrink: 0;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  padding: 8px 16px 12px;
}
.upload-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.upload-track {
  flex: 1;
  height: 4px;
  background: #eef1f5;
  border-radius: 2px;
  overflow: hidden;
}
.upload-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.2s;
}
.upload-text {
  font-size: 11px;
  color: var(--text-secondary);
}
.upload-cancel {
  font-size: 11px;
  color: #ff4d4f;
  padding: 2px 6px;
  border-radius: 4px;
}
.upload-cancel:hover {
  background: #fff2f0;
}

.input-frame {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.15s, background 0.15s;
}
.input-frame:focus-within {
  border-color: var(--primary);
}
.input-frame.drag {
  border: 2px dashed var(--primary);
  background: var(--primary-light);
}
.input-frame.disabled {
  opacity: 0.75;
}

/* 附件胶囊 */
.attach-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px 0;
}
.attach-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  padding: 3px 6px;
  background: #f5f7fa;
  border: 1px solid #e8ecf2;
  border-radius: 6px;
}
.chip-thumb {
  width: 26px;
  height: 26px;
  object-fit: cover;
  border-radius: 4px;
  flex: none;
}
.chip-icon {
  font-size: 16px;
  flex: none;
}
.chip-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chip-name {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chip-size {
  font-size: 10px;
  color: var(--text-muted);
}
.chip-del {
  flex: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #d0d3d9;
  color: #fff;
  font-size: 11px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chip-del:hover {
  background: #ff4d4f;
}

.drag-hint {
  text-align: center;
  font-size: 12px;
  color: var(--primary);
  padding: 6px 0 0;
  font-weight: 500;
}

textarea {
  display: block;
  width: 100%;
  min-height: 56px;
  max-height: 160px;
  border: none;
  outline: none;
  resize: none;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
  background: transparent;
  overflow-y: auto;
}
textarea::placeholder {
  color: #c0c4cc;
}
textarea:disabled {
  cursor: not-allowed;
}

/* 放大模式：输入框明显变高，便于编写 / 查看多行内容 */
.input-frame.expanded textarea {
  min-height: 300px;
  max-height: 420px;
}

/* 放大 / 收起按钮 */
.expand-btn {
  flex: none;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  background: transparent;
}
.expand-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-light);
}
.expand-btn svg {
  transition: transform 0.2s;
}
.expand-btn.active {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-light);
}
.expand-btn.active svg {
  transform: rotate(180deg);
}

.btn-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px 8px 10px;
}
.upload-btn {
  height: 28px;
  padding: 0 12px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
}
.upload-btn:hover:not(:disabled) {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-light);
}
.upload-btn:disabled,
.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.send-btn {
  width: 58px;
  height: 28px;
  background: var(--primary);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  font-weight: bold;
}
.send-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}
</style>
