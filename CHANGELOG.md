# Changelog

All notable changes to the splicr project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-06

### 🚀 Major Features & Highlights
- **Architectural Rewrite**: Complete modernization from legacy Python codebase to a high-performance **Tauri 2 + Rust + React 19 + TypeScript** desktop architecture.
- **7-Step AI Video Narrative Pipeline**:
  - **Step 1 (Intake)**: Raw video file drag-and-drop intake with resolution and frame rate probe.
  - **Step 2 (Detection)**: High-speed FFmpeg scene transition detection and highlight clip split.
  - **Step 3 (Script Engine)**: First-person monologue narration generator with 11 LLM provider choices (DeepSeek, OpenAI, Claude, Gemini, Ollama, etc.).
  - **Step 4 (Voice Synth)**: Multi-engine TTS voice synthesis with Edge-TTS and zero-shot GPT-SoVITS voice cloning.
  - **Step 5 (Subtitle)**: VAD endpoint detection for precise subtitle alignment and dynamic karaoke style rendering.
  - **Step 6 (Timeline Compose)**: Multi-track DAG alignment for background music, vocal track, and video keyframes.
  - **Step 7 (CapCut Draft Export)**: One-click export to native CapCut project draft format (`.draft`) and short-video resolution presets.

### 🎨 UI & Design System
- **Cinematic Darkroom Theme**: Sleek deep obsidian background (`#0D0D0F`) paired with warm gold accents (`#F5C842`).
- **Streamlined Navigation**: Simplified 5-module left navigation sidebar (首页, AI 7步流, 资产库, 设置, 帮助) with zero route duplication.
- **Chinese First**: Default interface language initialized to Chinese (`zh-CN`).

### 🛠️ Infrastructure & Quality Assurance
- **Project Structure Flattening**: Simplified monorepo structure by placing frontend and desktop app core cleanly at project root.
- **100% Test Coverage Compliance**: Passed 157 Vitest unit tests and Rust workspace check.
