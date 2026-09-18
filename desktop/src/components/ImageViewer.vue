<template>
  <div class="image-viewer" @click="$emit('close')">
    <div class="viewer-body" @click.stop>
      <div v-if="!loaded" class="viewer-status">加载中...</div>
      <div v-else-if="failed" class="viewer-status">加载失败</div>
      <img
        v-show="loaded && !failed"
        :src="currentUrl"
        alt="图片"
        @load="loaded = true"
        @error="onError"
      />
    </div>

    <!-- 顶部工具条 -->
    <div class="toolbar" @click.stop>
      <span v-if="urls.length > 1" class="counter">
        {{ index + 1 }} / {{ urls.length }}
      </span>
      <button class="tool-btn" title="在新窗口打开" @click="openInNewTab">
        新窗口打开
      </button>
      <button class="tool-btn" title="关闭 (Esc)" @click="$emit('close')">✕</button>
    </div>

    <!-- 左右切换 -->
    <button
      v-if="urls.length > 1"
      class="nav-btn prev"
      title="上一张 (←)"
      @click.stop="prev"
    >
      ‹
    </button>
    <button
      v-if="urls.length > 1"
      class="nav-btn next"
      title="下一张 (→)"
      @click.stop="next"
    >
      ›
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  urls: { type: Array, required: true },
  index: { type: Number, default: 0 },
});
const emit = defineEmits(["close"]);

const idx = ref(props.index);
const loaded = ref(false);
const failed = ref(false);

const currentUrl = computed(() => props.urls[idx.value] || "");

watch(currentUrl, () => {
  loaded.value = false;
  failed.value = false;
});

function onError() {
  loaded.value = true;
  failed.value = true;
}

function prev() {
  idx.value = (idx.value - 1 + props.urls.length) % props.urls.length;
}

function next() {
  idx.value = (idx.value + 1) % props.urls.length;
}

function openInNewTab() {
  window.open(currentUrl.value, "_blank");
}

function onKeydown(e) {
  if (e.key === "Escape") emit("close");
  else if (e.key === "ArrowLeft") prev();
  else if (e.key === "ArrowRight") next();
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<style scoped>
.image-viewer {
  position: fixed;
  inset: 0;
  background: #2a2a2a;
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
}
.viewer-body {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 20px;
}
img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.viewer-status {
  color: #999;
  font-size: 14px;
}

.toolbar {
  position: absolute;
  top: 12px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.counter {
  color: #ddd;
  font-size: 12px;
  margin-right: 4px;
}
.tool-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 12px;
}
.tool-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 42px;
  height: 64px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 28px;
  line-height: 1;
}
.nav-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}
.nav-btn.prev {
  left: 14px;
}
.nav-btn.next {
  right: 14px;
}
</style>
