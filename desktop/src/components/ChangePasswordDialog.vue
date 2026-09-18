<template>
  <div class="modal-mask">
    <div class="dialog">
      <div class="dialog-head">
        <h2 class="dialog-title">修改密码</h2>
        <button class="close-btn" title="关闭" @click="$emit('close')">×</button>
      </div>

      <label class="field-label">旧密码</label>
      <input
        v-model="oldPwd"
        type="password"
        autocomplete="current-password"
        @keydown.enter="onSubmit"
      />

      <label class="field-label">新密码</label>
      <input
        v-model="newPwd"
        type="password"
        autocomplete="new-password"
        @keydown.enter="onSubmit"
      />

      <label class="field-label">确认新密码</label>
      <input
        v-model="confirmPwd"
        type="password"
        autocomplete="new-password"
        @keydown.enter="onSubmit"
      />

      <p class="error" :class="{ visible: !!error }">{{ error }}</p>

      <div class="btn-row">
        <button class="cancel-btn" @click="$emit('close')">取消</button>
        <button class="ok-btn" @click="onSubmit">确认修改</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const emit = defineEmits(["close", "submit"]);

const oldPwd = ref("");
const newPwd = ref("");
const confirmPwd = ref("");
const error = ref("");

function onSubmit() {
  if (!oldPwd.value.trim() || !newPwd.value.trim() || !confirmPwd.value.trim()) {
    error.value = "请填写所有字段";
    return;
  }
  if (newPwd.value.trim() !== confirmPwd.value.trim()) {
    error.value = "两次输入的新密码不一致";
    return;
  }
  emit("submit", {
    oldPwd: oldPwd.value.trim(),
    newPwd: newPwd.value.trim(),
  });
}

function onKeydown(e) {
  if (e.key === "Escape") emit("close");
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<style scoped>
.dialog {
  width: 320px;
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px 24px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
}
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.dialog-title {
  font-size: 16px;
  color: var(--text-primary);
}
.close-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.close-btn:hover {
  background: #f0f0f0;
  color: var(--text-primary);
}

.field-label {
  display: block;
  font-size: 13px;
  color: #3a3a4a;
  margin-bottom: 6px;
}
input {
  width: 100%;
  height: 36px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  margin-bottom: 10px;
}
input:focus {
  border-color: var(--primary);
}
.error {
  min-height: 18px;
  font-size: 12px;
  color: #ff4d4f;
  margin-bottom: 8px;
  opacity: 0;
}
.error.visible {
  opacity: 1;
}
.btn-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.cancel-btn {
  width: 70px;
  height: 32px;
  background: #f5f5f5;
  color: var(--text-secondary);
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 13px;
}
.cancel-btn:hover {
  border-color: #b8bcc4;
}
.ok-btn {
  height: 32px;
  padding: 0 16px;
  background: var(--primary);
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}
.ok-btn:hover {
  background: var(--primary-hover);
}
</style>
