//! scenefab-i18n v2.5.0 · 后端国际化运行时 (M5.6 实装)
//!
//! ## 责任范围
//! Rust 端文案的加载 / 查询 / 语言切换。前端文案走 i18next (apps/desktop),
//! 本 crate 只服务后端错误消息、CLI 输出、事件 payload 中的人类可读文案。
//!
//! ## 设计
//! - 资源格式:JSON 两层结构 `{ "zh-CN": { "key": "文案" }, "en-US": {...} }`
//! - fallback 链:当前 Locale → zh-CN (DoD `fallback_lang`) → 原样返回 key
//! - 插值:`t_with_args("hello", &[("name", "World")])` 替换 `{name}` 占位符
//! - 线程安全:`Translator` 内部 RwLock,可 `Arc` 共享跨 tokio task
//! - 零新外部依赖:不引入 rust-i18n/unic-langid,纯 std + serde_json
//!
//! ## 用法
//! ```
//! use scenefab_i18n::{Locale, Translator};
//!
//! let json = r#"{"zh-CN": {"export.done": "导出完成: {path}"},
//!                "en-US": {"export.done": "Export done: {path}"}}"#;
//! let tr = Translator::from_json(json).unwrap();
//! assert_eq!(tr.t("export.done"), "导出完成: {path}");
//! tr.set_locale(Locale::EnUs);
//! assert_eq!(
//!     tr.t_with_args("export.done", &[("path", "/tmp/a.mp4")]),
//!     "Export done: /tmp/a.mp4"
//! );
//! ```

use std::collections::HashMap;
use std::sync::RwLock;

use serde::{Deserialize, Serialize};
use thiserror::Error;

// ════════════════════════════════════════════════════════════════════════
// 错误类型
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error)]
pub enum I18nError {
    /// JSON 资源解析失败
    #[error("i18n resource parse error: {0}")]
    Parse(String),
    /// 资源中不包含任何受支持的 Locale
    #[error("i18n resource contains no supported locale")]
    Empty,
}

// ════════════════════════════════════════════════════════════════════════
// Locale
// ════════════════════════════════════════════════════════════════════════

/// 受支持的语言 (与 DoD `i18n.locales` 一致:zh-CN / en-US)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Locale {
    #[serde(rename = "zh-CN")]
    ZhCn,
    #[serde(rename = "en-US")]
    EnUs,
}

impl Locale {
    /// BCP-47 标签 (与前端 i18next 资源目录命名一致)
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ZhCn => "zh-CN",
            Self::EnUs => "en-US",
        }
    }

    /// 宽松解析:大小写不敏感,`-`/`_` 均可 ("zh_cn" → ZhCn)
    pub fn parse(raw: &str) -> Option<Self> {
        let norm = raw.trim().to_ascii_lowercase().replace('_', "-");
        match norm.as_str() {
            "zh-cn" | "zh" => Some(Self::ZhCn),
            "en-us" | "en" => Some(Self::EnUs),
            _ => None,
        }
    }

    /// 全部受支持的 Locale
    pub fn all() -> [Self; 2] {
        [Self::ZhCn, Self::EnUs]
    }
}

impl std::fmt::Display for Locale {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ════════════════════════════════════════════════════════════════════════
// I18nBundle · 静态资源表
// ════════════════════════════════════════════════════════════════════════

/// 翻译资源表:Locale → (key → 文案)。不可变,可多 Translator 共享。
#[derive(Debug, Clone, Default)]
pub struct I18nBundle {
    messages: HashMap<Locale, HashMap<String, String>>,
}

impl I18nBundle {
    pub fn new() -> Self {
        Self::default()
    }

    /// 从 JSON 字符串解析 (两层结构:locale → key → 文案)。
    /// 未识别的 locale 键被静默忽略,但至少要有一个受支持的 locale。
    pub fn from_json(json: &str) -> Result<Self, I18nError> {
        let outer: HashMap<String, serde_json::Value> =
            serde_json::from_str(json).map_err(|e| I18nError::Parse(format!("top-level: {e}")))?;
        let mut bundle = Self::default();
        for (locale_key, value) in outer {
            let Some(locale) = Locale::parse(&locale_key) else {
                continue;
            };
            let inner: HashMap<String, String> = serde_json::from_value(value)
                .map_err(|e| I18nError::Parse(format!("locale {locale_key}: {e}")))?;
            bundle.messages.entry(locale).or_default().extend(inner);
        }
        if bundle.messages.is_empty() {
            return Err(I18nError::Empty);
        }
        Ok(bundle)
    }

    /// 合并另一份 JSON 资源 (后加载覆盖同名 key)
    pub fn merge_json(&mut self, json: &str) -> Result<(), I18nError> {
        let other = Self::from_json(json)?;
        for (locale, msgs) in other.messages {
            self.messages.entry(locale).or_default().extend(msgs);
        }
        Ok(())
    }

    /// 直接注册单条文案 (代码内嵌默认文案用)
    pub fn insert(&mut self, locale: Locale, key: impl Into<String>, msg: impl Into<String>) {
        self.messages
            .entry(locale)
            .or_default()
            .insert(key.into(), msg.into());
    }

    /// 查询 (不做 fallback)
    pub fn get(&self, locale: Locale, key: &str) -> Option<&str> {
        self.messages.get(&locale)?.get(key).map(String::as_str)
    }

    /// 某 locale 下的 key 总数
    pub fn key_count(&self, locale: Locale) -> usize {
        self.messages.get(&locale).map_or(0, HashMap::len)
    }

    /// 已加载的 locale 列表
    pub fn locales(&self) -> Vec<Locale> {
        let mut v: Vec<Locale> = self.messages.keys().copied().collect();
        v.sort_by_key(|l| l.as_str());
        v
    }
}

// ════════════════════════════════════════════════════════════════════════
// Translator · 运行时查询器
// ════════════════════════════════════════════════════════════════════════

/// 运行时翻译器。`Arc<Translator>` 可跨线程共享,`set_locale` 即时生效。
///
/// fallback 链:当前 locale → [`FALLBACK_LOCALE`] → 原样返回 key。
#[derive(Debug)]
pub struct Translator {
    bundle: I18nBundle,
    locale: RwLock<Locale>,
}

/// DoD `fallback_lang`:任何 locale 缺 key 时回落到 zh-CN
pub const FALLBACK_LOCALE: Locale = Locale::ZhCn;

impl Translator {
    /// 空 bundle 构造 (稍后用 [`Self::merge_json`] 填充)
    pub fn new() -> Self {
        Self {
            bundle: I18nBundle::new(),
            locale: RwLock::new(FALLBACK_LOCALE),
        }
    }

    /// 从 JSON 资源构造,默认 locale = zh-CN
    pub fn from_json(json: &str) -> Result<Self, I18nError> {
        Ok(Self {
            bundle: I18nBundle::from_json(json)?,
            locale: RwLock::new(FALLBACK_LOCALE),
        })
    }

    /// 内置后端默认文案 (Rust 侧错误 / 事件 / CLI 通用短语)
    pub fn with_backend_defaults() -> Self {
        let mut tr = Self::new();
        let zh = &mut tr.bundle;
        zh.insert(Locale::ZhCn, "common.ok", "完成");
        zh.insert(Locale::ZhCn, "common.cancelled", "已取消");
        zh.insert(Locale::ZhCn, "common.failed", "失败: {reason}");
        zh.insert(Locale::ZhCn, "pipeline.started", "流水线已启动");
        zh.insert(Locale::ZhCn, "pipeline.step_done", "步骤 {step}/5 完成");
        zh.insert(Locale::ZhCn, "pipeline.done", "全部 5 步完成");
        zh.insert(Locale::ZhCn, "export.done", "导出完成: {path}");
        zh.insert(Locale::ZhCn, "update.available", "发现新版本 {version}");
        let en = &mut tr.bundle;
        en.insert(Locale::EnUs, "common.ok", "Done");
        en.insert(Locale::EnUs, "common.cancelled", "Cancelled");
        en.insert(Locale::EnUs, "common.failed", "Failed: {reason}");
        en.insert(Locale::EnUs, "pipeline.started", "Pipeline started");
        en.insert(Locale::EnUs, "pipeline.step_done", "Step {step}/5 done");
        en.insert(Locale::EnUs, "pipeline.done", "All 5 steps done");
        en.insert(Locale::EnUs, "export.done", "Export done: {path}");
        en.insert(
            Locale::EnUs,
            "update.available",
            "New version {version} available",
        );
        tr
    }

    /// 合并额外 JSON 资源 (后加载覆盖同名 key)
    pub fn merge_json(&mut self, json: &str) -> Result<(), I18nError> {
        self.bundle.merge_json(json)
    }

    /// 当前语言
    pub fn locale(&self) -> Locale {
        *self.locale.read().expect("i18n locale lock poisoned")
    }

    /// 切换语言 (即时生效,无需重建)
    pub fn set_locale(&self, locale: Locale) {
        *self.locale.write().expect("i18n locale lock poisoned") = locale;
    }

    /// 宽松切换:`"en-US"` / `"en_us"` 均可;无法识别时保持现状并返回 false
    pub fn try_set_locale(&self, raw: &str) -> bool {
        match Locale::parse(raw) {
            Some(l) => {
                self.set_locale(l);
                true
            }
            None => false,
        }
    }

    /// 查文案:当前 locale → zh-CN → key 原样返回
    pub fn t(&self, key: &str) -> String {
        let locale = self.locale();
        if let Some(msg) = self.bundle.get(locale, key) {
            return msg.to_owned();
        }
        if locale != FALLBACK_LOCALE {
            if let Some(msg) = self.bundle.get(FALLBACK_LOCALE, key) {
                return msg.to_owned();
            }
        }
        key.to_owned()
    }

    /// 带插值查文案:`{name}` 占位符被 args 中同名值替换,未命中占位符原样保留
    pub fn t_with_args(&self, key: &str, args: &[(&str, &str)]) -> String {
        let mut out = self.t(key);
        for (name, value) in args {
            out = out.replace(&format!("{{{name}}}"), value);
        }
        out
    }

    /// 底层 bundle 只读访问 (统计 / 调试用)
    pub fn bundle(&self) -> &I18nBundle {
        &self.bundle
    }
}

impl Default for Translator {
    fn default() -> Self {
        Self::with_backend_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_json() -> &'static str {
        r#"{
            "zh-CN": {"greet": "你好 {name}", "only_zh": "仅中文"},
            "en-US": {"greet": "Hello {name}"},
            "ja-JP": {"greet": "こんにちは"}
        }"#
    }

    // ── Locale ──────────────────────────────────────────────────────
    #[test]
    fn locale_parse_variants() {
        assert_eq!(Locale::parse("zh-CN"), Some(Locale::ZhCn));
        assert_eq!(Locale::parse("zh_cn"), Some(Locale::ZhCn));
        assert_eq!(Locale::parse("ZH"), Some(Locale::ZhCn));
        assert_eq!(Locale::parse("en-us"), Some(Locale::EnUs));
        assert_eq!(Locale::parse("en"), Some(Locale::EnUs));
        assert_eq!(Locale::parse("ja-JP"), None);
        assert_eq!(Locale::parse(""), None);
    }

    #[test]
    fn locale_as_str_roundtrip() {
        for l in Locale::all() {
            assert_eq!(Locale::parse(l.as_str()), Some(l));
        }
    }

    #[test]
    fn locale_serde_uses_bcp47() {
        assert_eq!(serde_json::to_string(&Locale::ZhCn).unwrap(), "\"zh-CN\"");
        let back: Locale = serde_json::from_str("\"en-US\"").unwrap();
        assert_eq!(back, Locale::EnUs);
    }

    // ── Bundle ──────────────────────────────────────────────────────
    #[test]
    fn bundle_from_json_skips_unknown_locale() {
        let b = I18nBundle::from_json(sample_json()).unwrap();
        assert_eq!(b.locales(), vec![Locale::EnUs, Locale::ZhCn]); // 按 BCP-47 标签排序
        assert_eq!(b.get(Locale::ZhCn, "greet"), Some("你好 {name}"));
        assert_eq!(b.key_count(Locale::ZhCn), 2);
        assert_eq!(b.key_count(Locale::EnUs), 1);
    }

    #[test]
    fn bundle_from_json_errors() {
        assert!(matches!(
            I18nBundle::from_json("not json"),
            Err(I18nError::Parse(_))
        ));
        assert!(matches!(
            I18nBundle::from_json(r#"{"ja-JP": {"a": "b"}}"#),
            Err(I18nError::Empty)
        ));
        // locale 内层必须是 string map
        assert!(matches!(
            I18nBundle::from_json(r#"{"zh-CN": {"k": 42}}"#),
            Err(I18nError::Parse(_))
        ));
    }

    #[test]
    fn bundle_merge_overrides_same_key() {
        let mut b = I18nBundle::from_json(sample_json()).unwrap();
        b.merge_json(r#"{"zh-CN": {"greet": "您好 {name}"}}"#)
            .unwrap();
        assert_eq!(b.get(Locale::ZhCn, "greet"), Some("您好 {name}"));
        assert_eq!(b.key_count(Locale::ZhCn), 2);
    }

    // ── Translator ──────────────────────────────────────────────────
    #[test]
    fn t_hits_current_locale() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert_eq!(tr.t("greet"), "你好 {name}");
    }

    #[test]
    fn t_falls_back_to_zh_cn() {
        let tr = Translator::from_json(sample_json()).unwrap();
        tr.set_locale(Locale::EnUs);
        // en-US 缺 only_zh → fallback zh-CN
        assert_eq!(tr.t("only_zh"), "仅中文");
    }

    #[test]
    fn t_returns_key_when_missing_everywhere() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert_eq!(tr.t("no.such.key"), "no.such.key");
    }

    #[test]
    fn t_with_args_interpolates() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert_eq!(
            tr.t_with_args("greet", &[("name", "SceneFab")]),
            "你好 SceneFab"
        );
    }

    #[test]
    fn t_with_args_keeps_unmatched_placeholder() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert_eq!(tr.t_with_args("greet", &[]), "你好 {name}");
    }

    #[test]
    fn set_locale_switches_messages() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert_eq!(tr.locale(), Locale::ZhCn);
        tr.set_locale(Locale::EnUs);
        assert_eq!(tr.locale(), Locale::EnUs);
        assert_eq!(tr.t_with_args("greet", &[("name", "World")]), "Hello World");
    }

    #[test]
    fn try_set_locale_rejects_unknown() {
        let tr = Translator::from_json(sample_json()).unwrap();
        assert!(tr.try_set_locale("en_US"));
        assert_eq!(tr.locale(), Locale::EnUs);
        assert!(!tr.try_set_locale("fr-FR"));
        assert_eq!(tr.locale(), Locale::EnUs); // 保持现状
    }

    #[test]
    fn backend_defaults_cover_both_locales() {
        let tr = Translator::with_backend_defaults();
        assert!(tr.bundle().key_count(Locale::ZhCn) >= 8);
        assert!(tr.bundle().key_count(Locale::EnUs) >= 8);
        assert_eq!(tr.t("pipeline.done"), "全部 5 步完成");
        tr.set_locale(Locale::EnUs);
        assert_eq!(tr.t("pipeline.done"), "All 5 steps done");
        assert_eq!(
            tr.t_with_args("common.failed", &[("reason", "disk full")]),
            "Failed: disk full"
        );
    }

    #[test]
    fn translator_is_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<Translator>();
    }
}
