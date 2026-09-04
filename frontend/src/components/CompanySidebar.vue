<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { fetchTasks, extractInsuranceCompany, type ChatTask } from '../api';

const tasks = ref<ChatTask[]>([]);
const selectedCompany = ref<string | null>(null);
const keyword = ref('');
const loading = ref(false);

const emit = defineEmits<{
  select: [tasks: ChatTask[]];
}>();

// 按保险公司分组
const companies = computed(() => {
  const map = new Map<string, { name: string; tasks: ChatTask[] }>();
  for (const t of tasks.value) {
    const name = t.insurance_company || t.customer_company || '未分类';
    if (!map.has(name)) map.set(name, { name, tasks: [] });
    map.get(name)!.tasks.push(t);
  }
  return [...map.values()].sort((a, b) => b.tasks.length - a.tasks.length);
});

const filteredCompanies = computed(() => {
  if (!keyword.value) return companies.value;
  const k = keyword.value.toLowerCase();
  return companies.value.filter(c => c.name.toLowerCase().includes(k));
});

async function load() {
  loading.value = true;
  try {
    tasks.value = await fetchTasks(0, 200);
  } finally {
    loading.value = false;
  }
}

function selectCompany(c: { name: string; tasks: ChatTask[] }) {
  selectedCompany.value = c.name;
  emit('select', c.tasks);
}

onMounted(load);
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2 class="sidebar-title">保险公司</h2>
      <span class="sidebar-count">{{ companies.length }} 家</span>
    </div>

    <div class="sidebar-search">
      <input v-model="keyword" type="text" placeholder="搜索保险公司..." class="search-input" />
    </div>

    <div class="company-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div
        v-else
        v-for="company in filteredCompanies"
        :key="company.name"
        class="company-item"
        :class="{ active: selectedCompany === company.name }"
        @click="selectCompany(company)"
      >
        <div class="company-indicator"></div>
        <div class="company-info">
          <span class="company-name">{{ company.name }}</span>
          <span class="company-meta">
            {{ company.tasks.length }} 条 · {{ company.tasks[0].creator_name || company.tasks[0].creator || '-' }}
          </span>
        </div>
        <span class="company-badge">{{ company.tasks.length }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100%;
  background: #f7f8fa;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 16px 14px 8px;
}

.sidebar-title { font-size: 17px; font-weight: 700; color: var(--primary); margin: 0; }
.sidebar-count { font-size: 13px; color: var(--text-muted); }

.sidebar-search { padding: 0 10px 8px; }

.search-input {
  width: 100%; height: 34px; padding: 0 12px;
  border: 1px solid #e0e0e0; border-radius: 6px;
  font-size: 14px; background: #fff; outline: none;
}
.search-input:focus { border-color: var(--primary); }

.company-list { flex: 1; overflow-y: auto; padding: 0 6px 8px; }

.company-item {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 10px; border-radius: 8px;
  cursor: pointer; transition: background 0.15s;
}
.company-item:hover { background: #f0f1f3; }
.company-item.active { background: #f0f7ff; }

.company-indicator {
  width: 3px; height: 36px; border-radius: 2px;
  background: transparent; flex-shrink: 0;
}
.company-item.active .company-indicator { background: var(--accent); }

.company-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.company-name { font-size: 15px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.company-meta { font-size: 13px; color: var(--text-muted); }

.company-badge {
  font-size: 13px; font-weight: 600; color: var(--primary);
  background: var(--primary-light); padding: 3px 9px;
  border-radius: 10px; flex-shrink: 0;
}

.loading { text-align: center; padding: 20px; color: var(--text-muted); font-size: 14px; }
</style>
