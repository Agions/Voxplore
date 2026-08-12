//! monoloop-core · 跨模块领域原语 re-export
//!
//! 把 `monoloop-domain` 的所有公开项重新导出,
//! 让下游 crate 只需 `use monoloop_core::domain::*;` 即可访问项目模型。

pub use monoloop_domain::*;
