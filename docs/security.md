---
title: 安全设计
description: SceneFab 的安全机制、API 密钥管理和数据保护措施。
---

# 安全设计

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

---

## 数据隐私

| 数据 | 处理方式 |
|------|----------|
| 视频文件 | **永不上传云端**，全在本地处理 |
| 解说文字 | 仅传输至 AI API（DeepSeek/Qwen），不含视频画面 |
| API Key | 存储于 OS Keychain 或加密文件，不写入代码或 Git |

---

## 安全最佳实践

::: warning ⚠️ 重要
- **永远不要**将 API Key 提交到 Git 仓库
- `.env` 文件已加入 `.gitignore`，请勿移除
- 生产环境建议使用 OS Keychain 存储
:::

```bash
# 安全检查：确认 .env 不会被提交
git diff .env          # 应为空
git log --all -- .env  # 应为空的
```

---

## 配置路径

| 系统 | 配置文件目录 |
|------|-------------|
| macOS | `~/.scenefab/` |
| Windows | `C:\Users\<user>\.scenefab\` |
| Linux | `~/.scenefab/` |