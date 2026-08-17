//! splicr-core · 跨模块领域原语 re-export
//!
//! 把 `splicr-domain` 的所有公开项重新导出,
//! 让下游 crate 只需 `use splicr_core::domain::*;` 即可访问项目模型。

pub use splicr_domain::*;
