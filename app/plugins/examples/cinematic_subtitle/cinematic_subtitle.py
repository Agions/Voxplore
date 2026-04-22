"""
Cinematic Subtitle Plugin
电影感字幕插件 - 提供 ASS 格式的电影级字幕样式
"""

from typing import Dict, Any, List, Optional

from app.plugins.interfaces.export_plugin import BaseExportPlugin


class CinematicSubtitlePlugin(BaseExportPlugin):
    """
    电影感字幕生成插件

    支持的字幕样式:
    - cinematic: 电影黑底白色字幕
    - cinematic_intense: 情绪高潮版（带颜色）
    - minimal: 极简白字透明底
    - narration_only: 仅解说词字幕
    - bilingual: 双语字幕
    """

    def get_format_name(self) -> str:
        return "Cinematic ASS Subtitles"

    def get_file_extension(self) -> str:
        return ".ass"

    def get_export_options(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "style",
                "type": "select",
                "default": "cinematic",
                "choices": [
                    "cinematic",        # 电影黑底白字
                    "cinematic_intense", # 情绪版带颜色
                    "minimal",          # 极简透明底
                    "narration_only",   # 仅解说
                    "bilingual",        # 双语字幕
                ],
                "description": "字幕样式风格",
            },
            {
                "name": "font_size",
                "type": "number",
                "default": 48,
                "description": "字幕字体大小",
            },
            {
                "name": "primary_color",
                "type": "string",
                "default": "&H00FFFFFF",  # 白色
                "description": "主字幕颜色 (ASS 格式 BGR)",
            },
            {
                "name": "outline_color",
                "type": "string",
                "default": "&H00000000",  # 黑色描边
                "description": "描边颜色",
            },
            {
                "name": "outline_width",
                "type": "number",
                "default": 2.0,
                "description": "描边宽度",
            },
            {
                "name": "shadow_enabled",
                "type": "boolean",
                "default": True,
                "description": "是否启用阴影",
            },
            {
                "name": "position",
                "type": "select",
                "default": "bottom",
                "choices": ["bottom", "center", "top"],
                "description": "字幕位置",
            },
        ]

    def export(
        self,
        project_data: Dict[str, Any],
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        生成 ASS 字幕文件
        """
        opts = options or {}
        style = opts.get("style", "cinematic")
        font_size = opts.get("font_size", 48)
        primary_color = opts.get("primary_color", "&H00FFFFFF")
        outline_color = opts.get("outline_color", "&H00000000")
        outline_width = opts.get("outline_width", 2.0)
        shadow = opts.get("shadow_enabled", True)
        position = opts.get("position", "bottom")

        # 获取字幕数据
        subtitles = project_data.get("subtitles", [])
        if not subtitles:
            return False

        # 生成 ASS 内容
        ass_content = self._generate_ass(
            subtitles=subtitles,
            style=style,
            font_size=font_size,
            primary_color=primary_color,
            outline_color=outline_color,
            outline_width=outline_width,
            shadow=shadow,
            position=position,
        )

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return True

    def _generate_ass(
        self,
        subtitles: List[Dict[str, Any]],
        style: str,
        font_size: int,
        primary_color: str,
        outline_color: str,
        outline_width: float,
        shadow: bool,
        position: str,
    ) -> str:
        """生成 ASS 字幕内容"""

        # 风格参数映射
        style_params = self._get_style_params(style, font_size, primary_color, outline_color, outline_width, shadow)

        # 位置映射
        alignment = {
            "bottom": 2,   # 底部居中
            "center": 5,   # 居中
            "top": 8,      # 顶部居中
        }.get(position, 2)

        lines = []
        lines.append("[Script Info]")
        lines.append("Title: Voxplore Cinematic Subtitles")
        lines.append("ScriptType: v4.00+")
        lines.append("WrapStyle: 0")
        lines.append("ScaledBorderAndShadow: yes")
        lines.append(f"PlayResX: 1920")
        lines.append(f"PlayResY: 1080")
        lines.append("")

        lines.append("[V4+ Styles]")
        lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")

        # 主字幕样式
        style_line = (
            f"Style: Default,"
            f"{style_params['font_name']},"
            f"{font_size},"
            f"{primary_color},"
            f"{outline_color},"
            f"{'&H00000000' if shadow else '&H00000000'},"
            f"0,0,0,0,100,100,0,0,"
            f"{style_params['border_style']},"
            f"{outline_width},"
            f"{style_params['shadow']},"
            f"{alignment},"
            f"30,30,30,1"
        )
        lines.append(style_line)

        # 情绪版样式（带颜色）
        if style == "cinematic_intense":
            intense_style = (
                f"Style: Intense,"
                f"{style_params['font_name']},"
                f"{font_size},"
                f"&H00FFDD44,"   # 金色
                f"&H00000000,"
                f"&H00000000,"
                f"0,0,0,0,100,100,0,0,"
                f"1,2,3,"
                f"{alignment},"
                f"30,30,30,1"
            )
            lines.append(intense_style)

        lines.append("")

        lines.append("[Events]")
        lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        for sub in subtitles:
            start = sub.get("start", 0.0)
            end = sub.get("end", 0.0)
            text = sub.get("text", "")
            emotion = sub.get("emotion", "neutral")

            # 格式化时间
            start_ass = self._format_time_ass(start)
            end_ass = self._format_time_ass(end)

            # 选择样式
            sub_style = "Intense" if style == "cinematic_intense" and emotion in ("suspense", "motivational") else "Default"

            # 处理特殊符号
            text = text.replace("\\n", "\\N")

            line = f"Dialogue: 0,{start_ass},{end_ass},{sub_style},,0,0,0,,{text}"
            lines.append(line)

        return "\n".join(lines)

    def _get_style_params(
        self,
        style: str,
        font_size: int,
        primary_color: str,
        outline_color: str,
        outline_width: float,
        shadow: bool,
    ) -> Dict[str, Any]:
        """获取风格参数"""

        params = {
            "font_name": "Arial",
            "border_style": 1,  # 1=Outline, 3=Box
            "shadow": 1.0 if shadow else 0.0,
        }

        if style == "cinematic":
            params["font_name"] = "Arial"
            params["border_style"] = 1
            params["shadow"] = 1.5 if shadow else 0.0

        elif style == "minimal":
            params["font_name"] = "Arial"
            params["border_style"] = 1
            params["shadow"] = 0.0

        elif style == "bilingual":
            params["font_name"] = "Arial"
            params["border_style"] = 1
            params["shadow"] = 1.0 if shadow else 0.0

        return params

    def _format_time_ass(self, seconds: float) -> str:
        """将秒数转换为 ASS 时间格式 H:MM:SS.CC"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": "电影感 ASS 字幕生成，支持多种预设样式",
            "author": self.manifest.author,
            "styles": [
                {"id": "cinematic", "name": "电影黑底白字", "description": "经典电影字幕风格"},
                {"id": "cinematic_intense", "name": "情绪版", "description": "关键场景带颜色高亮"},
                {"id": "minimal", "name": "极简透明底", "description": "纯文字无背景"},
                {"id": "bilingual", "name": "双语字幕", "description": "中英双语上下排列"},
            ],
            "features": [
                "ASS 格式支持",
                "可调节描边和阴影",
                "情绪色彩高亮",
                "多种位置选项",
            ],
        }
