<template>
  <LoginPage v-if="!store.user" @login-success="onLoginSuccess" />
  <MainWindow v-else :user="store.user" @logout="onLogout" />

  <!-- 全局 Toast -->
  <div v-if="store.toast" class="toast" :class="store.toast.type">
    {{ store.toast.msg }}
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import LoginPage from "./components/LoginPage.vue";
import MainWindow from "./components/MainWindow.vue";
import { store, showToast } from "./store";
import { clearToken, setOnUnauthorized } from "./api";

/** 安全修改窗口标题（纯浏览器调试环境下不生效但不报错） */
function setWindowTitle(title) {
  try {
    import("@tauri-apps/api/window").then(({ getCurrentWindow }) =>
      getCurrentWindow().setTitle(title).catch(() => {})
    );
  } catch {
    /* 非 Tauri 环境 */
  }
}

function onLoginSuccess(user) {
  store.user = user;
  // 对齐 PySide：登录后窗口标题变为「客服工单录入 — 用户名」
  setWindowTitle(`客服保单录入 — ${user.display_name || user.username || ""}`);
}

function onLogout() {
  clearToken(); // 清除本地 token，下次需重新登录
  store.user = null;
  setWindowTitle("易梯保险系统");
  showToast("已退出登录", "success");
}

onMounted(() => {
  // 任意接口返回 401：清 token 并回到登录页
  setOnUnauthorized(() => {
    store.user = null;
    setWindowTitle("易梯保险系统");
  });
});
</script>

<style scoped></style>
