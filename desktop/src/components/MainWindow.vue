<template>
  <div class="main-window">
    <div class="content">
      <!-- 左栏：保单列表（标题行右侧内嵌用户信息） -->
      <HistoryPanel
        ref="historyRef"
        @item-click="onHistoryItemClick"
      >
        <template #user>
          <UserMenu
            :user="user"
            @change-password="showChangePwd = true"
            @logout="confirmLogout = true"
          />
        </template>
      </HistoryPanel>

      <!-- 右栏：聊天面板 -->
      <ChatPanel
        ref="chatRef"
        @task-created="onTaskCreated"
        @task-changed="onTaskChanged"
      />
    </div>

    <!-- 修改密码对话框 -->
    <ChangePasswordDialog
      v-if="showChangePwd"
      @close="showChangePwd = false"
      @submit="onChangePassword"
    />

    <!-- 退出登录确认 -->
    <ConfirmDialog
      v-if="confirmLogout"
      title="退出登录"
      :content="`确定要退出「${displayName}」的登录吗？未发送的内容将丢失。`"
      confirm-text="退出登录"
      danger
      @cancel="confirmLogout = false"
      @confirm="doLogout"
    />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import HistoryPanel from "./HistoryPanel.vue";
import ChatPanel from "./ChatPanel.vue";
import ChangePasswordDialog from "./ChangePasswordDialog.vue";
import ConfirmDialog from "./ConfirmDialog.vue";
import UserMenu from "./UserMenu.vue";
import { changePassword } from "../api";
import { showToast } from "../store";

const props = defineProps({ user: { type: Object, required: true } });
const emit = defineEmits(["logout"]);

const historyRef = ref(null);
const chatRef = ref(null);
const showChangePwd = ref(false);
const confirmLogout = ref(false);

const displayName = computed(
  () => props.user.display_name || props.user.username || "未登录"
);

/** 历史记录点击 — 切换到对应任务 */
function onHistoryItemClick(task) {
  chatRef.value?.setCurrentTask(task);
}

/** 新任务创建 — 回第 1 页刷新列表，并标记为已读 */
function onTaskCreated(taskId) {
  if (taskId) historyRef.value?.markSeen(taskId);
  historyRef.value?.resetAndRefresh();
}

/** 消息被撤回 — 静默刷新左侧列表（保留选中与页码） */
function onTaskChanged() {
  historyRef.value?.refresh();
}

/** 修改密码 */
async function onChangePassword({ oldPwd, newPwd }) {
  try {
    await changePassword(props.user.id, oldPwd, newPwd);
    showChangePwd.value = false;
    showToast("密码已修改", "success");
  } catch (e) {
    showToast(`失败: ${e.message}`, "error");
  }
}

/** 退出登录（token 由 App 统一清理） */
function doLogout() {
  confirmLogout.value = false;
  emit("logout");
}
</script>

<style scoped>
.main-window {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.content {
  flex: 1;
  display: flex;
  min-height: 0;
}
</style>
