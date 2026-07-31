"""
Plugins Router
插件管理 API
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.plugins.interfaces.base import AppContext, PluginManifest, PluginType
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry, PluginState

router = APIRouter()

# 默认插件搜索目录
_DEFAULT_PLUGIN_DIR = Path.home() / ".scenefab" / "plugins"

# 模块级共享加载器（延迟初始化，保证发现/注册只执行一次）
_loader: PluginLoader | None = None


def _get_loader() -> PluginLoader:
    """
    获取共享插件加载器，首次调用时完成初始化：
    1. 添加默认插件目录（若存在）
    2. 发现插件清单
    3. 将每个清单注册到注册表
    """
    global _loader
    if _loader is not None:
        return _loader

    loader = PluginLoader()
    if _DEFAULT_PLUGIN_DIR.is_dir():
        loader.add_plugin_directory(str(_DEFAULT_PLUGIN_DIR))

    registry = loader.get_registry()
    # 设置应用上下文，确保插件初始化阶段能真正执行 instance.initialize()
    registry.set_context(AppContext(plugin_dir=str(_DEFAULT_PLUGIN_DIR)))
    for manifest in loader.discover_plugins():
        if manifest.id in registry:
            continue
        try:
            registry.register_plugin(manifest)
        except ValueError:
            # 清单校验失败或重复注册，跳过
            continue

    _loader = loader
    return loader


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    plugin_type: str
    enabled: bool
    capabilities: list[str]


class PluginListResponse(BaseModel):
    total: int
    plugins: list[PluginInfo]


class PluginEnableRequest(BaseModel):
    enabled: bool


def _to_plugin_info(manifest: PluginManifest, registry: PluginRegistry) -> PluginInfo:
    """将插件清单 + 注册表状态转换为 API 响应模型"""
    return PluginInfo(
        id=manifest.id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        plugin_type=manifest.plugin_type.value,
        enabled=registry.get_state(manifest.id) == PluginState.ENABLED,
        capabilities=list(manifest.tags),
    )


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins():
    """
    列出所有已发现的插件
    """
    try:
        registry = _get_loader().get_registry()
        manifests = registry.list_plugins()
        plugins = [_to_plugin_info(manifest, registry) for manifest in manifests]
        return PluginListResponse(total=len(plugins), plugins=plugins)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/types")
async def list_plugin_types():
    """
    列出所有支持的插件类型
    """
    try:
        return {
            "types": [
                {"value": t.value, "description": _type_description(t.value)}
                for t in PluginType
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plugins/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str):
    """
    获取指定插件详情
    """
    try:
        registry = _get_loader().get_registry()
        manifest = registry.get_manifest(plugin_id)
        if manifest is None:
            raise HTTPException(
                status_code=404, detail=f"Plugin '{plugin_id}' not found"
            )

        return _to_plugin_info(manifest, registry)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, request: PluginEnableRequest):
    """
    启用/禁用插件
    """
    try:
        registry = _get_loader().get_registry()

        if plugin_id not in registry:
            raise HTTPException(
                status_code=404, detail=f"Plugin '{plugin_id}' not found"
            )

        if request.enabled:
            state = registry.get_state(plugin_id)
            if state == PluginState.INSTALLED:
                registry.load_plugin(plugin_id)
                registry.initialize_plugin(plugin_id)
            elif state == PluginState.LOADED:
                registry.initialize_plugin(plugin_id)
            registry.enable_plugin(plugin_id)
        else:
            registry.disable_plugin(plugin_id)

        return {"plugin_id": plugin_id, "enabled": request.enabled}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _type_description(plugin_type: str) -> str:
    descriptions = {
        "AI_GENERATOR": "AI 内容生成器插件",
        "EXPORT_FORMAT": "视频导出格式插件",
        "UI_EXTENSION": "UI 扩展组件",
        "EFFECT_FILTER": "特效滤镜插件",
        "AUDIO_VOICE": "语音/配音插件",
        "VIDEO_DECODER": "视频解码插件",
    }
    return descriptions.get(plugin_type, "未知类型")


def _plugin_info_from_registry(plugin_id: str, reg_entry: dict) -> PluginInfo:
    """从 registry entry 构造 PluginInfo（list/single 共享）"""
    manifest = reg_entry.get("manifest", {})
    return PluginInfo(
        id=plugin_id,
        name=manifest.get("name", plugin_id),
        version=manifest.get("version", "0.0.0"),
        description=manifest.get("description", ""),
        plugin_type=manifest.get("plugin_type", "UNKNOWN"),
        enabled=reg_entry.get("enabled", False),
        capabilities=manifest.get("capabilities", []),
    )
