//! scenefab-plugin v3.0 · Polish 占位实现
//!
//! ## 责任范围
//! wasmtime 插件宿主 + Rust SDK + WASM 沙箱
//!
//! ## 状态
//! - **当前阶段**：M1 (Polish) — 仅类型 / trait 占位,无业务实现
//! - **下一阶段**:M2 — 接入 Manifest TOML parser + wasmtime linker + capability 校验 实现
//!
//! ## 后续模块规划 (M2-M10)
//! - 详见 docs/refactor/v3-migration/03-rust-backend.md § <对应小节>

#![allow(dead_code, unused_imports)]
