//! src-tauri 命令 · help (M5.7 · 接 scenefab-help)
//!
//! - help_topics: 全量主题列表 (可按分类过滤)
//! - help_topic_get: 按 id 取单篇主题 (含 markdown 正文)
//! - help_search: 加权全文搜索 (标题/关键词权重高于正文)
//!
//! `HelpRegistry::with_defaults()` 在 lib.rs 中 `.manage()` 注入,
//! 内置 6 篇默认主题与前端 HelpPage 卡片对应。

use scenefab_help::{HelpCategory, HelpRegistry, HelpTopic, SearchHit};
use tauri::State;

/// 全量主题列表。category 非空时按分类过滤 (kebab-case,非法分类返回错误)。
#[tauri::command]
pub async fn help_topics(
    reg: State<'_, HelpRegistry>,
    category: Option<String>,
) -> Result<Vec<HelpTopic>, String> {
    let topics = match category {
        Some(raw) if !raw.trim().is_empty() => {
            let cat = HelpCategory::parse(&raw).ok_or_else(|| format!("未知帮助分类: {raw}"))?;
            reg.list_by_category(cat)
        }
        _ => reg.list_all(),
    };
    Ok(topics.into_iter().cloned().collect())
}

/// 按 id 取单篇主题 (含 markdown 正文);不存在返回错误
#[tauri::command]
pub async fn help_topic_get(reg: State<'_, HelpRegistry>, id: String) -> Result<HelpTopic, String> {
    reg.get(&id).cloned().map_err(|e| e.to_string())
}

/// 加权全文搜索。空查询返回空列表;按得分降序、同分按 id 升序。
#[tauri::command]
pub async fn help_search(
    reg: State<'_, HelpRegistry>,
    query: String,
) -> Result<Vec<SearchHit>, String> {
    Ok(reg.search(&query))
}
