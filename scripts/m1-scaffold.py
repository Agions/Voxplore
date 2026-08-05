#!/usr/bin/env python3
"""
SceneFab v3.0 · M1 脚本
为 12 个业务 crate (除 src-tauri) 批量生成 Cargo.toml + lib.rs stub。
"""
import os
import sys
from pathlib import Path

REPO = Path("/Users/zfkc/Desktop/04-AI/scene-fab")
CRATES_DIR = REPO / "crates"

# (crate 名, 模块路径数组, 文档描述)
CRATES = [
    ("scenefab-core",       [],     "服务容器/统一类型/错误/Tracing 初始化"),
    ("scenefab-domain",     [],     "领域模型 (Project, MediaFile, Script, Export 等)"),
    ("scenefab-ffmpeg",     [],     "FFmpeg 包装: 命令行调用 + 进度解析 + 探针"),
    ("scenefab-llm",        [],     "11 个 LLM Provider + LlmManager 故障切换"),
    ("scenefab-tts",        [],     "TTS 引擎 (Edge-TTS / OpenAI-TTS / GPT-SoVITS)"),
    ("scenefab-video",      [],     "视频元数据提取 (probe + chapter + scene)"),
    ("scenefab-export",     [],     "4 策略导出 (single/concat/batch/series)"),
    ("scenefab-pipeline",   [],     "5 步流水线状态机 + MonologueMaker"),
    ("scenefab-plugin",     [],     "wasmtime 插件宿主 + Rust SDK + WASM 沙箱"),
    ("scenefab-update",     [],     "tauri-plugin-updater + GitHub Releases"),
    ("scenefab-help",       [],     "帮助内容分发 + i18n 资源加载"),
    ("scenefab-i18n",       [],     "i18n 资源加载 + 语言切换运行时"),
    # scenefab-cli 是 binary,需要 [bin] section
]

CARGO_TPL = '''[package]
name = "{name}"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
description = "{desc}"

[lints]
workspace = true
'''

CLI_CARGO_TPL = '''[package]
name = "{name}"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
description = "{desc}"

[[bin]]
name = "{name}"
path = "src/main.rs"

[lints]
workspace = true
'''

LIB_RS_TPL = '''//! {name} v3.0 · {stage} 占位实现
//!
//! ## 责任范围
//! {desc}
//!
//! ## 状态
//! - **当前阶段**：M1 ({stage}) — 仅类型 / trait 占位,无业务实现
//! - **下一阶段**:M2 — 接入 {next} 实现
//!
//! ## 后续模块规划 (M2-M10)
//! - 详见 docs/refactor/v3-migration/03-rust-backend.md § <对应小节>

#![allow(dead_code, unused_imports)]
'''


def main():
    for i, (name, _mod_paths, desc) in enumerate(CRATES):
        crate_dir = CRATES_DIR / name
        if not crate_dir.exists():
            print(f"  ✗ {name} 不存在,跳过")
            continue

        # Cargo.toml
        cargo_toml = crate_dir / "Cargo.toml"
        cargo_toml.write_text(CARGO_TPL.format(
            name=name, desc=desc), encoding="utf-8")
        print(f"  ✓ {name}/Cargo.toml")

        # lib.rs (scenefab-core 特殊,带 domain/services 模块)
        lib_rs = crate_dir / "src" / "lib.rs"
        stages = ["Init", "Foundation", "Core", "Integration", "Polish"]
        nexts = {
            "scenefab-core":      "AppContext / ServiceContainer / Result + Error + tracing_subscriber",
            "scenefab-domain":    "Project / Timeline / MediaFile / Script 等结构体 + serde",
            "scenefab-ffmpeg":    "FFmpeg sidecar 探针 + 编码调用 + 进度事件",
            "scenefab-llm":       "LlmProvider trait + 11 provider impl + LlmManager fallback chain",
            "scenefab-tts":       "TtsProvider trait + 3 provider + 音色/语速参数",
            "scenefab-video":     "ffprobe 元数据 + chapter detection + scene segmentation",
            "scenefab-export":    "ExportStrategy trait + 4 策略 + aspect ratio / codec 转码",
            "scenefab-pipeline":  "5 步状态机 (XState 模型) + MonologueMaker 业务编排",
            "scenefab-plugin":    "Manifest TOML parser + wasmtime linker + capability 校验",
            "scenefab-update":    "GitHub Releases polling + 增量下载 + 校验和签名",
            "scenefab-help":      "嵌入式 help 索引 + 离线 markdown 加载",
            "scenefab-i18n":      "加载 zh-CN/en-US/ja-JP Fluent .ftl 文件 + rust-i18n",
        }
        stage = stages[min(i, len(stages) - 1)]
        next_ = nexts.get(name, "完整实现")

        content = LIB_RS_TPL.format(
            name=name,
            stage=stage,
            desc=desc,
            next=next_,
        )
        lib_rs.write_text(content, encoding="utf-8")
        print(f"  ✓ {name}/src/lib.rs")

    # scenefab-cli 单独处理 (binary + 含 main.rs)
    cli = CRATES_DIR / "scenefab-cli"
    if cli.exists():
        cli_dir = cli / "src"
        (cli_dir / "main.rs").write_text(LIB_RS_TPL.format(
            name="scenefab-cli",
            stage="Init",
            desc="SceneFab 命令行入口 (CI / 自动化 / Advanced 用户)",
            next="scenefab build/export/doctor/updater 子命令",
        ), encoding="utf-8")
        print(f"  ✓ scenefab-cli/src/main.rs")


if __name__ == "__main__":
    main()
