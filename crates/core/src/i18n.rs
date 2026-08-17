//! splicr-core · i18n — 后端多语言翻译工具

use std::collections::HashMap;
use std::sync::RwLock;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Locale {
    ZhCn,
    EnUs,
}

impl Locale {
    pub fn parse(s: &str) -> Option<Self> {
        let norm = s.to_lowercase().replace('_', "-");
        if norm.starts_with("zh") {
            Some(Self::ZhCn)
        } else if norm.starts_with("en") {
            Some(Self::EnUs)
        } else {
            None
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::ZhCn => "zh-CN",
            Self::EnUs => "en-US",
        }
    }
}

pub struct Translator {
    locale: RwLock<Locale>,
    messages: HashMap<String, HashMap<String, String>>,
}

impl std::fmt::Debug for Translator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Translator")
            .field("locale", &*self.locale.read().unwrap())
            .finish()
    }
}

impl Translator {
    pub fn new(default_locale: Locale) -> Self {
        Self {
            locale: RwLock::new(default_locale),
            messages: HashMap::new(),
        }
    }

    pub fn with_backend_defaults() -> Self {
        Self::new(Locale::ZhCn)
    }

    pub fn locale(&self) -> Locale {
        self.locale.read().unwrap().clone()
    }

    pub fn try_set_locale(&self, raw: &str) -> bool {
        if let Some(loc) = Locale::parse(raw) {
            *self.locale.write().unwrap() = loc;
            true
        } else {
            false
        }
    }

    pub fn t(&self, key: &str) -> String {
        let loc = self.locale().as_str().to_string();
        if let Some(map) = self.messages.get(&loc) {
            if let Some(val) = map.get(key) {
                return val.clone();
            }
        }
        key.to_string()
    }

    pub fn t_with_args(&self, key: &str, pairs: &[(&str, &str)]) -> String {
        let mut msg = self.t(key);
        for (k, v) in pairs {
            msg = msg.replace(&format!("{{{k}}}"), v);
        }
        msg
    }
}
