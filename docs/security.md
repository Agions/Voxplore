---
title: 安全设计
description: SceneFab 的安全机制、API 密钥管理和数据保护措施。
---

# 安全设计

SceneFab 将安全性作为核心设计原则，采用多层防护机制保护用户数据和 API 密钥。

---

## 核心安全原则

| 原则 | 说明 |
|------|------|
| **隐私优先** | 视频文件永不上传云端，全在本地处理 |
| **最小权限** | 仅请求必要的 API 权限 |
| **加密存储** | API Key 使用 OS Keychain 或 Fernet 加密 |
| **零信任** | 不假设任何外部服务是可信的 |

---

## API 密钥存储

SceneFab 采用多层级密钥存储策略，按优先级依次尝试：

```
优先 → OS Keychain（系统级安全存储）
        ├── macOS: Keychain Services
        ├── Windows: Credential Manager
        └── Linux: Secret Service API (GNOME Keyring / KWallet)
降级 → 加密文件（Fernet + PBKDF2）
        └── ~/.scenefab/credentials.enc
```

### 加密机制

| 组件 | 算法 | 说明 |
|------|------|------|
| 主密钥派生 | PBKDF2 | 从用户密码派生 AES 密钥（100,000 次迭代） |
| 文件加密 | Fernet (AES-128-CBC) | 对称加密存储 |
| 密钥盐值 | 随机生成 | 每个安装实例独立盐值 |

### 密钥生命周期

```
生成 → 派生 → 加密存储 → 使用 → 轮换 → 销毁
  │      │        │        │      │      │
  └──────┴────────┴────────┴──────┴──────┘
              全程内存加密
```

---

## 数据隐私

| 数据 | 处理方式 | 存储位置 |
|------|----------|----------|
| 视频文件 | **永不上传云端**，全在本地处理 | 本地磁盘 |
| 解说文字 | 仅传输至 AI API（DeepSeek/Qwen），不含视频画面 | 内存（临时） |
| API Key | 存储于 OS Keychain 或加密文件 | OS Keychain / 加密文件 |
| 配置文件 | 本地存储，不上传 | `~/.scenefab/` |
| 日志 | 本地存储，脱敏处理 | `~/.scenefab/logs/` |

### 数据传输

```
本地视频 → [FFmpeg 处理] → 本地输出
     │
     └─→ 仅文字描述 → [AI API] → 解说稿
              │
              └─→ 无视频画面传输
```

---

## 安全最佳实践

### 密钥管理

::: warning ⚠️ 重要
- **永远不要**将 API Key 提交到 Git 仓库
- `.env` 文件已加入 `.gitignore`，请勿移除
- 生产环境建议使用 OS Keychain 存储
- 定期轮换 API Key（建议每 90 天）
:::

```bash
# 安全检查：确认 .env 不会被提交
git diff .env          # 应为空
git log --all -- .env  # 应为空

# 检查是否有敏感信息泄露
git secrets --scan
```

### 环境隔离

```bash
# 开发环境使用独立的 API Key
export DEEPSEEK_API_KEY=sk-dev-xxx

# 生产环境使用不同的 Key
export DEEPSEEK_API_KEY=sk-prod-xxx
```

### 网络安全

| 场景 | 建议 |
|------|------|
| 公共网络 | 使用 VPN 或代理 |
| 企业网络 | 配置 HTTP_PROXY/HTTPS_PROXY |
| 本地开发 | 无需代理，直连即可 |

---

## 配置路径

| 系统 | 配置文件目录 | 权限建议 |
|------|-------------|----------|
| macOS | `~/.scenefab/` | `700` (仅用户可访问) |
| Windows | `C:\Users\<user>\.scenefab\` | 仅用户可访问 |
| Linux | `~/.scenefab/` | `700` (仅用户可访问) |

```bash
# 设置正确的权限
chmod 700 ~/.scenefab/
chmod 600 ~/.scenefab/credentials.enc
```

---

## 安全审计

### 日志审计

```bash
# 查看 API 调用日志
cat ~/.scenefab/logs/api.log | grep "API_CALL"

# 检查异常访问
cat ~/.scenefab/logs/security.log | grep "ALERT"
```

### 定期检查

| 检查项 | 频率 | 说明 |
|--------|------|------|
| API Key 轮换 | 每 90 天 | 在服务商控制台重新生成 |
| 日志审查 | 每周 | 检查异常调用模式 |
| 依赖更新 | 每月 | `pip install --upgrade` |
| 安全补丁 | 及时 | 关注 GitHub Security Advisories |

---

## 漏洞报告

如发现安全漏洞，请通过以下方式报告：

- **邮箱**：security@agions.com
- **GitHub**：[Security Advisories](https://github.com/Agions/scene-fab/security/advisories)

::: tip
我们承诺在 48 小时内响应安全漏洞报告。
:::

---

## 合规性

| 标准 | 状态 | 说明 |
|------|------|------|
| GDPR | ✅ 合规 | 不收集个人数据 |
| CCPA | ✅ 合规 | 不出售用户数据 |
| MIT License | ✅ 开源 | 商用和个人使用均无需授权 |
