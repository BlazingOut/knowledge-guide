// 星航日志桌面壳：前端为纯静态 Vite + React 应用，无需任何自定义 IPC 命令，
// Tauri 在这里只负责提供原生窗口、WebView 容器和自动更新能力。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .run(tauri::generate_context!())
        .expect("failed to run 星航日志");
}
