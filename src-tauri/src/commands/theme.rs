//! src-tauri 命令 · theme / i18n (M5.6 · 接 splicr-i18n)
//!
//! - i18n_get_locale: 当前后端文案语言
//! - i18n_set_locale: 切换后端文案语言 (宽松解析 "en-US"/"en_us";成功后 emit `app:locale_changed`)
//! - i18n_translate: 查文案 (支持 `{name}` 插值;fallback 链:当前 → zh-CN → key 原样)
//!
//! 前端 UI 文案走 i18next,本组命令服务"后端文案与前端语言保持一致"的场景
//! (错误 toast / 事件消息的语言跟随)。`Translator::with_backend_defaults()`
//! 在 lib.rs 中 `.manage()` 注入。

use std::collections::HashMap;

use tauri::{AppHandle, Emitter, State};
use splicr_core::Translator;

/// 当前后端文案语言 (BCP-47,如 "zh-CN")
#[tauri::command]
pub async fn i18n_get_locale(tr: State<'_, Translator>) -> Result<String, String> {
    Ok(tr.locale().as_str().to_owned())
}

/// 切换后端文案语言。无法识别时返回 false 并保持现状。
#[tauri::command]
pub async fn i18n_set_locale(
    app: AppHandle,
    tr: State<'_, Translator>,
    locale: String,
) -> Result<bool, String> {
    let ok = tr.try_set_locale(&locale);
    if ok {
        // 与前端 useLocale / theme store 联动的既有事件契约
        let _ = app.emit(
            "app:locale_changed",
            serde_json::json!({ "locale": tr.locale().as_str() }),
        );
    }
    Ok(ok)
}

/// 查文案。args 为 `{name}` 插值表,可缺省。
#[tauri::command]
pub async fn i18n_translate(
    tr: State<'_, Translator>,
    key: String,
    args: Option<HashMap<String, String>>,
) -> Result<String, String> {
    let Some(args) = args else {
        return Ok(tr.t(&key));
    };
    // 稳定输出:按 key 字典序插值,避免 HashMap 迭代顺序影响
    let mut pairs: Vec<(&str, &str)> = args.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect();
    pairs.sort_unstable_by(|a, b| a.0.cmp(b.0));
    Ok(tr.t_with_args(&key, &pairs))
}
