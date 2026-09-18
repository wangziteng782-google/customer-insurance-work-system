import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

// 阻止 WebView 把拖入的文件当作页面导航打开（全局兜底）
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

createApp(App).mount("#app");
