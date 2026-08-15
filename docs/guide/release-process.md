---
title: 发布流程
description: Vynaro v1.0.0 桌面端的 GitHub Releases 发布、签名、CI 集成指引。
---

# 发布流程

本文档描述 Vynaro v1.0.0 桌面端（Tauri 2 + Rust + React 19）的工程化发布流程，覆盖：

- 版本号与 `Cargo.toml` / `tauri.conf.json` 同步
- `tauri build` 三平台产物
- GitHub Releases 上传
- 应用更新器（M4 vynaro-update / M5 tauri-plugin-updater）配套策略
- CI 签名密钥（`TAURI_SIGNING_PRIVATE_KEY` 等）的安全配置

## 1. 版本号

`version` 字段在以下 3 处必须保持一致：

| 位置                                                | 用途                             |
| --------------------------------------------------- | -------------------------------- |
| `apps/desktop/src-tauri/Cargo.toml` 第 3 行         | 运行时 `AppContext.version` 注入 |
| `apps/desktop/src-tauri/tauri.conf.json` 第 4 行    | Tauri 打包元数据、资源 AC        |
| `crates/*/Cargo.toml`（`version.workspace = true`） | 工作区共享                       |

发布前用一行脚本同步：

```bash
NEW_VERSION="2.5.0-beta.1"
sed -i '' "s/^version = \"[^\"]*\"$/version = \"$NEW_VERSION\"/" \
  apps/desktop/src-tauri/Cargo.toml
# tauri.conf.json 需手工 update(避免 JSON 转义问题)
```

> ⚠️ `version` 必须符合 [semver 2.0](https://semver.org/)，alpha/beta/pre-release 后缀用 `-` 隔开。

## 2. 构建产物

### 2.1 本地三平台

```bash
# macOS (universal binary)
cd apps/desktop && pnpm tauri build --target universal-apple-darwin

# Windows (msi)
pnpm tauri build --target x86_64-pc-windows-msvc

# Linux (deb + AppImage)
pnpm tauri build --target x86_64-unknown-linux-gnu
```

构建产物路径（由 `tauri.conf.json` 的 `bundle.targets="all"` 决定）：

| 平台    | 路径                                                                                                 |
| ------- | ---------------------------------------------------------------------------------------------------- |
| macOS   | `apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Vynaro.app`             |
| macOS   | `apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/dmg/Vynaro_*.dmg`             |
| Windows | `apps/desktop/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/msi/Vynaro_*.msi`             |
| Linux   | `apps/desktop/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/deb/Vynaro_*.deb`           |
| Linux   | `apps/desktop/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/appimage/Vynaro_*.AppImage` |

### 2.2 CI 工作流

GitHub Actions（在 `.github/workflows/` 下）建议矩阵：

<v-pre>
```yaml
strategy:
  matrix:
    include:
      - os: macos-latest
        target: universal-apple-darwin
      - os: windows-latest
        target: x86_64-pc-windows-msvc
      - os: ubuntu-22.04
        target: x86_64-unknown-linux-gnu
```

每个 matrix 步骤执行：

1. `pnpm install --frozen-lockfile`
2. `pnpm --filter vynaro-desktop build` （前端）
3. `<v-pre>cargo build --release --target $&#123;&#123; matrix.target }}</v-pre>` （Rust）
4. `<v-pre>cargo tauri build --target $&#123;&#123; matrix.target }}</v-pre>` （打包）
5. `actions/upload-artifact@v4` 上传 bundle 目录
</v-pre>

## 3. GitHub Releases

发布流程：

```bash
# 1. 推 tag
git tag v1.0.0 -beta.1
git push origin v1.0.0 -beta.1

# 2. gh CLI 创建 release + 上传 bundle
gh release create v1.0.0 -beta.1 \
  --title "Vynaro v1.0.0 -beta.1" \
  --notes-file .github/RELEASE_TEMPLATE.md \
  apps/desktop/src-tauri/target/**/bundle/**/*.dmg \
  apps/desktop/src-tauri/target/**/bundle/**/*.msi \
  apps/desktop/src-tauri/target/**/bundle/**/*.deb \
  apps/desktop/src-tauri/target/**/bundle/**/*.AppImage
```

release 标题必须以 `v` 开头（`vynaro-update` 内部 `tag_name.trim_start_matches('v')` 已兼容，但 GitHub webhook 触发器仍要求 `v` 前缀）。

### 3.1 update 资源元数据

为了让 `vynaro-update` 自动探测 SHA-256 校验，二进制 asset 上传时 GitHub 仓库需要启用 **Generate release notes** 的同名 `.sha256` 文件：

```bash
# 上传前生成
shasum -a 256 Vynaro_2.5.0-beta.1_aarch64.dmg > Vynaro_2.5.0-beta.1_aarch64.dmg.sha256
gh release upload v1.0.0 -beta.1 Vynaro_2.5.0-beta.1_aarch64.dmg.sha256
```

或者更优的做法 — 把 SHA-256 直接写入 `Asset.digest`（GitHub 在 web UI 自动生成），`vynaro-update` 会读取：

```json
{
  "name": "Vynaro_2.5.0-beta.1_aarch64.dmg",
  "digest": "sha256:abc123...",
  "browser_download_url": "https://github.com/.../Vynaro_2.5.0-beta.1_aarch64.dmg"
}
```

## 4. 应用更新器策略

### 4.1 M4 阶段（当前）— `vynaro-update` crate

- 探测：`https://api.github.com/repos/qingshanyanyu/Vynaro/releases/latest`
- 下载：直链 `browser_download_url`
- 校验：读取 asset 的 `digest` 字段（`sha256:...`）
- 安装：M4 阶段仅打开下载目录，需用户手动替换并重启

**仓库硬编码**：`apps/desktop/src-tauri/src/lib.rs` 第 49 行

```rust
.register(Arc::new(UpdateService::new(
    ctx.version.to_string(),
    "qingshanyanyu/Vynaro",  // TODO 配置文件化
)))
```

> 后期应改为读取 `AppContext.services.resolve::<ConfigService>()` 的 `update_repo` 字段。

### 4.2 M5 计划 — `tauri-plugin-updater` 正式接入

| 步骤 | 操作                                                                     |
| ---- | ------------------------------------------------------------------------ |
| ①    | 添加 `tauri-plugin-updater = "2"` 到 `apps/desktop/src-tauri/Cargo.toml` |
| ②    | `tauri.conf.json` → `plugins.updater` 配置 endpoint + pubkey             |
| ③    | `capabilities/default.json` 添加 `"updater:default"` 权限                |
| ④    | `vynaro-update` 内部用 `tauri::updater::Updater` 替代 `reqwest` 直链   |
| ⑤    | 自动重启安装（替代 M4 手动下载目录）                                     |

## 5. CI 签名密钥（M5 阶段启用）

`tauri-plugin-updater` 要求 `.sig` 签名文件。流程：

```bash
# 一次性生成（本地或 CI runner）
cargo tauri signer generate -w ~/.tauri/vynaro.key
# 输出:
#   Public:  dW50cnVzdGVkIGNvbW1lbmQgLi4u (BASE64)
#   Private: kAGQ6tpaYjJuOlm...           (BASE64, 永远不要 commit)

# 每次构建
cargo tauri signer sign --private-key $TAURI_SIGNING_PRIVATE_KEY \
  src-tauri/target/release/bundle/macos/Vynaro.app.tar.gz
```

GitHub Actions Secrets 配置：

| Secret                               | 来源                             |
| ------------------------------------ | -------------------------------- |
| `TAURI_SIGNING_PRIVATE_KEY`          | `~/.tauri/vynaro.key` 完整内容   |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | 生成时如果设置过                 |
| `APPLE_CERTIFICATE`                  | base64 编码的 `.p12`             |
| `APPLE_CERTIFICATE_PASSWORD`         | p12 密码                         |
| `APPLE_SIGNING_IDENTITY`             | "Developer ID Application: ..."  |
| `APPLE_ID`                           | Apple ID 邮箱（公证用）          |
| `APPLE_PASSWORD`                     | App-specific password            |
| `APPLE_TEAM_ID`                      | 10 字符 Team ID                  |

### 5.1 GitHub Actions 签名示例

<v-pre>
```yaml
- name: Sign macOS bundle
  if: matrix.os == 'macos-latest'
  env:
    TAURI_SIGNING_PRIVATE_KEY: $&#123;&#123; secrets.TAURI_SIGNING_PRIVATE_KEY }}
    TAURI_SIGNING_PRIVATE_KEY_PASSWORD: $&#123;&#123; secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
    APPLE_CERTIFICATE: $&#123;&#123; secrets.APPLE_CERTIFICATE }}
    APPLE_CERTIFICATE_PASSWORD: $&#123;&#123; secrets.APPLE_CERTIFICATE_PASSWORD }}
    APPLE_SIGNING_IDENTITY: $&#123;&#123; secrets.APPLE_SIGNING_IDENTITY }}
  run: |
    cargo install tauri-cli --version "^2.0" --locked
    pnpm tauri build --target universal-apple-darwin
    # 自动触发 .sig 生成
```
</v-pre>

### 5.2 私钥泄露应急

1. 立即在 `~/.tauri/vynaro.key` 端执行 `cargo tauri signer revoke --key $OLD_KEY`
2. 在 GitHub → Settings → Secrets → 删除 `TAURI_SIGNING_PRIVATE_KEY`
3. 重新生成新密钥对
4. 更新 `tauri.conf.json` 的 `plugins.updater.pubkey` 字段
5. 通知所有用户手动下载最新版本（带新签名的 release）

## 6. 发布 Checklist

发布前勾选：

- [ ] `version` 三处一致（Cargo.toml / tauri.conf.json / workspace）
- [ ] `tauri build` 三平台产物存在
- [ ] GitHub Release tag 以 `v` 开头
- [ ] 每个 bundle asset 都附 `.sha256` 或在 UI 端填了 digest
- [ ] （M5）`.sig` 文件已生成并上传
- [ ] changelog 已更新（`CHANGELOG.md`）
- [ ] `pnpm exec tsc --noEmit` 0 errors
- [ ] `cargo test --workspace` 0 failed
- [ ] `cargo clippy --workspace -- -D warnings` 0 warnings

发布后验证：

- [ ] 客户端打开 → 帮助 → 检查更新 → 探测到新版本
- [ ] 下载 → 进度条 → 100% → ready
- [ ] 安装（M5）→ 自动重启；M4 → 打开下载目录

## 7. 参考链接

- [Tauri 2 官方发布指南](https://tauri.app/distribute/)
- [tauri-plugin-updater 文档](https://v2.tauri.app/plugin/updater/)
- [GitHub Actions Secrets 最佳实践](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Tauri 代码签名指南](https://tauri.app/distribute/sign/android/)
