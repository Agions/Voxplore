---
title: 配置参考
description: SceneFab 两文件配置结构与常见配置场景。
---

# 配置参考

SceneFab 采用两文件配置结构，将应用设置与 LLM 提供商配置分离，便于管理和切换。

## 配置文件结构

| 文件 | 用途 | 格式 |
| --- | --- | --- |
| `config/app_config.yaml` | 应用级设置（缓存、日志、默认提供商、重试策略） | YAML |
| `config/llm.yaml` | LLM 提供商配置（API Key、模型、参数） | YAML |

## 快速参考

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `default_llm` | `deepseek` | 默认 LLM 提供商 |
| `cache.enabled` | `true` | 启用结果缓存 |
| `cache.max_size` | `100` | 最大缓存条目数 |
| `cache.ttl` | `3600` | 缓存过期时间（秒） |
| `log_level` | `INFO` | 日志级别 |
| `retry.max_retries` | `3` | 最大重试次数 |
| `retry.backoff_factor` | `2.0` | 退避因子 |
| `retry.base_delay` | `1.0` | 基础延迟（秒） |
| `retry.max_delay` | `60.0` | 最大延迟（秒） |

### app_config.yaml

应用级配置，控制缓存、日志、默认提供商和重试策略：

```yaml
# config/app_config.yaml
cache:
  enabled: true
  max_size: 100
  ttl: 3600
default_llm: deepseek
log_level: INFO
retry:
  max_retries: 3
  backoff_factor: 2.0
  base_delay: 1.0
  max_delay: 60.0
```

`default_llm` 字段决定默认使用哪个 LLM 提供商，可选值：`qwen` / `deepseek` / `openai` / `claude` / `gemini` / `kimi` / `glm5` / `doubao` / `hunyuan` / `local`。

### llm.yaml

LLM 提供商配置，每个提供商独立配置 API Key、模型和生成参数：

```yaml
# config/llm.yaml
LLM:
  default_provider: "deepseek"

  qwen:
    enabled: true
    api_key: ${QWEN_API_KEY}
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: "qwen3.7-max"
    max_tokens: 32768
    temperature: 0.7

  deepseek:
    enabled: false
    api_key: ${DEEPSEEK_API_KEY}
    base_url: "https://api.deepseek.com"
    model: "deepseek-v4-pro"
    max_tokens: 32768
    temperature: 0.7
```

`api_key` 支持环境变量引用（`${VAR_NAME}`），避免将密钥硬编码到配置文件中。

### 本地模型配置

本地模型通过 Ollama 或 LM Studio 运行，无需 API Key：

```yaml
# config/llm.yaml 中的 local 段
local:
  enabled: false
  api_key: ""
  base_url: "http://localhost:11434"
  model: "qwen3:32b"
  max_tokens: 4096
  temperature: 0.7
```

## 常见配置场景

### 场景一：首次配置

1. 复制配置模板：

```bash
cp config/llm.yaml.example config/llm.yaml
cp config/app_config.yaml.example config/app_config.yaml
```

2. 在 `config/llm.yaml` 中填入 API Key（至少配置一个提供商）：

```yaml
qwen:
  enabled: true
  api_key: "sk-your-qwen-key"

deepseek:
  enabled: true
  api_key: "sk-your-deepseek-key"
```

3. 在 `config/app_config.yaml` 中设置默认提供商：

```yaml
default_llm: qwen
```

### 场景二：切换提供商

修改 `config/app_config.yaml` 中的 `default_llm` 字段，然后在 `config/llm.yaml` 中确保目标提供商已启用并配置了 API Key：

```yaml
# app_config.yaml
default_llm: deepseek
```

```yaml
# llm.yaml
deepseek:
  enabled: true
  api_key: ${DEEPSEEK_API_KEY}
  model: "deepseek-v4-pro"
```

### 场景三：自定义模型

在 `config/llm.yaml` 中修改目标提供商的 `model` 字段。模型名必须存在于 `services.ai.model_catalog` 中：

```yaml
# 切换到 Gemini 3.1 Pro 用于长视频理解
gemini:
  enabled: true
  api_key: ${GEMINI_API_KEY}
  model: "gemini-3.1-pro"
  max_tokens: 8000
```

## 环境变量

API Key 也可以通过环境变量设置，优先级高于配置文件：

| 变量 | 说明 |
| --- | --- |
| `QWEN_API_KEY` | 阿里云百炼 API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `CLAUDE_API_KEY` | Anthropic API Key |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `KIMI_API_KEY` | Kimi / Moonshot API Key |
| `GLM5_API_KEY` | 智谱 GLM API Key |
| `DOUBAO_API_KEY` | 字节豆包 API Key |
| `HUNYUAN_API_KEY` | 腾讯混元 API Key |

## 配置优先级

```text
命令行参数 > 环境变量 > llm.yaml / app_config.yaml > 默认值
```

## 故障排除

| 问题 | 排查步骤 |
| --- | --- |
| 配置不生效 | 确认 YAML 语法正确，使用 `scenefab --show-config` 查看当前生效配置 |
| API Key 无效 (401) | 确认 Key 格式正确（通常 `sk-` 开头）且未过期 |
| 触发限流 (429) | 降低并发或在服务商控制台升级套餐 |
| 模型名错误 | 确认模型名存在于 `model_catalog` 中，使用 `scenefab --list-models` 查看 |

## 相关文档

- [AI 模型参考](/ai-models) — 模型选择与推荐配置
- [架构概览](/architecture) — 配置在系统中的位置
