//! vynaro-core · help — 帮助文档与 FAQ 注册表

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum HelpCategory {
    Guide,
    Reference,
    Shortcut,
    Faq,
    Troubleshooting,
}

impl HelpCategory {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "guide" => Some(Self::Guide),
            "reference" => Some(Self::Reference),
            "shortcut" => Some(Self::Shortcut),
            "faq" => Some(Self::Faq),
            "troubleshooting" => Some(Self::Troubleshooting),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Guide => "guide",
            Self::Reference => "reference",
            Self::Shortcut => "shortcut",
            Self::Faq => "faq",
            Self::Troubleshooting => "troubleshooting",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpTopic {
    pub id: String,
    pub title: String,
    pub summary: Option<String>,
    pub category: HelpCategory,
    pub keywords: Vec<String>,
    pub content: String,
    pub related: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchHit {
    pub id: String,
    pub topic_id: String,
    pub title: String,
    pub score: u32,
    pub snippet: String,
}

#[derive(Debug, Default)]
pub struct HelpRegistry {
    topics: HashMap<String, HelpTopic>,
}

impl HelpRegistry {
    pub fn new() -> Self {
        Self {
            topics: HashMap::new(),
        }
    }

    pub fn with_defaults() -> Self {
        let mut reg = Self::new();
        reg.register(HelpTopic {
            id: "quick-start".into(),
            title: "快速开始".into(),
            summary: Some("Vynaro 第一人称解说快速上手指南".into()),
            category: HelpCategory::Guide,
            keywords: vec!["入门".into(), "导入".into()],
            content: "### Vynaro 第一人称解说快速上手\n1. 导入本地视频素材\n2. 点击智能拆条分析剧情\n3. 生成第一人称独白脚本\n4. 配音合成与字幕对齐\n5. 一键导出至短视频平台".into(),
            related: vec![],
        });
        reg
    }

    pub fn register(&mut self, topic: HelpTopic) {
        self.topics.insert(topic.id.clone(), topic);
    }

    pub fn list_all(&self) -> Vec<&HelpTopic> {
        let mut list: Vec<&HelpTopic> = self.topics.values().collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn list_by_category(&self, cat: HelpCategory) -> Vec<&HelpTopic> {
        let mut list: Vec<&HelpTopic> =
            self.topics.values().filter(|t| t.category == cat).collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn get(&self, id: &str) -> Result<&HelpTopic, anyhow::Error> {
        self.topics
            .get(id)
            .ok_or_else(|| anyhow::anyhow!("未找到帮助主题: {id}"))
    }

    pub fn search(&self, query: &str) -> Vec<SearchHit> {
        if query.trim().is_empty() {
            return vec![];
        }
        let q = query.to_lowercase();
        let mut hits = vec![];
        for t in self.topics.values() {
            let mut score = 0;
            if t.title.to_lowercase().contains(&q) {
                score += 10;
            }
            if t.keywords.iter().any(|k| k.to_lowercase().contains(&q)) {
                score += 5;
            }
            if t.content.to_lowercase().contains(&q) {
                score += 1;
            }
            if score > 0 {
                hits.push(SearchHit {
                    id: t.id.clone(),
                    topic_id: t.id.clone(),
                    title: t.title.clone(),
                    score,
                    snippet: t.content.chars().take(80).collect(),
                });
            }
        }
        hits.sort_by(|a, b| {
            b.score
                .cmp(&a.score)
                .then_with(|| a.topic_id.cmp(&b.topic_id))
        });
        hits
    }
}
