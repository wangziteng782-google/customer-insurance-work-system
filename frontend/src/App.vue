<script setup lang="ts">
import { ref, onMounted } from 'vue';
import CompanySidebar from './components/CompanySidebar.vue';
import ChatPanel from './components/ChatPanel.vue';
import SummaryPanel from './components/SummaryPanel.vue';
import type { ChatTask, ChatMessage } from './api';
import { fetchUsers, type AppUser } from './api';

const selectedTasks = ref<ChatTask[]>([]);
const allMessages = ref<ChatMessage[]>([]);
const users = ref<AppUser[]>([]);
const currentUser = ref<AppUser | null>(null);

function onSelect(tasks: ChatTask[]) {
  selectedTasks.value = tasks;
}

function onMessagesLoaded(msgs: ChatMessage[]) {
  allMessages.value = msgs;
}

function onUserSelect(userId: number) {
  const user = users.value.find(u => u.id === userId) || null;
  currentUser.value = user;
  if (user) localStorage.setItem('current_user_id', String(user.id));
}

onMounted(async () => {
  try {
    users.value = await fetchUsers();
    // 恢复上次选择
    const savedId = localStorage.getItem('current_user_id');
    if (savedId) {
      const user = users.value.find(u => u.id === Number(savedId));
      if (user) currentUser.value = user;
    }
    // 默认选中第一个
    if (!currentUser.value && users.value.length > 0) {
      currentUser.value = users.value[0];
    }
  } catch (e) {
    console.error('加载用户列表失败:', e);
  }
});
</script>

<template>
  <div class="app-layout">
    <!-- 顶栏 -->
    <header class="app-topbar">
      <div class="topbar-brand">
        <img src="/logo.png" class="topbar-logo" alt="logo" />
        <h1 class="topbar-title">保险工单管理系统</h1>
      </div>
      <div class="topbar-info">
        <select
          class="user-select"
          :value="currentUser?.id || ''"
          @change="onUserSelect(Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-if="!users.length" value="">加载中...</option>
          <option v-for="u in users" :key="u.id" :value="u.id">
            {{ u.display_name || u.username }}
          </option>
        </select>
        <span class="topbar-date">{{ new Date().toLocaleDateString('zh-CN') }}</span>
      </div>
    </header>

    <!-- 三栏主体 -->
    <main class="app-body">
      <CompanySidebar @select="onSelect" />
      <ChatPanel :tasks="selectedTasks" @messages-loaded="onMessagesLoaded" />
      <SummaryPanel :tasks="selectedTasks" :messages="allMessages" />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.topbar-brand { display: flex; align-items: center; gap: 10px; }

.topbar-logo {
  width: 32px; height: 32px;
  object-fit: contain;
}

.topbar-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.topbar-info { display: flex; align-items: center; gap: 12px; }
.user-select {
  height: 28px;
  padding: 0 8px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 13px;
  color: #3a3a4a;
  background: #fff;
  cursor: pointer;
  outline: none;
}
.user-select:focus { border-color: #1677ff; }
.topbar-date { font-size: 12px; color: var(--text-muted); }

.app-body { flex: 1; display: flex; overflow: hidden; }
</style>
