---
title: 安全设计
description: Voxplore 的安全机制、API 密钥管理和数据保护措施。
---

# 安全设计

Voxplore 在设计之初就将安全作为核心考量，保护用户的敏感数据和隐私。

---

## API 密钥安全

### 存储层级

Voxplore 采用多层级密钥存储策略，按优先级依次尝试：

```
优先 → OS Keychain (系统级安全存储)
        ├── macOS:        Keychain Services
        ├── Windows:       Credential Manager
        └── Linux:        Secret Service API (GNOME Keyring / KWallet)

降级 → 加密文件 (Fernet + PBKDF2)
        └── ~/.narrafiilm/credentials.enc
```

### 加密机制

| 组件 | 算法 | 说明 |
|------|------|------|
| 主密钥派生 | PBKDF2 | 从用户密码派生 AES 密钥（100,000 次迭代） |
| 文件加密 | Fernet (AES-128-CBC) | 对称加密存储 |
| 密钥盐值 | 随机生成 | 每个安装实例独立盐值 |

### 密钥访问流程

```
用户输入 API Key
      │
      ▼
SecureKeyManager
      │
      ├─→ [优先] 写入 OS Keychain
      │         (系统级加密存储)
      │
      └─→ [降级] 写入加密文件
                (credentials.enc)
```

### 安全最佳实践

::: warning ⚠️ 重要
- **永远不要**将 API Key 提交到 Git 仓库
- `.env` 文件已加入 `.gitignore`，请勿移除
- 生产环境建议使用 OS Keychain 存储
:::

```bash
# 安全检查：确认 .env 不会被提交
git check-ignore .env
# 应该输出: .env

# 如果没有输出，手动添加
echo ".env" >> .gitignore
```

---

## 文件操作安全

### 路径安全

Voxplore 对所有文件路径进行严格验证：

| 检查项 | 说明 |
|--------|------|
| 路径穿越检测 | 禁止 `..` 等路径遍历攻击 |
| 危险路径禁止 | 禁止访问 `/etc`、`/proc`、`/sys`、`C:\Windows` 等系统目录 |
| 扩展名白名单 | 仅允许操作视频/音频/图片等合法文件类型 |
| 文件大小限制 | 单文件最大 50GB（可配置） |

### 安全文件处理器

```python
# 使用 SecureFileHandler 进行所有文件操作
from narrafiilm.core.secure_file_handler import SecureFileHandler

handler = SecureFileHandler()

# 安全读取（自动验证路径和扩展名）
with handler.open('/user/project/video.mp4', 'rb') as f:
    data = f.read()

# 不安全的路径将被拒绝
# handler.open('/etc/passwd', 'rb')  # → SecurityError
# handler.open('../../../secret.mp4', 'rb')  # → SecurityError
```

---

## 命令执行安全

Voxplore 仅允许执行经过白名单验证的命令：

### FFmpeg 白名单

```python
# 允许的命令（仅 FFmpeg 系列）
ALLOWED_COMMANDS = {
    'ffmpeg',
    'ffprobe',
    'ffmpegthumbnailer',
    'mkvmerge',
    'mkvextract',
}

# 危险命令关键词检测
DANGEROUS_PATTERNS = [
    'rm -rf',
    'dd if=',
    'mkfs',
    'LD_PRELOAD',
    '| sh',
    '; sh',
    '&& sh',
]

# 环境变量清理
BLOCKED_ENV_VARS = [
    'LD_PRELOAD',
    'LD_LIBRARY_PATH',  # 可被利用加载恶意 .so
    'BASH_ENV',
    'ENV',
]
```

### 命令执行验证

```python
# 示例：安全执行 FFmpeg
from narrafiilm.core.command_validator import CommandValidator

validator = CommandValidator()

# 验证命令是否在白名单中
if not validator.is_allowed('ffmpeg'):
    raise SecurityError(f"Command not in whitelist: ffmpeg")

# 验证参数中无危险内容
if validator.has_dangerous_patterns(args):
    raise SecurityError("Dangerous pattern detected in command args")

# 清理危险环境变量后执行
env = validator.clean_environment(original_env)
subprocess.run(['ffmpeg', ...], env=env)
```

---

## 插件安全

### 插件签名验证

生产环境中的插件必须经过数字签名：

```bash
# 插件开发者签名
python -m narrafiilm plugins sign ./plugins/my-plugin

# Voxplore 验证签名
python -m narrafiilm plugins install ./my-plugin-1.0.0.vfplugin
# → 签名验证通过后才安装
```

### 插件沙箱

插件运行在受限的沙箱环境中：

| 限制类型 | 说明 |
|----------|------|
| 文件访问 | 只能访问用户授权的目录 |
| 网络访问 | 可配置，默认仅允许 HTTPS |
| 系统命令 | 禁止执行任何 Shell 命令 |
| API Key | 插件不直接获取 API Key（通过 IPC 获取） |

---

## 数据隐私

### 本地处理优先

- 🎬 视频内容仅在本地处理
- 🤖 AI 分析时，视频片段会上传到 AI 服务商（使用他们的隐私政策）
- 📝 生成的字幕和脚本保存在本地

### 网络请求安全

- ✅ 所有 AI API 请求使用 HTTPS
- ✅ 验证服务器证书
- ✅ 不发送敏感系统信息到第三方

### 数据清理

```bash
# 清除所有本地缓存
python -m narrafiilm cache clear

# 清除项目数据（不可恢复）
python -m narrafiilm data purge --project=my-project
```

---

## 漏洞报告

如果你发现安全漏洞，请通过以下方式私下报告：

| 方式 | 说明 |
|------|------|
| GitHub Security Advisory | [报告安全漏洞](https://github.com/Agions/Voxplore/security/advisories/new) |
| 邮件 | security@narrafiilm.ai |

**请不要**在公开的 GitHub Issues 中报告安全问题。

我们承诺在 48 小时内响应，并在修复后公开致谢。

---

## 安全配置参考

| 配置项 | 文件位置 | 说明 |
|--------|----------|------|
| API Key 存储 | `~/.narrafiilm/credentials.enc` | 加密文件 |
| 信任密钥 | `~/.narrafiilm/trusted_keys/` | 插件签名公钥 |
| 插件目录 | `./plugins/` | 插件加载目录 |
| 日志 | `~/.narrafiilm/logs/` | 操作日志（不含敏感数据） |
| 缓存 | `~/.narrafiilm/cache/` | 临时缓存 |

---

## 相关文档

- 🔧 [配置参考](./config.md) — 配置文件详解
- 🤖 [AI 模型配置](./guide/ai-configuration.md) — API Key 配置
- 🔌 [插件开发](./guide/plugin-development.md) — 插件安全机制
- 📐 [架构概览](./architecture.md) — 系统架构
