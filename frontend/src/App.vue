<script setup lang="ts">
import { ref } from 'vue';
import CompanySidebar from './components/CompanySidebar.vue';
import ChatPanel from './components/ChatPanel.vue';
import SummaryPanel from './components/SummaryPanel.vue';
import type { ChatTask, ChatMessage } from './api';

const selectedTasks = ref<ChatTask[]>([]);
const allMessages = ref<ChatMessage[]>([]);

function onSelect(tasks: ChatTask[]) {
  selectedTasks.value = tasks;
}

function onMessagesLoaded(msgs: ChatMessage[]) {
  allMessages.value = msgs;
}
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
.topbar-date { font-size: 12px; color: var(--text-muted); }

.app-body { flex: 1; display: flex; overflow: hidden; }
</style>
