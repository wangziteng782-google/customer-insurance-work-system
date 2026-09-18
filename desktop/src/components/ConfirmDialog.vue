<template>
  <div class="modal-mask">
    <div class="dialog">
      <h2 class="dialog-title">{{ title }}</h2>
      <p class="dialog-content">{{ content }}</p>
      <div class="btn-row">
        <button class="cancel-btn" @click="$emit('cancel')">取消</button>
        <button
          class="ok-btn"
          :class="{ danger }"
          @click="$emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "提示" },
  content: { type: String, default: "" },
  confirmText: { type: String, default: "确定" },
  danger: { type: Boolean, default: false },
});
defineEmits(["cancel", "confirm"]);
</script>

<style scoped>
.dialog {
  width: 320px;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
}
.dialog-title {
  font-size: 16px;
  color: var(--text-primary);
  margin-bottom: 10px;
}
.dialog-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
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
  min-width: 76px;
  padding: 0 12px;
  background: var(--primary);
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}
.ok-btn:hover {
  background: var(--primary-hover);
}
.ok-btn.danger {
  background: #ff4d4f;
}
.ok-btn.danger:hover {
  background: #ff7875;
}
</style>
