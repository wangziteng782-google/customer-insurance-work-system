<template>
  <div class="chat-message" :class="{ handler: isHandler }">
    <div class="wrap">
      <div class="bubble" @contextmenu.prevent="onContextMenu">
        <!-- 内勤留言标签 -->
        <div v-if="isHandler" class="handler-tag">内勤留言</div>

        <!-- 文字 -->
        <div v-if="content" class="text">{{ content }}</div>

        <!-- 图片网格（仅用户消息） -->
        <div
          v-if="!isHandler && imagePaths.length"
          class="img-grid"
          :class="{ single: imagePaths.length === 1 }"
        >
          <div
            v-for="(p, i) in imagePaths.slice(0, 4)"
            :key="i"
            class="img-cell"
            @click="$emit('view-image', imagePaths, i)"
          >
            <img :src="toUrl(p)" loading="lazy" alt="图片" />
            <div v-if="i === 3 && imagePaths.length > 4" class="more-overlay">
              +{{ imagePaths.length - 4 }}
            </div>
          </div>
        </div>

        <!-- 文件列表（仅用户消息） -->
        <div v-if="!isHandler && docPaths.length" class="file-list">
          <button
            v-for="(p, i) in docPaths"
            :key="i"
            class="file-item"
            :title="baseName(p)"
            @click="openFile(p)"
          >
            <span class="file-icon">{{ fileIcon(p) }}</span>
            <span class="file-name">{{ baseName(p) }}</span>
            <span class="file-ext">{{ extTag(p) }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 右键菜单：复制文本 / 撤回 -->
    <div
      v-if="menuVisible"
      class="ctx-menu"
      :style="{ left: menuX + 'px', top: menuY + 'px' }"
    >
      <div v-if="content" class="ctx-item" @click="copyText">复制文本</div>
      <div v-if="canRecall" class="ctx-item" @click="onRecall">撤回</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { toUrl } from "../api";
import { baseName, extOf, fileIcon, isImagePath } from "../constants";

const props = defineProps({
  content: { type: String, default: "" },
  filePaths: { type: Array, default: null },
  isHandler: { type: Boolean, default: false },
  // 能否撤回（自己发的 + 2 分钟内），由父组件判断后传入
  canRecall: { type: Boolean, default: false },
});

const emit = defineEmits(["view-image", "recall"]);

const imagePaths = computed(() =>
  (props.filePaths || []).filter((p) => isImagePath(p))
);
const docPaths = computed(() =>
  (props.filePaths || []).filter((p) => !isImagePath(p))
);

function extTag(path) {
  const e = extOf(path);
  return e ? e.slice(1).toUpperCase() : "文件";
}

function openFile(path) {
  window.open(toUrl(path), "_blank");
}

// ── 右键复制 ──
const menuVisible = ref(false);
const menuX = ref(0);
const menuY = ref(0);

function onContextMenu(e) {
  // 纯附件消息没有文本，但可能可以撤回，所以两者都不满足才不弹菜单
  if (!props.content && !props.canRecall) return;
  menuX.value = Math.min(e.clientX, window.innerWidth - 130);
  menuY.value = Math.min(e.clientY, window.innerHeight - 96);
  menuVisible.value = true;
}

function onRecall() {
  closeMenu();
  emit("recall");
}

function closeMenu() {
  menuVisible.value = false;
}

function copyText() {
  closeMenu();
  navigator.clipboard.writeText(props.content).catch(() => {
    const ta = document.createElement("textarea");
    ta.value = props.content;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  });
}

function onKeydown(e) {
  if (e.key === "Escape") closeMenu();
}

onMounted(() => {
  document.addEventListener("click", closeMenu);
  document.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", closeMenu);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<style scoped>
.chat-message {
  display: flex;
  width: 100%;
}
.chat-message:not(.handler) {
  justify-content: flex-end;
}
.chat-message.handler {
  justify-content: flex-start;
}

.wrap {
  display: flex;
  flex-direction: column;
  max-width: 520px;
  min-width: 0;
}
.chat-message:not(.handler) .wrap {
  align-items: flex-end;
}
.chat-message.handler .wrap {
  align-items: flex-start;
}

.bubble {
  max-width: 100%;
  border-radius: 12px 2px 12px 12px;
  padding: 10px 12px;
  user-select: text;
}
.chat-message:not(.handler) .bubble {
  background: var(--primary);
}
.chat-message.handler .bubble {
  background: #f0f0f0;
}

.text {
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-message:not(.handler) .text {
  color: #fff;
}
.chat-message.handler .text {
  color: var(--text-primary);
}

.handler-tag {
  font-size: 11px;
  color: #999;
  margin-bottom: 2px;
}

/* ── 图片网格 ── */
.img-grid {
  display: grid;
  grid-template-columns: repeat(2, 112px);
  gap: 4px;
  margin-top: 6px;
}
.img-grid.single {
  grid-template-columns: 150px;
}
.img-cell {
  position: relative;
  width: 100%;
  height: 112px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.12);
}
.img-grid.single .img-cell {
  height: 150px;
}
.img-cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s;
}
.img-cell:hover img {
  transform: scale(1.04);
}
.more-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── 文件列表 ── */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 260px;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 6px;
  text-align: left;
}
.file-item:hover {
  background: #fff;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.12);
}
.file-icon {
  flex: none;
  font-size: 14px;
}
.file-name {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-ext {
  flex: none;
  font-size: 10px;
  color: var(--primary);
  font-weight: 600;
}

/* ── 右键菜单 ── */
.ctx-menu {
  position: fixed;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 3000;
  min-width: 110px;
}
.ctx-item {
  padding: 6px 14px;
  font-size: 13px;
  color: var(--text-primary);
  border-radius: 4px;
  cursor: pointer;
}
.ctx-item:hover {
  background: var(--primary-light);
  color: var(--primary);
}
</style>
