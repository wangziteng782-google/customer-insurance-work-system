<template>
  <div class="login-page">
    <!-- 背景装饰（复刻 PySide 装饰圆/方块） -->
    <div class="decor circle c1"></div>
    <div class="decor circle c2"></div>
    <div class="decor circle c3"></div>
    <div class="decor rounded r1"></div>
    <div class="decor rounded r2"></div>
    <div class="decor circle c4"></div>

    <!-- 登录卡片 -->
    <div class="card">
      <div class="top-bar"></div>
      <h1 class="title">易梯保险系统</h1>
      <p class="subtitle">请登录以继续</p>

      <form @submit.prevent="onLogin">
        <label class="field-label">手机号</label>
        <input
          v-model.trim="phone"
          type="text"
          placeholder="请输入手机号"
          autocomplete="username"
        />

        <label class="field-label">密码</label>
        <input
          v-model="password"
          type="password"
          placeholder="请输入密码"
          autocomplete="current-password"
        />

        <p class="error" :class="{ visible: !!error }">{{ error }}</p>

        <button class="login-btn" type="submit" :disabled="loading">
          {{ loading ? "登录中..." : "登 录" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { login } from "../api";

const emit = defineEmits(["login-success"]);

const phone = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function onLogin() {
  if (!phone.value || !password.value) {
    error.value = "请输入手机号和密码";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const user = await login(phone.value, password.value);
    emit("login-success", user);
  } catch (e) {
    error.value = e.message.includes("手机号或密码")
      ? "手机号或密码错误"
      : `登录失败: ${e.message}`;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* ── 背景装饰 ── */
.decor {
  position: absolute;
  pointer-events: none;
}
.circle {
  border-radius: 50%;
}
.c1 {
  left: -50px;
  top: -80px;
  width: 220px;
  height: 220px;
  background: #e8f4ff;
}
.c2 {
  right: 80px;
  bottom: 60px;
  width: 180px;
  height: 180px;
  background: #e8f4ff;
}
.c3 {
  left: -30px;
  bottom: 100px;
  width: 100px;
  height: 100px;
  background: #f0f0f0;
}
.c4 {
  right: 50px;
  top: 100px;
  width: 50px;
  height: 50px;
  background: #f5f5f5;
}
.rounded {
  border-radius: 20px;
}
.r1 {
  right: -40px;
  top: -40px;
  width: 120px;
  height: 120px;
  background: #f0f7ff;
  border-radius: 20px;
}
.r2 {
  left: 60px;
  top: 200px;
  width: 60px;
  height: 60px;
  background: #e8f4ff;
  border-radius: 12px;
}

/* ── 登录卡片 ── */
.card {
  position: relative;
  width: 360px;
  height: 380px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  padding: 36px 36px 32px;
  overflow: hidden;
}
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--primary);
}
.title {
  font-size: 22px;
  font-weight: bold;
  color: var(--text-primary);
  text-align: center;
}
.subtitle {
  font-size: 13px;
  color: #999;
  text-align: center;
  margin: 4px 0 18px;
}
.field-label {
  display: block;
  font-size: 13px;
  color: #3a3a4a;
  font-weight: 500;
  margin-bottom: 6px;
}
input {
  width: 100%;
  height: 40px;
  border: 1.5px solid #d9d9d9;
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: #fafafa;
  outline: none;
  margin-bottom: 14px;
  transition: border-color 0.15s, background 0.15s;
}
input:focus {
  border-color: var(--primary);
  background: #fff;
}
.error {
  min-height: 18px;
  font-size: 12px;
  color: #ff4d4f;
  text-align: center;
  margin-bottom: 6px;
  opacity: 0;
}
.error.visible {
  opacity: 1;
}
.login-btn {
  width: 100%;
  height: 42px;
  background: var(--primary);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  transition: background 0.15s;
}
.login-btn:hover {
  background: var(--primary-hover);
}
.login-btn:active {
  background: var(--primary-active);
}
.login-btn:disabled {
  background: #91caff;
  cursor: not-allowed;
}
</style>
