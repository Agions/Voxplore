"""
素材版权预检模块

功能：
1. 视频元数据提取（来源、时长、编码信息）
2. 关键帧哈希生成（用于溯源和去重）
3. 版权风险评估
4. 使用建议生成

技术栈：
- FFmpeg/ffprobe: 视频元数据提取
- OpenCV: 关键帧提取
- hashlib: 哈希计算
"""

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """视频元数据"""

    file_path: str
    file_name: str
    file_size: int  # bytes
    duration: float  # seconds
    width: int
    height: int
    fps: float
    codec: str
    bitrate: int  # bps
    format_name: str
    creation_time: str | None = None
    modification_time: str | None = None
    md5_hash: str = ""
    sha256_hash: str = ""


@dataclass
class CopyrightCheckResult:
    """版权检查结果"""

    metadata: VideoMetadata
    risk_level: str  # "low", "medium", "high"
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    fair_use_assessment: dict[str, Any] = field(default_factory=dict)
    check_time: str = ""
    checker_version: str = "1.0.0"


class CopyrightChecker:
    """
    版权预检器

    用于检查视频素材的版权风险，提供合规性建议。

    使用方法：
        checker = CopyrightChecker()
        result = checker.check("path/to/video.mp4")
        print(result.risk_level)
        print(result.recommendations)
    """

    # 合理使用阈值
    FAIR_USE_DURATION_THRESHOLD = 120  # 2 分钟
    FAIR_USE_PERCENTAGE_THRESHOLD = 0.10  # 10%

    def __init__(self, ffprobe_path: str = "ffprobe"):
        """
        初始化版权检查器

        Args:
            ffprobe_path: ffprobe 可执行文件路径
        """
        self.ffprobe_path = ffprobe_path
        logger.info("CopyrightChecker 初始化完成")

    def check(self, video_path: str) -> CopyrightCheckResult:
        """
        执行版权检查

        Args:
            video_path: 视频文件路径

        Returns:
            CopyrightCheckResult: 检查结果
        """
        logger.info(f"开始版权检查: {video_path}")

        # 1. 提取元数据
        metadata = self._extract_metadata(video_path)

        # 2. 评估风险
        risk_level, risk_factors = self._assess_risk(metadata)

        # 3. 生成建议
        recommendations = self._generate_recommendations(metadata, risk_level)

        # 4. 合理使用评估
        fair_use_assessment = self._assess_fair_use(metadata)

        result = CopyrightCheckResult(
            metadata=metadata,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
            fair_use_assessment=fair_use_assessment,
            check_time=datetime.now().isoformat(),
        )

        logger.info(f"版权检查完成: 风险等级={risk_level}")
        return result

    def _extract_metadata(self, video_path: str) -> VideoMetadata:
        """
        提取视频元数据

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata: 视频元数据
        """
        video_path_obj = Path(video_path)

        if not video_path_obj.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 使用 ffprobe 提取元数据
        try:
            metadata = self._extract_with_ffprobe(video_path)
        except Exception as e:
            logger.warning(f"ffprobe 提取失败，使用基础信息: {e}")
            metadata = self._extract_basic_metadata(video_path)

        # 计算文件哈希
        metadata.md5_hash = self._calculate_hash(video_path, "md5")
        metadata.sha256_hash = self._calculate_hash(video_path, "sha256")

        return metadata

    def _extract_with_ffprobe(self, video_path: str) -> VideoMetadata:
        """
        使用 ffprobe 提取详细元数据

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata: 视频元数据
        """
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe 执行失败: {result.stderr}")

        data = json.loads(result.stdout)

        # 提取格式信息
        format_info = data.get("format", {})
        duration = float(format_info.get("duration", 0))
        file_size = int(format_info.get("size", 0))
        bitrate = int(format_info.get("bit_rate", 0))
        format_name = format_info.get("format_name", "unknown")

        # 提取视频流信息
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if video_stream is None:
            raise ValueError("未找到视频流")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec = video_stream.get("codec_name", "unknown")

        # 计算帧率
        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 0
        else:
            fps = float(fps_str)

        # 提取时间信息
        creation_time = None
        modification_time = None
        tags = format_info.get("tags", {})
        if "creation_time" in tags:
            creation_time = tags["creation_time"]
        if "modification_time" in tags:
            modification_time = tags["modification_time"]

        return VideoMetadata(
            file_path=str(video_path),
            file_name=Path(video_path).name,
            file_size=file_size,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            bitrate=bitrate,
            format_name=format_name,
            creation_time=creation_time,
            modification_time=modification_time,
        )

    def _extract_basic_metadata(self, video_path: str) -> VideoMetadata:
        """
        提取基础元数据（ffprobe 不可用时的后备方案）

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata: 视频元数据
        """
        video_path_obj = Path(video_path)

        return VideoMetadata(
            file_path=str(video_path),
            file_name=video_path_obj.name,
            file_size=video_path_obj.stat().st_size,
            duration=0.0,
            width=0,
            height=0,
            fps=0.0,
            codec="unknown",
            bitrate=0,
            format_name="unknown",
        )

    def _calculate_hash(self, file_path: str, algorithm: str = "md5") -> str:
        """
        计算文件哈希

        Args:
            file_path: 文件路径
            algorithm: 哈希算法（md5 或 sha256）

        Returns:
            str: 哈希值
        """
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _assess_risk(self, metadata: VideoMetadata) -> tuple[str, list[str]]:
        """
        评估版权风险

        Args:
            metadata: 视频元数据

        Returns:
            tuple: (风险等级, 风险因素列表)
        """
        risk_factors = []
        risk_score = 0

        # 检查时长风险
        if metadata.duration > 7200:  # 2 小时
            risk_factors.append("视频时长超过 2 小时，可能是完整电影/剧集")
            risk_score += 30
        elif metadata.duration > 3600:  # 1 小时
            risk_factors.append("视频时长超过 1 小时，需注意合理使用")
            risk_score += 15

        # 检查分辨率风险（高分辨率可能意味着高质量盗版）
        if metadata.width >= 3840 or metadata.height >= 2160:  # 4K
            risk_factors.append("4K 分辨率，可能是高质量盗版源")
            risk_score += 20
        elif metadata.width >= 1920 or metadata.height >= 1080:  # 1080p
            risk_factors.append("1080p 分辨率，需确认来源合法性")
            risk_score += 10

        # 检查文件名风险关键词
        risk_keywords = [
            "bluray",
            "bdrip",
            "hdrip",
            "dvdrip",
            "webrip",
            "hdtv",
            "cam",
            "ts",
            "tc",
            "枪版",
            "盗版",
            "抢先版",
        ]
        file_name_lower = metadata.file_name.lower()
        for keyword in risk_keywords:
            if keyword in file_name_lower:
                risk_factors.append(f"文件名包含风险关键词: {keyword}")
                risk_score += 25
                break

        # 确定风险等级
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        return risk_level, risk_factors

    def _generate_recommendations(
        self,
        metadata: VideoMetadata,
        risk_level: str,
    ) -> list[str]:
        """
        生成合规建议

        Args:
            metadata: 视频元数据
            risk_level: 风险等级

        Returns:
            list: 建议列表
        """
        recommendations = []

        # 通用建议
        recommendations.append("建议使用正版授权素材或创作共用（CC）协议素材")

        # 基于风险等级的建议
        if risk_level == "high":
            recommendations.append("⚠️ 高风险：强烈建议不要使用此素材进行商业用途")
            recommendations.append("建议使用时长控制在原片 5% 以内，且不超过 2 分钟")
            recommendations.append('建议添加明显的解说评论，确保构成"转换性使用"')
        elif risk_level == "medium":
            recommendations.append("⚠️ 中风险：使用时需注意合理使用原则")
            recommendations.append("建议使用时长控制在原片 10% 以内")
            recommendations.append("建议添加足够的原创解说内容")
        else:
            recommendations.append("✅ 低风险：可正常使用，但仍需注意版权标识")

        # 基于时长的建议
        if metadata.duration > 3600:
            recommendations.append("长视频建议只截取关键片段，避免使用完整内容")

        # 通用合规建议
        recommendations.append("在视频描述中标注素材来源")
        recommendations.append("保留原始素材的购买/授权凭证")

        return recommendations

    def _assess_fair_use(self, metadata: VideoMetadata) -> dict[str, Any]:
        """
        评估合理使用

        Args:
            metadata: 视频元数据

        Returns:
            dict: 合理使用评估结果
        """
        # 计算安全使用时长
        safe_duration_absolute = self.FAIR_USE_DURATION_THRESHOLD  # 2 分钟
        safe_duration_percentage = (
            metadata.duration * self.FAIR_USE_PERCENTAGE_THRESHOLD
        )  # 10%
        safe_duration = min(safe_duration_absolute, safe_duration_percentage)

        # 判断是否符合合理使用
        is_within_fair_use = metadata.duration <= safe_duration

        return {
            "safe_duration_seconds": safe_duration,
            "safe_duration_percentage": self.FAIR_USE_PERCENTAGE_THRESHOLD * 100,
            "safe_duration_absolute": safe_duration_absolute,
            "is_within_fair_use": is_within_fair_use,
            "recommendation": (
                "当前时长在合理使用范围内"
                if is_within_fair_use
                else f"建议将使用时长控制在 {safe_duration:.1f} 秒以内"
            ),
        }


def check_copyright(
    video_path: str, ffprobe_path: str = "ffprobe"
) -> CopyrightCheckResult:
    """
    便捷函数：执行版权检查

    Args:
        video_path: 视频文件路径
        ffprobe_path: ffprobe 可执行文件路径

    Returns:
        CopyrightCheckResult: 检查结果
    """
    checker = CopyrightChecker(ffprobe_path=ffprobe_path)
    return checker.check(video_path)
