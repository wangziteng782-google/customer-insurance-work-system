<script setup lang="ts">
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <img src="/logo.png" alt="logo" class="header-logo" />
      <h1 class="header-title">保险工单管理系统</h1>
    </header>
    <main class="app-main">
      <p>欢迎使用保险工单管理系统</p>
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background-color: #f5f5f5;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 12px;
  background-color: #fff;
  padding: 12px 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-logo {
  height: 36px;
  width: auto;
}

.header-title {
  font-size: 18px;
  font-weight: bold;
  color: #1a1a1a;
}

.app-main {
  padding: 24px;
}
</style>
