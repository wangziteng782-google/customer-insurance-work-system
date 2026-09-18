/// 易梯保险系统 — Tauri 桌面客户端
///
/// 全部业务逻辑（登录、保单列表、聊天、上传）都在 Vue3 前端中通过
/// HTTP 调用后端接口完成，与 PySide6 版 client 完全一致，
/// 后端无需任何改动。Rust 侧仅承载 WebView 窗口。
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
