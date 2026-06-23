# SceneFab 示例

本目录包含 SceneFab 的使用示例，帮助你快速上手。

## 目录结构

```text
examples/
├── README.md              # 本文件
├── config/                # 配置文件示例
│   ├── llm.yaml           # LLM 配置示例
│   └── app_config.yaml    # 应用配置示例
├── cli-usage.sh           # CLI 命令示例
└── python-api.py          # Python API 示例
```

## 快速开始

### 1. 配置示例

复制配置文件到项目根目录的 `config/` 目录：

```bash
cp examples/config/llm.yaml config/llm.yaml
cp examples/config/app_config.yaml config/app_config.yaml
```

编辑 `config/llm.yaml`，填入你的 API Key。

### 2. CLI 使用

查看 CLI 命令示例：

```bash
cat examples/cli-usage.sh
```

### 3. Python API

查看 Python API 示例：

```bash
cat examples/python-api.py
```

## 更多资源

- [快速开始指南](https://agions.github.io/scene-fab/guide/quick-start)
- [配置参考](https://agions.github.io/scene-fab/config)
- [AI 模型参考](https://agions.github.io/scene-fab/ai-models)
