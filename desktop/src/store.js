/**
 * 轻量全局状态（当前登录用户 + Toast）
 */
import { reactive } from "vue";

export const store = reactive({
  /** 当前登录用户 {id, username, display_name, role, token} */
  user: null,

  /** toast: {msg, type: 'success'|'error'|'info'} */
  toast: null,
});

let toastTimer = null;

export function showToast(msg, type = "info", duration = 2500) {
  store.toast = { msg, type };
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    store.toast = null;
  }, duration);
}
