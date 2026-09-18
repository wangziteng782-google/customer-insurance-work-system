<template>
  <div ref="rootEl" class="user-menu">
    <button class="user-info" :class="{ open }" @click.stop="toggle">
      <span class="user-meta">
        <span class="user-name">{{ displayName }}</span>
        <span class="user-role">{{ roleText }}</span>
      </span>
      <span class="user-status" title="在线"></span>
      <svg
        class="user-chevron"
        :class="{ flipped: open }"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <div v-if="open" class="user-dropdown">
      <div class="dropdown-header">
        <div class="dropdown-name">{{ displayName }}</div>
        <div class="dropdown-sub">{{ roleText }}</div>
      </div>
      <div class="dropdown-divider"></div>
      <div class="dropdown-item" @click="onChangePassword">修改密码</div>
      <div class="dropdown-item dropdown-danger" @click="onLogout">
        退出登录
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { roleLabel } from "../constants";

const props = defineProps({
  user: { type: Object, required: true },
});
const emit = defineEmits(["change-password", "logout"]);

const open = ref(false);
const rootEl = ref(null);

const displayName = computed(
  () => props.user.display_name || props.user.username || "未登录"
);
const roleText = computed(() => roleLabel(props.user.role));

function toggle() {
  open.value = !open.value;
}

function close() {
  open.value = false;
}

function onChangePassword() {
  close();
  emit("change-password");
}

function onLogout() {
  close();
  emit("logout");
}

function onDocumentClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) close();
}

function onKeydown(e) {
  if (e.key === "Escape") close();
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<style scoped>
.user-menu {
  position: relative;
}

/* ── 用户信息块 ── */
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border-radius: 8px;
  transition: background 0.15s;
}
.user-info:hover,
.user-info.open {
  background: var(--bg-hover);
}
.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 0;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
  white-space: nowrap;
}
.user-role {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  line-height: 1.2;
  white-space: nowrap;
}
.user-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #52c41a;
  flex: none;
  box-shadow: 0 0 0 2px #fff;
}
.user-chevron {
  width: 14px;
  height: 14px;
  color: #999;
  margin-left: 2px;
  transition: transform 0.2s;
}
.user-chevron.flipped {
  transform: rotate(180deg);
}

/* ── 下拉菜单 ── */
.user-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 170px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 500;
}
.dropdown-header {
  padding: 8px 12px 6px;
}
.dropdown-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.dropdown-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.dropdown-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}
.dropdown-item {
  padding: 8px 12px;
  font-size: 13px;
  color: #333;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}
.dropdown-item:hover {
  background: #f5f5f5;
}
.dropdown-danger {
  color: #ff4d4f;
}
.dropdown-danger:hover {
  background: #fff2f0;
}
</style>
