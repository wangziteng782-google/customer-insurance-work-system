<template>
  <div class="history-panel">
    <!-- 标题行：左「保单列表」 + 右用户信息（由父组件通过插槽传入） -->
    <div class="title-bar">
      <span class="title">保单列表</span>
      <slot name="user" />
    </div>

    <!-- 搜索行：搜索框 + 刷新 -->
    <div class="search-row">
      <div class="search-box">
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索保单..."
        />
        <button
          v-if="searchKeyword"
          class="search-clear"
          title="清空"
          @click="searchKeyword = ''"
        >
          ×
        </button>
      </div>
      <button class="refresh-btn" title="刷新列表" @click="refresh()">↻</button>
    </div>

    <!-- 类型筛选：按钮式（不是下拉）。筛选在后端做，因为列表是分页的 -->
    <div class="filter-row">
      <button
        v-for="f in STATUS_FILTERS"
        :key="f.value"
        class="filter-btn"
        :class="{ on: statusFilter === f.value }"
        @click="setStatusFilter(f.value)"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- 卡片列表 -->
    <div class="scroll-area">
      <div class="card-list">
        <div
          v-for="task in filteredTasks"
          :key="task.task_id"
          class="policy-card"
          :class="{ selected: selectedTaskId === task.task_id }"
          @click="onCardClick(task)"
        >
          <span class="indicator" :style="indicatorStyle(task)"></span>
          <div class="card-content">
            <div class="card-row1">
              <span v-if="isUnread(task)" class="unread-dot"></span>
              <span
                class="card-title"
                :class="{ unread: isUnread(task) }"
                >{{ task.customer_company || "未填写客户公司" }}</span
              >
              <span class="status-badge" :style="badgeStyle(task.status)">
                {{ statusInfo(task.status).label }}
              </span>
            </div>
            <div class="card-row2">
              {{ task.insurance_company || "未填写保险公司" }}
            </div>
            <div class="card-row3">
              <span class="time" :title="`创建：${fmtDateTime(task.created_at)}`">{{
                fmtDateTime(cardTime(task))
              }}</span>
              <span class="msg-count">{{ task.msg_count || 0 }} 条</span>
            </div>
          </div>
        </div>
        <div v-if="!filteredTasks.length" class="empty-hint">
          {{ statusFilter ? "该类型下暂无保单" : "暂无保单" }}
        </div>
      </div>
    </div>

    <!-- 分页控制 -->
    <div class="page-bar">
      <button
        class="page-btn"
        :disabled="currentPage <= 0"
        @click="onPrevPage"
      >
        &lt;
      </button>
      <span class="page-label">{{ currentPage + 1 }}/{{ pageCount }}</span>
      <button
        class="page-btn"
        :disabled="!hasNextPage"
        @click="onNextPage"
      >
        &gt;
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { listChatTasks, listMyChatTasks } from "../api";
import {
  fmtDateTime,
  statusInfo,
} from "../constants";
import { store } from "../store";

const emit = defineEmits(["item-click"]);

const PAGE_SIZE = 10;
const POLL_INTERVAL = 5000; // 10s 轮询 /api/chat/tasks/mine
const LAST_SEEN_KEY = "task_lastseen";

const tasks = ref([]);
const selectedTaskId = ref("");
const currentPage = ref(0);
const totalCount = ref(0);
const searchKeyword = ref("");
/** 类型筛选："全部" / "进行中" / "已递交"
 *  取值要和后端的分组对上（backend/cit_api/dao/message_dao.py 的 STATUS_GROUP_*） */
const STATUS_FILTERS = [
  { value: "", label: "全部" },
  { value: "in_progress", label: "进行中" },
  { value: "submitted", label: "已递交" },
];
const statusFilter = ref("");
let pollTimer = null;

/** 已读记录：{ task_id: ISO 时间 } */
const lastSeenMap = ref(loadLastSeen());

function loadLastSeen() {
  try {
    return JSON.parse(localStorage.getItem(LAST_SEEN_KEY) || "{}");
  } catch {
    return {};
  }
}

function markSeen(taskId) {
  if (!taskId) return;
  lastSeenMap.value = {
    ...lastSeenMap.value,
    [taskId]: new Date().toISOString(),
  };
  try {
    localStorage.setItem(LAST_SEEN_KEY, JSON.stringify(lastSeenMap.value));
  } catch {
    /* ignore */
  }
}

/** 任务最后活动时间：updated_at 与消息/留言时间的最大值（用于未读判断） */
function lastActivity(task) {
  let latest = String(task.updated_at || task.created_at || "");
  for (const m of task.messages || []) {
    if (m.created_at && String(m.created_at) > latest) latest = String(m.created_at);
  }
  for (const c of task.comments || []) {
    if (c.created_at && String(c.created_at) > latest) latest = String(c.created_at);
  }
  return latest;
}

/** 卡片展示的时间：最新一条消息的时间（与后端排序键一致，无消息退回更新时间/创建时间） */
function cardTime(task) {
  let latest = "";
  for (const m of task.messages || []) {
    if (m.created_at && String(m.created_at) > latest) latest = String(m.created_at);
  }
  return latest || task.updated_at || task.created_at || "";
}

function isUnread(task) {
  const latest = lastActivity(task);
  if (!latest) return false;
  const seen = lastSeenMap.value[task.task_id];
  if (!seen) return true;
  return latest > seen;
}

/** 本地搜索过滤（客户公司 / 保险公司 / 任务号） */
const filteredTasks = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase();
  if (!kw) return tasks.value;
  return tasks.value.filter((t) => {
    const searchable = [
      t.task_id,
      t.customer_company,
      t.insurance_company,
      t.creator,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return searchable.includes(kw);
  });
});

const pageCount = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE))
);

const hasNextPage = computed(() => tasks.value.length >= PAGE_SIZE);

function badgeStyle(status) {
  const s = statusInfo(status);
  return { color: s.fg, background: s.bg };
}

/** 左侧 3px 指示条：仅选中时显示金色，默认无颜色 */
function indicatorStyle(task) {
  if (selectedTaskId.value === task.task_id) {
    return { background: "var(--accent)" };
  }
  return { background: "transparent" };
}

/** 加载当前页 */
async function loadHistory() {
  const skip = currentPage.value * PAGE_SIZE;
  try {
    if (store.user) {
      tasks.value = await listMyChatTasks(
        store.user.id,
        skip,
        PAGE_SIZE,
        statusFilter.value
      );
    } else {
      // 兜底列表接口不支持分组，此时类型筛选不生效
      tasks.value = await listChatTasks(skip, PAGE_SIZE);
    }
  } catch (e) {
    console.error("加载任务列表失败:", e);
    tasks.value = [];
  }
  // 总数估算（后端无 count 接口）
  totalCount.value =
    tasks.value.length < PAGE_SIZE
      ? skip + tasks.value.length
      : skip + tasks.value.length + 1;
}

/** 切换类型筛选：回到第 1 页再拉
 *  筛选在后端做，第 1 页是必须的 —— 否则原来的页码可能落在新结果集之外，看着像"没数据" */
function setStatusFilter(value) {
  if (statusFilter.value === value) return;
  statusFilter.value = value;
  currentPage.value = 0;
  loadHistory();
}

function onPrevPage() {
  if (currentPage.value > 0) {
    currentPage.value -= 1;
    loadHistory();
  }
}

function onNextPage() {
  if (tasks.value.length >= PAGE_SIZE) {
    currentPage.value += 1;
    loadHistory();
  }
}

function onCardClick(task) {
  selectedTaskId.value = task.task_id;
  markSeen(task.task_id);
  emit("item-click", task);
}

/** 静默刷新：保留页码与选中任务（轮询 / 手动刷新） */
function refresh() {
  loadHistory();
}

/** 新建任务后刷新：回到第 1 页（新任务在最前） */
function resetAndRefresh() {
  currentPage.value = 0;
  selectedTaskId.value = "";
  loadHistory();
}

onMounted(() => {
  loadHistory();
  pollTimer = setInterval(refresh, POLL_INTERVAL);
});

onUnmounted(() => clearInterval(pollTimer));

defineExpose({ refresh, resetAndRefresh, markSeen });
</script>

<style scoped>
.history-panel {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
}

/* ── 标题行（含用户信息插槽） ── */
.title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 8px 8px 6px 10px;
}
.title {
  font-size: 15px;
  font-weight: bold;
  color: var(--primary);
  letter-spacing: 0.5px;
  flex: none;
}

/* ── 搜索行 ── */
.search-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px 6px 8px;
}
.search-box {
  position: relative;
  flex: 1;
  min-width: 0;
}
.search-box input {
  width: 100%;
  height: 28px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 0 24px 0 10px;
  font-size: 12px;
  outline: none;
  background: #fff;
}
.search-box input:focus {
  border-color: var(--primary);
}
.search-clear {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
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
.search-clear:hover {
  background: #b8bcc4;
}
.refresh-btn {
  width: 28px;
  height: 28px;
  flex: none;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 6px;
  font-size: 16px;
  font-weight: bold;
  line-height: 1;
}
.refresh-btn:hover {
  background: #d6eaff;
}
.refresh-btn:active {
  background: #91caff;
  color: var(--primary-active);
}

/* ── 类型筛选（按钮式） ── */
.filter-row {
  display: flex;
  gap: 6px;
  padding: 0 8px 6px 8px;
}
.filter-btn {
  flex: 1;
  height: 24px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1;
}
.filter-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.filter-btn.on {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

/* ── 卡片列表 ── */
.scroll-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 6px 8px;
}

.policy-card {
  display: flex;
  background: var(--bg-card);
  border-radius: 10px;
  cursor: pointer;
  overflow: hidden;
  transition: background 0.12s;
}
.policy-card:hover {
  background: var(--bg-hover);
}
.policy-card.selected {
  background: #e3efff;
  box-shadow: inset 0 0 0 1.5px rgba(22, 119, 255, 0.45);
}
.policy-card.selected .card-title {
  color: var(--primary);
}
.policy-card.selected .card-row2,
.policy-card.selected .card-row3 {
  color: #4b5563;
}
.indicator {
  width: 4px;
  flex-shrink: 0;
  border-radius: 2px;
}
.card-content {
  flex: 1;
  min-width: 0;
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.card-row1 {
  display: flex;
  align-items: center;
  gap: 6px;
}
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  flex: none;
}
.card-title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-title.unread {
  font-weight: 700;
}
.status-badge {
  flex: none;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  padding: 2px 8px;
  min-width: 54px;
  text-align: center;
  line-height: 19px;
}

.card-row2 {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-row3 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
.msg-count {
  flex: none;
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  padding: 24px 0;
}

/* ── 分页 ── */
.page-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-top: 1px solid var(--border);
}
.page-btn {
  width: 26px;
  height: 22px;
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 10px;
}
.page-btn:hover:not(:disabled) {
  color: var(--primary);
  border-color: var(--primary);
}
.page-btn:disabled {
  color: #ccc;
  border-color: #eee;
  cursor: not-allowed;
}
.page-label {
  flex: 1;
  text-align: center;
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
