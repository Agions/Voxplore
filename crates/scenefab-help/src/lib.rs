//! scenefab-help v3.0 · 帮助系统 (M5.7 实装)
//!
//! ## 责任范围
//! 内置帮助主题的注册 / 查询 / 全文搜索。前端 HelpPage 的文档卡片、
//! 命令面板 "?" 搜索、错误页"查看帮助"跳转均消费本 crate。
//!
//! ## 设计
//! - [`HelpTopic`][]:一篇帮助文档 (markdown 正文 + 分类 + 关键词 + 关联主题)
//! - [`HelpRegistry`][]:内存注册表,支持
//!   - [`HelpRegistry::register`] 代码内注册
//!   - [`HelpRegistry::register_markdown`] 从带 frontmatter 的 markdown 文本注册
//!   - [`HelpRegistry::search`] 加权全文搜索 (标题/关键词权重高于正文)
//! - 零新外部依赖:frontmatter 用轻量行解析器,不引入 pulldown-cmark
//!   (正文保持 markdown 原文,渲染交给前端)
//!
//! ## frontmatter 格式
//! ```text
//! ---
//! id: quick-start
//! title: 快速上手
//! category: guide
//! summary: 5 分钟了解 5 步流水线
//! keywords: 入门, 流水线, 概念
//! related: ai-video, cli-reference
//! ---
//! 正文 markdown...
//! ```

use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use thiserror::Error;

// ════════════════════════════════════════════════════════════════════════
// 错误类型
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error)]
pub enum HelpError {
    /// markdown frontmatter 缺失或格式错误
    #[error("help markdown parse error: {0}")]
    Parse(String),
    /// 主题 id 已存在
    #[error("help topic id duplicated: {0}")]
    Duplicated(String),
    /// 主题不存在
    #[error("help topic not found: {0}")]
    NotFound(String),
}

// ════════════════════════════════════════════════════════════════════════
// 主题模型
// ════════════════════════════════════════════════════════════════════════

/// 帮助主题分类
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum HelpCategory {
    /// 使用指南 / 教程
    Guide,
    /// 故障排查
    Troubleshooting,
    /// 快捷键
    Shortcut,
    /// 常见问题
    Faq,
    /// 参考 (CLI / API 字段说明)
    Reference,
}

impl HelpCategory {
    /// 宽松解析 (kebab-case,大小写不敏感)
    pub fn parse(raw: &str) -> Option<Self> {
        match raw.trim().to_ascii_lowercase().as_str() {
            "guide" => Some(Self::Guide),
            "troubleshooting" => Some(Self::Troubleshooting),
            "shortcut" => Some(Self::Shortcut),
            "faq" => Some(Self::Faq),
            "reference" => Some(Self::Reference),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Guide => "guide",
            Self::Troubleshooting => "troubleshooting",
            Self::Shortcut => "shortcut",
            Self::Faq => "faq",
            Self::Reference => "reference",
        }
    }
}

/// 一篇帮助文档
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HelpTopic {
    /// 唯一标识 (kebab-case,如 "quick-start")
    pub id: String,
    pub category: HelpCategory,
    pub title: String,
    /// 一句话摘要 (卡片副标题用)
    pub summary: String,
    /// markdown 正文 (不含 frontmatter)
    pub content: String,
    /// 搜索关键词
    pub keywords: Vec<String>,
    /// 关联主题 id
    pub related: Vec<String>,
}

// ════════════════════════════════════════════════════════════════════════
// frontmatter 解析
// ════════════════════════════════════════════════════════════════════════

/// 从带 frontmatter 的 markdown 文本解析出 [`HelpTopic`]。
///
/// 必填字段:`id` / `title` / `category`;缺省字段:`summary` 空、
/// `keywords` / `related` 空列表。
pub fn parse_topic_markdown(md: &str) -> Result<HelpTopic, HelpError> {
    let md = md.trim_start_matches('\u{feff}');
    let body = md
        .strip_prefix("---")
        .ok_or_else(|| HelpError::Parse("missing frontmatter opening '---'".to_owned()))?;
    let (head, rest) = body
        .split_once("\n---")
        .ok_or_else(|| HelpError::Parse("missing frontmatter closing '---'".to_owned()))?;

    let mut fields: HashMap<String, String> = HashMap::new();
    for line in head.lines() {
        let line = line.trim_end();
        if line.trim().is_empty() {
            continue;
        }
        let Some((k, v)) = line.split_once(':') else {
            return Err(HelpError::Parse(format!("bad frontmatter line: {line:?}")));
        };
        fields.insert(k.trim().to_owned(), v.trim().to_owned());
    }

    let mut take = |k: &str| -> Result<String, HelpError> {
        fields
            .remove(k)
            .filter(|v| !v.is_empty())
            .ok_or_else(|| HelpError::Parse(format!("missing required field: {k}")))
    };

    let id = take("id")?;
    let title = take("title")?;
    let category_raw = take("category")?;
    let category = HelpCategory::parse(&category_raw)
        .ok_or_else(|| HelpError::Parse(format!("unknown category: {category_raw:?}")))?;

    let split_list = |raw: Option<String>| -> Vec<String> {
        raw.map(|s| {
            s.split(',')
                .map(str::trim)
                .filter(|x| !x.is_empty())
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
    };

    // 正文:去掉 closing '---' 后的前导换行
    let content = rest
        .trim_start_matches('\r')
        .trim_start_matches('\n')
        .to_owned();

    Ok(HelpTopic {
        id,
        category,
        title,
        summary: fields.remove("summary").unwrap_or_default(),
        content,
        keywords: split_list(fields.remove("keywords")),
        related: split_list(fields.remove("related")),
    })
}

// ════════════════════════════════════════════════════════════════════════
// HelpRegistry · 注册表 + 搜索
// ════════════════════════════════════════════════════════════════════════

/// 搜索结果一项
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SearchHit {
    pub id: String,
    pub title: String,
    /// 加权得分 (越大越相关)
    pub score: u32,
}

/// 帮助主题注册表 (内存版,M5 范围;后续可从磁盘目录批量加载)
#[derive(Debug, Default)]
pub struct HelpRegistry {
    topics: HashMap<String, HelpTopic>,
}

// 搜索权重:标题/关键词命中远重于正文命中
const W_TITLE: u32 = 10;
const W_KEYWORD: u32 = 6;
const W_SUMMARY: u32 = 3;
const W_CONTENT: u32 = 1;

impl HelpRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// 注册一篇主题。id 重复返回错误 (不覆盖)。
    pub fn register(&mut self, topic: HelpTopic) -> Result<(), HelpError> {
        if self.topics.contains_key(&topic.id) {
            return Err(HelpError::Duplicated(topic.id));
        }
        self.topics.insert(topic.id.clone(), topic);
        Ok(())
    }

    /// 从 markdown frontmatter 文本注册
    pub fn register_markdown(&mut self, md: &str) -> Result<(), HelpError> {
        let topic = parse_topic_markdown(md)?;
        self.register(topic)
    }

    pub fn get(&self, id: &str) -> Result<&HelpTopic, HelpError> {
        self.topics
            .get(id)
            .ok_or_else(|| HelpError::NotFound(id.to_owned()))
    }

    pub fn contains(&self, id: &str) -> bool {
        self.topics.contains_key(id)
    }

    pub fn len(&self) -> usize {
        self.topics.len()
    }

    pub fn is_empty(&self) -> bool {
        self.topics.is_empty()
    }

    /// 全量主题 (按 id 排序,输出稳定)
    pub fn list_all(&self) -> Vec<&HelpTopic> {
        let mut v: Vec<&HelpTopic> = self.topics.values().collect();
        v.sort_by(|a, b| a.id.cmp(&b.id));
        v
    }

    /// 按分类过滤 (按 id 排序)
    pub fn list_by_category(&self, category: HelpCategory) -> Vec<&HelpTopic> {
        let mut v: Vec<&HelpTopic> = self
            .topics
            .values()
            .filter(|t| t.category == category)
            .collect();
        v.sort_by(|a, b| a.id.cmp(&b.id));
        v
    }

    /// 加权全文搜索。多词以空白拆分,每词独立计分求和。
    /// 大小写不敏感;空查询返回空列表;按得分降序、同分按 id 升序。
    pub fn search(&self, query: &str) -> Vec<SearchHit> {
        let terms: Vec<String> = query
            .split_whitespace()
            .map(|t| t.to_lowercase())
            .filter(|t| !t.is_empty())
            .collect();
        if terms.is_empty() {
            return vec![];
        }

        let mut hits: Vec<SearchHit> = self
            .topics
            .values()
            .filter_map(|t| {
                let score = terms
                    .iter()
                    .map(|term| Self::score_topic(t, term))
                    .sum::<u32>();
                (score > 0).then(|| SearchHit {
                    id: t.id.clone(),
                    title: t.title.clone(),
                    score,
                })
            })
            .collect();
        hits.sort_by(|a, b| b.score.cmp(&a.score).then(a.id.cmp(&b.id)));
        hits
    }

    fn score_topic(topic: &HelpTopic, term: &str) -> u32 {
        let mut score = 0;
        if topic.title.to_lowercase().contains(term) {
            score += W_TITLE;
        }
        if topic
            .keywords
            .iter()
            .any(|k| k.to_lowercase().contains(term))
        {
            score += W_KEYWORD;
        }
        if topic.summary.to_lowercase().contains(term) {
            score += W_SUMMARY;
        }
        if topic.content.to_lowercase().contains(term) {
            score += W_CONTENT;
        }
        score
    }

    /// 内置默认主题集 (与前端 HelpPage 6 张文档卡片一一对应)
    pub fn with_defaults() -> Self {
        let mut reg = Self::new();
        let defaults = [
            (
                "quick-start",
                HelpCategory::Guide,
                "快速上手",
                "5 分钟了解 5 步流水线的核心概念",
                "素材导入 场景拆分 脚本生成 配音字幕 导出发布",
            ),
            (
                "ai-video",
                HelpCategory::Guide,
                "AI 视频生成指南",
                "从脚本提示词到成片的最佳实践",
                "LLM 提示词 风格 情绪",
            ),
            (
                "cli-reference",
                HelpCategory::Reference,
                "CLI 参考",
                "命令行参数与配置文件字段",
                "命令 参数 app_config",
            ),
            (
                "python-api",
                HelpCategory::Reference,
                "Python API",
                "为高级用户提供的程序化控制",
                "脚本 自动化 批处理",
            ),
            (
                "troubleshooting",
                HelpCategory::Troubleshooting,
                "故障排查",
                "常见错误与解决方案",
                "错误 日志 ffmpeg 失败",
            ),
            (
                "narration-spec",
                HelpCategory::Reference,
                "叙述规范",
                "第一人称脚本撰写语法说明",
                "第一人称 脚本 校验",
            ),
        ];
        for (id, category, title, summary, keywords) in defaults {
            // 内置集合保证无重复 id,unwrap 仅用于防御性编程可见化
            reg.register(HelpTopic {
                id: id.to_owned(),
                category,
                title: title.to_owned(),
                summary: summary.to_owned(),
                content: String::new(),
                keywords: keywords.split_whitespace().map(str::to_owned).collect(),
                related: vec![],
            })
            .expect("default help topics must not collide");
        }
        reg
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn topic(id: &str, title: &str, keywords: &[&str]) -> HelpTopic {
        HelpTopic {
            id: id.to_owned(),
            category: HelpCategory::Guide,
            title: title.to_owned(),
            summary: String::new(),
            content: String::new(),
            keywords: keywords.iter().map(|s| s.to_string()).collect(),
            related: vec![],
        }
    }

    const MD: &str = "---\nid: quick-start\ntitle: 快速上手\ncategory: guide\nsummary: 5 分钟入门\nkeywords: 入门, 流水线\nrelated: ai-video\n---\n# 快速上手\n\n正文内容。";

    // ── frontmatter 解析 ────────────────────────────────────────────
    #[test]
    fn parse_full_frontmatter() {
        let t = parse_topic_markdown(MD).unwrap();
        assert_eq!(t.id, "quick-start");
        assert_eq!(t.title, "快速上手");
        assert_eq!(t.category, HelpCategory::Guide);
        assert_eq!(t.summary, "5 分钟入门");
        assert_eq!(t.keywords, vec!["入门", "流水线"]);
        assert_eq!(t.related, vec!["ai-video"]);
        assert!(t.content.starts_with("# 快速上手"));
    }

    #[test]
    fn parse_optional_fields_default_empty() {
        let md = "---\nid: a\ntitle: A\ncategory: faq\n---\nbody";
        let t = parse_topic_markdown(md).unwrap();
        assert_eq!(t.category, HelpCategory::Faq);
        assert!(t.summary.is_empty());
        assert!(t.keywords.is_empty());
        assert_eq!(t.content, "body");
    }

    #[test]
    fn parse_errors() {
        assert!(matches!(
            parse_topic_markdown("no frontmatter"),
            Err(HelpError::Parse(_))
        ));
        assert!(matches!(
            parse_topic_markdown("---\nid: x\n(no closing)"),
            Err(HelpError::Parse(_))
        ));
        assert!(matches!(
            parse_topic_markdown("---\ntitle: 缺 id\ncategory: guide\n---\nx"),
            Err(HelpError::Parse(_))
        ));
        assert!(matches!(
            parse_topic_markdown("---\nid: x\ntitle: X\ncategory: nope\n---\nx"),
            Err(HelpError::Parse(_))
        ));
    }

    // ── 注册表 ──────────────────────────────────────────────────────
    #[test]
    fn register_and_get() {
        let mut reg = HelpRegistry::new();
        reg.register(topic("a", "A", &[])).unwrap();
        assert_eq!(reg.len(), 1);
        assert!(reg.contains("a"));
        assert_eq!(reg.get("a").unwrap().title, "A");
        assert!(matches!(reg.get("zz"), Err(HelpError::NotFound(_))));
    }

    #[test]
    fn register_rejects_duplicate_id() {
        let mut reg = HelpRegistry::new();
        reg.register(topic("a", "A", &[])).unwrap();
        assert!(matches!(
            reg.register(topic("a", "A2", &[])),
            Err(HelpError::Duplicated(_))
        ));
        // 原主题不被覆盖
        assert_eq!(reg.get("a").unwrap().title, "A");
    }

    #[test]
    fn register_markdown_end_to_end() {
        let mut reg = HelpRegistry::new();
        reg.register_markdown(MD).unwrap();
        assert_eq!(reg.get("quick-start").unwrap().keywords.len(), 2);
    }

    #[test]
    fn list_by_category_filters() {
        let mut reg = HelpRegistry::new();
        reg.register(topic("g1", "G1", &[])).unwrap();
        let mut t = topic("f1", "F1", &[]);
        t.category = HelpCategory::Faq;
        reg.register(t).unwrap();
        assert_eq!(reg.list_by_category(HelpCategory::Guide).len(), 1);
        assert_eq!(reg.list_by_category(HelpCategory::Faq).len(), 1);
        assert_eq!(reg.list_by_category(HelpCategory::Shortcut).len(), 0);
        assert_eq!(reg.list_all().len(), 2);
    }

    // ── 搜索 ────────────────────────────────────────────────────────
    #[test]
    fn search_ranks_title_over_content() {
        let mut reg = HelpRegistry::new();
        let mut in_title = topic("t1", "ffmpeg 转码", &[]);
        in_title.content = "无关正文".to_owned();
        let mut in_content = topic("t2", "其他主题", &[]);
        in_content.content = "这里提到 ffmpeg".to_owned();
        reg.register(in_title).unwrap();
        reg.register(in_content).unwrap();

        let hits = reg.search("ffmpeg");
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].id, "t1"); // 标题命中 (10) > 正文命中 (1)
        assert!(hits[0].score > hits[1].score);
    }

    #[test]
    fn search_case_insensitive_and_multi_term() {
        let mut reg = HelpRegistry::new();
        let mut t = topic("x", "FFmpeg Guide", &["encode"]);
        t.summary = "encoding tutorial".to_owned();
        reg.register(t).unwrap();

        let hits = reg.search("ffmpeg encode");
        assert_eq!(hits.len(), 1);
        // 标题(10) + 关键词(6) + 摘要(3) + 正文(0),两个词都命中各计一轮
        assert!(hits[0].score >= W_TITLE + W_KEYWORD);
    }

    #[test]
    fn search_empty_query_and_no_match() {
        let mut reg = HelpRegistry::new();
        reg.register(topic("a", "A", &[])).unwrap();
        assert!(reg.search("").is_empty());
        assert!(reg.search("   ").is_empty());
        assert!(reg.search("不存在的词").is_empty());
    }

    #[test]
    fn search_tie_broken_by_id() {
        let mut reg = HelpRegistry::new();
        let mut b = topic("b", "同分", &[]);
        b.content = "x".to_owned();
        let mut a = topic("a", "同分", &[]);
        a.content = "x".to_owned();
        reg.register(b).unwrap();
        reg.register(a).unwrap();
        let hits = reg.search("同分");
        assert_eq!(hits[0].id, "a");
        assert_eq!(hits[1].id, "b");
    }

    // ── 默认主题集 ──────────────────────────────────────────────────
    #[test]
    fn defaults_match_frontend_six_cards() {
        let reg = HelpRegistry::with_defaults();
        assert_eq!(reg.len(), 6);
        for id in [
            "quick-start",
            "ai-video",
            "cli-reference",
            "python-api",
            "troubleshooting",
            "narration-spec",
        ] {
            assert!(reg.contains(id), "missing default topic {id}");
        }
        assert!(!reg.search("流水线").is_empty());
        assert!(!reg.search("错误").is_empty());
    }
}
