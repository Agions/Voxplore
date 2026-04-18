---
title: 插件开发
description: 了解如何为 Voxplore 开发自定义插件，扩展核心功能。
---

# 插件开发指南

Voxplore 采用插件化架构，允许开发者通过插件扩展核心功能。

## 插件类型

Voxplore 支持四种插件类型：

| 类型 | 说明 | 接口 |
|------|------|------|
| **VideoProcessorPlugin** | 自定义视频处理器 | `process(video, params)` |
| **ExportPlugin** | 自定义导出格式 | `export(project, options)` |
| **AIGeneratorPlugin** | 自定义 AI 生成器 | `generate(context)` |
| **UIExtensionPlugin** | 自定义 UI 扩展 | `extend(ui_manager)` |

---

## 插件目录结构

```
plugins/
└── my-plugin/
    ├── __init__.py          # 插件入口
    ├── manifest.json         # 插件元数据
    ├── plugin.py             # 插件主逻辑
    ├── config.yaml           # 插件配置（可选）
    └── resources/            # 插件资源（可选）
        ├── icon.png
        └── styles.css
```

---

## 创建第一个插件

### 1. 创建插件目录

```bash
mkdir -p plugins/my-first-plugin
cd plugins/my-first-plugin
```

### 2. 编写 manifest.json

```json
{
  "name": "my-first-plugin",
  "version": "1.0.0",
  "display_name": "我的第一个插件",
  "description": "插件描述",
  "author": "你的名字",
  "license": "MIT",
  "plugin_type": "VideoProcessorPlugin",
  "min_app_version": "3.0.0",
  "entry_point": "plugin:MyPlugin",
  "dependencies": {
    "numpy": ">=1.20.0"
  }
}
```

### 3. 编写插件主逻辑

```python
# plugin.py
from narrafiilm.plugins import VideoProcessorPlugin

class MyPlugin(VideoProcessorPlugin):
    """我的第一个插件"""

    # 插件元数据
    name = "my-first-plugin"
    display_name = "我的第一个插件"

    def __init__(self):
        super().__init__()
        self.supported_formats = ['.mp4', '.mov']

    def process(self, video_path: str, params: dict) -> str:
        """
        处理视频

        Args:
            video_path: 输入视频路径
            params: 处理参数

        Returns:
            输出视频路径
        """
        output_path = params.get('output_dir', './output')

        # 在这里实现你的处理逻辑
        # ...

        return output_path

    def validate(self, video_path: str) -> bool:
        """验证视频文件是否可用"""
        import os
        return os.path.exists(video_path) and \
               os.path.splitext(video_path)[1] in self.supported_formats

    def get_params_schema(self) -> dict:
        """返回参数 schema，用于 UI 自动生成配置表单"""
        return {
            "brightness": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "label": "亮度"
            },
            "contrast": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "label": "对比度"
            }
        }
```

### 4. 导出插件类

```python
# __init__.py
from .plugin import MyPlugin

__all__ = ['MyPlugin']
```

---

## 插件加载与安装

### 开发模式安装

```bash
# 在项目根目录运行
python -m narrafiilm plugins install ./plugins/my-first-plugin
```

### 验证安装

```bash
python -m narrafiilm plugins list
```

输出：
```
✅ my-first-plugin (1.0.0) - 我的第一个插件 [已启用]
```

### 卸载插件

```bash
python -m narrafiilm plugins uninstall my-first-plugin
```

---

## 插件 API

### VideoProcessorPlugin

```python
class VideoProcessorPlugin:
    name: str                    # 插件唯一标识
    display_name: str            # 显示名称
    version: str                 # 版本号
    supported_formats: List[str] # 支持的视频格式

    def process(self, video_path: str, params: dict) -> str:
        """处理视频，返回输出路径"""
        ...

    def validate(self, video_path: str) -> bool:
        """验证视频文件"""
        ...

    def get_params_schema(self) -> dict:
        """返回参数 schema"""
        ...
```

### ExportPlugin

```python
class ExportPlugin:
    name: str
    display_name: str

    def export(self, project: Project, options: dict) -> str:
        """导出项目，返回导出文件路径"""
        ...

    def get_export_options(self) -> dict:
        """返回导出选项 schema"""
        ...
```

### AIGeneratorPlugin

```python
class AIGeneratorPlugin:
    name: str
    display_name: str

    def generate(self, context: dict) -> dict:
        """
        生成 AI 内容

        Args:
            context: 包含 video、audio、scene 等上下文信息

        Returns:
            生成结果 dict
        """
        ...

    def get_required_context(self) -> List[str]:
        """返回必需的上下文字段"""
        return ['video', 'audio']
```

### UIExtensionPlugin

```python
class UIExtensionPlugin:
    name: str
    display_name: str

    def extend(self, ui_manager: UIManager):
        """扩展 UI"""
        ...

    def get_menu_items(self) -> List[MenuItem]:
        """返回要添加的菜单项"""
        ...
```

---

## 安全机制

Voxplore 插件运行在受限制的环境中：

### 沙箱限制

| 限制项 | 说明 |
|--------|------|
| 文件访问 | 仅允许访问用户授权的目录 |
| 网络访问 | 可配置，默认为允许 HTTP/HTTPS |
| 系统命令 | 仅允许白名单内的命令 |
| 环境变量 | 插件只能访问有限的环境变量 |

### 签名验证

生产环境插件必须经过签名：

```bash
# 对插件进行签名
python -m narrafiilm plugins sign ./plugins/my-first-plugin
```

---

## 发布插件

### 打包插件

```bash
python -m narrafiilm plugins package ./plugins/my-first-plugin
```

生成文件：`my-first-plugin-1.0.0.vfplugin`

### 社区插件市场

（功能开发中）未来将在模板市场中支持社区插件分发。

---

## 调试技巧

### 启用调试日志

```python
import logging

logger = logging.getLogger('narrafiilm.plugins.my-first-plugin')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
```

### 在开发时热重载

```bash
python app/main.py --plugin-dev --plugin-path=./plugins/my-first-plugin
```

### 测试单个插件

```python
from narrafiilm.plugins.manager import PluginManager

manager = PluginManager()
manager.load_plugin('./plugins/my-first-plugin')

plugin = manager.get_plugin('my-first-plugin')
result = plugin.process('test_video.mp4', {'output_dir': './output'})
```

---

## 示例插件

完整的参考插件请参考项目中的示例：

```bash
ls examples/plugins/
# watermark-plugin/     # 水印插件示例
# subtitle-export/       # 自定义字幕导出插件
```

::: warning ⚠️ 注意
插件可以访问用户数据，请确保：
1. 不上传用户文件到第三方服务器（除非明确告知用户）
2. 不在代码中硬编码敏感信息
3. 遵循 Voxplore 的隐私政策
:::

::: tip 💡 提示
开发插件前建议先阅读 [架构概览](/architecture) 了解核心模块接口。
:::
