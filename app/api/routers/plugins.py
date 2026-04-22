"""
Plugins Router
插件管理 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    plugin_type: str
    enabled: bool
    capabilities: List[str]


class PluginListResponse(BaseModel):
    total: int
    plugins: List[PluginInfo]


class PluginEnableRequest(BaseModel):
    enabled: bool


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins():
    """
    列出所有已发现的插件
    """
    try:
        from app.plugins.loader import PluginLoader

        loader = PluginLoader()
        discovered = loader.discover_plugins()
        registry = loader.get_registry()

        plugins = []
        for pid in discovered:
            reg_entry = registry.get(pid, {})
            manifest = reg_entry.get("manifest", {})
            plugins.append(
                PluginInfo(
                    id=pid,
                    name=manifest.get("name", pid),
                    version=manifest.get("version", "0.0.0"),
                    description=manifest.get("description", ""),
                    plugin_type=manifest.get("plugin_type", "UNKNOWN"),
                    enabled=reg_entry.get("enabled", False),
                    capabilities=manifest.get("capabilities", []),
                )
            )

        return PluginListResponse(total=len(plugins), plugins=plugins)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str):
    """
    获取指定插件详情
    """
    try:
        from app.plugins.loader import PluginLoader

        loader = PluginLoader()
        registry = loader.get_registry()

        if plugin_id not in registry:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

        reg_entry = registry[plugin_id]
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, request: PluginEnableRequest):
    """
    启用/禁用插件
    """
    try:
        from app.plugins.loader import PluginLoader

        loader = PluginLoader()
        registry = loader.get_registry()

        if plugin_id not in registry:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

        registry[plugin_id]["enabled"] = request.enabled

        return {"plugin_id": plugin_id, "enabled": request.enabled}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/types")
async def list_plugin_types():
    """
    列出所有支持的插件类型
    """
    try:
        from app.plugins.interfaces.base import PluginType

        return {
            "types": [
                {"value": t.value, "description": _type_description(t.value)}
                for t in PluginType
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _type_description(plugin_type: str) -> str:
    descriptions = {
        "AI_GENERATOR": "AI 内容生成器插件",
        "EXPORT_FORMAT": "视频导出格式插件",
        "UI_EXTENSION": "UI 扩展组件",
        "EFFECT_FILTER": "特效滤镜插件",
        "SUBTITLE_STYLE": "字幕样式插件",
        "AUDIO_VOICE": "语音/配音插件",
        "VIDEO_DECODER": "视频解码插件",
    }
    return descriptions.get(plugin_type, "未知类型")
