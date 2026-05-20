#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 核心处理流水线
整合视频分析、选段、解说生成、配音合成
"""
import os
import time
import logging
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .models import (
    VideoSegment, EmotionPeak, NarrationBlock, SubtitleItem,
    AudioTrack, VideoProject, NarrationStyle, EmotionType, VideoGroup
)
from .video import VideoAnalyzer, VideoProcessor
from .ai_services import ai_service_manager, TTSService, ASRService

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """流水线配置"""
    min_segment_duration: float = 9.0
    max_segment_duration: float = 60.0
    frame_sample_interval: float = 1.0
    min_confidence: float = 0.6
    visual_weight: float = 0.7
    audio_weight: float = 0.3
    max_workers: int = 4


class EmotionPeakDetector:
    """
    情感峰值检测器
    基于视觉复杂度和音频能量分析
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
    
    def detect(
        self,
        segments: List[VideoSegment],
        progress_callback: Optional[Callable] = None
    ) -> List[EmotionPeak]:
        """
        检测情感峰值
        
        Args:
            segments: 视频片段列表
            progress_callback: 进度回调
            
        Returns:
            情感峰值列表（按评分降序）
        """
        peaks = []
        total = len(segments)
        
        for i, seg in enumerate(segments):
            # 视觉复杂度分析（使用帧差分）
            visual_score = self._analyze_visual_complexity(seg)
            
            # 音频情绪分析（基于音频能量）
            audio_score = self._analyze_audio_emotion(seg)
            
            # 综合评分
            peak_score = (
                self.config.visual_weight * visual_score +
                self.config.audio_weight * audio_score
            )
            
            # 判断峰值原因
            reason = self._determine_reason(visual_score, audio_score)
            
            peaks.append(EmotionPeak(
                segment=seg,
                peak_score=peak_score,
                reason=reason,
                visual_score=visual_score,
                audio_score=audio_score
            ))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        # 按评分降序排列
        peaks.sort(key=lambda p: p.peak_score, reverse=True)
        
        return peaks
    
    def _analyze_visual_complexity(self, segment: VideoSegment) -> float:
        """分析视觉复杂度"""
        try:
            import cv2
            import numpy as np
            
            # 采样分析
            cap = cv2.VideoCapture(segment.video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            start_frame = int(segment.start_time * fps)
            end_frame = int(segment.end_time * fps)
            
            sample_interval = max(1, int(fps * 0.5))  # 每0.5秒采样
            diffs = []
            prev_gray = None
            
            for f in range(start_frame, min(end_frame, start_frame + 100), sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ret, frame = cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        diff = np.mean(np.abs(gray.astype(float) - prev_gray.astype(float)))
                        diffs.append(diff)
                    prev_gray = gray
            
            cap.release()
            
            if diffs:
                avg_diff = np.mean(diffs)
                return min(1.0, avg_diff / 30.0)
            
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Visual analysis failed: {e}")
        
        # 回退：基于时间戳生成伪随机分数
        return 0.3 + (hash(f"{segment.video_path}{segment.start_time}") % 50) / 100.0
    
    def _analyze_audio_emotion(self, segment: VideoSegment) -> float:
        """分析音频情绪"""
        try:
            import librosa
            import numpy as np
            
            # 提取音频片段
            y, sr = librosa.load(
                segment.video_path,
                offset=segment.start_time,
                duration=segment.duration,
                sr=16000
            )
            
            if len(y) < sr:
                return 0.5
            
            # 计算能量
            energy = np.sum(y ** 2) / len(y)
            energy_norm = min(1.0, float(energy ** 0.5) * 5)
            
            # 计算音调
            try:
                pitches, _ = librosa.piptrack(y=y, sr=sr)
                pitch_max = [p[p > 0].max() for p in pitches.T if p[p > 0].size > 0]
                if pitch_max:
                    pitch_norm = min(1.0, np.mean(pitch_max) / 300.0)
                else:
                    pitch_norm = 0.5
            except:
                pitch_norm = 0.5
            
            # 综合情绪 = 能量 * 0.6 + 音调 * 0.4
            return energy_norm * 0.6 + pitch_norm * 0.4
            
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
        
        return 0.5
    
    def _determine_reason(self, visual: float, audio: float) -> str:
        """判断峰值原因"""
        if visual > audio * 1.5:
            if visual > 0.8:
                return "高复杂度场景，信息密度大"
            elif visual > 0.6:
                return "动作密度较高"
            else:
                return "画面信息丰富"
        elif audio > visual * 1.5:
            return "音频情绪强度高"
        else:
            if visual > 0.7 and audio > 0.7:
                return "视觉+音频双重高能"
            elif visual > 0.6:
                return "综合情感峰值"
            else:
                return "情感起伏明显"


class FirstPersonExtractor:
    """
    第一人称视角提取器
    使用视觉模型识别第一人称视角片段
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.emotion_detector = EmotionPeakDetector(config)
    
    def extract(
        self,
        video_path: str,
        group_id: str = "",
        use_cache: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[VideoSegment]:
        """
        提取第一人称片段
        
        Args:
            video_path: 视频路径
            group_id: 分组 ID
            use_cache: 是否使用缓存
            progress_callback: 进度回调
            
        Returns:
            第一人称片段列表（按置信度降序）
        """
        # 获取视频信息
        video_info = VideoAnalyzer.get_video_info(video_path)
        duration = video_info["duration"]
        
        # 生成采样时间点
        timestamps = self._generate_timestamps(duration)
        
        logger.info(f"Analyzing {len(timestamps)} frames in {video_path}")
        
        # 分析每帧
        first_person_frames = []
        ai_service = ai_service_manager
        
        for i, ts in enumerate(timestamps):
            result = self._analyze_frame(video_path, ts, ai_service.vision)
            
            if result and result.get("is_first_person") and result.get("confidence", 0) >= self.config.min_confidence:
                first_person_frames.append({
                    "timestamp": ts,
                    "confidence": result.get("confidence", 0),
                    "description": result.get("description", "")
                })
            
            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(i + 1, len(timestamps))
        
        # 聚类连续片段
        segments = self._cluster_frames(first_person_frames)
        
        # 过滤和验证
        segments = self._filter_segments(segments)
        
        # 设置分组 ID
        for seg in segments:
            seg.group_id = group_id
        
        return segments
    
    def _generate_timestamps(self, duration: float) -> List[float]:
        """生成采样时间点"""
        timestamps = []
        current = 0.0
        
        while current < duration:
            timestamps.append(current)
            current += self.config.frame_sample_interval
        
        return timestamps
    
    def _analyze_frame(
        self,
        video_path: str,
        timestamp: float,
        vision_service
    ) -> Optional[Dict[str, Any]]:
        """分析单帧"""
        # 提取帧
        frame = VideoAnalyzer.extract_frame(video_path, timestamp)
        
        if frame is None:
            return None
        
        # 如果有视觉服务，使用它
        if vision_service and vision_service.enabled:
            try:
                import cv2
                import numpy as np
                
                # 编码为 JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()
                
                return vision_service.analyze_frame(
                    frame_data,
                    prompt="分析这张图片：1)是否有第一人称视角(POV/主观镜头)？2)简要描述画面内容（10字以内）"
                )
            except Exception as e:
                logger.warning(f"Vision analysis failed: {e}")
        
        # 回退：模拟结果
        return self._mock_analysis(timestamp)
    
    def _mock_analysis(self, timestamp: float) -> Dict[str, Any]:
        """模拟分析结果"""
        import random
        
        hash_val = hash(f"{timestamp:.2f}")
        is_first_person = (hash_val % 10) < 3  # 30% 概率
        
        return {
            "is_first_person": is_first_person,
            "confidence": random.uniform(0.6, 0.9) if is_first_person else random.uniform(0.1, 0.4),
            "description": "第一人称街头漫步" if is_first_person else "第三人称观察"
        }
    
    def _cluster_frames(self, frames: List[Dict]) -> List[VideoSegment]:
        """聚类连续的第一人称帧"""
        if not frames:
            return []
        
        frames.sort(key=lambda f: f["timestamp"])
        
        segments = []
        current_start = frames[0]["timestamp"]
        current_conf = frames[0]["confidence"]
        current_desc = frames[0]["description"]
        last_time = frames[0]["timestamp"]
        
        for frame in frames[1:]:
            if frame["timestamp"] - last_time < 2.0:  # 连续
                current_conf = (current_conf + frame["confidence"]) / 2
                last_time = frame["timestamp"]
            else:
                # 保存片段
                segments.append(VideoSegment(
                    video_path="",
                    start_time=current_start,
                    end_time=last_time,
                    confidence=current_conf,
                    description=current_desc
                ))
                current_start = frame["timestamp"]
                current_conf = frame["confidence"]
                current_desc = frame["description"]
                last_time = frame["timestamp"]
        
        # 最后一个片段
        segments.append(VideoSegment(
            video_path="",
            start_time=current_start,
            end_time=last_time,
            confidence=current_conf,
            description=current_desc
        ))
        
        return segments
    
    def _filter_segments(self, segments: List[VideoSegment]) -> List[VideoSegment]:
        """过滤片段"""
        filtered = []
        
        for seg in segments:
            duration = seg.end_time - seg.start_time
            
            # 太短的丢弃
            if duration < 3.0:
                continue
            
            # 过长的拆分
            if duration > self.config.max_segment_duration:
                sub_segments = self._split_long_segment(seg)
                filtered.extend(sub_segments)
            else:
                filtered.append(seg)
        
        # 按置信度降序
        filtered.sort(key=lambda s: s.confidence, reverse=True)
        
        return filtered
    
    def _split_long_segment(self, segment: VideoSegment) -> List[VideoSegment]:
        """拆分过长片段"""
        duration = segment.end_time - segment.start_time
        num_splits = int(duration / self.config.max_segment_duration) + 1
        sub_duration = duration / num_splits
        
        subs = []
        for i in range(num_splits):
            subs.append(VideoSegment(
                video_path=segment.video_path,
                start_time=segment.start_time + i * sub_duration,
                end_time=segment.start_time + (i + 1) * sub_duration,
                confidence=segment.confidence,
                description=f"{segment.description} ({i+1}/{num_splits})"
            ))
        
        return subs


class ScriptGenerator:
    """
    解说文案生成器
    使用 LLM 生成第一人称解说文案
    """
    
    STYLE_PROMPTS = {
        NarrationStyle.HEALING: "温暖治愈的风格，像朋友在耳边轻声诉说",
        NarrationStyle.MYSTERIOUS: "神秘悬疑的风格，营造紧张氛围",
        NarrationStyle.INSPIRATIONAL: "励志激昂的风格，充满正能量",
        NarrationStyle.NOSTALGIC: "怀旧平静的风格，回忆往事",
        NarrationStyle.ROMANTIC: "浪漫温柔的风格，表达深情",
        NarrationStyle.HUMOROUS: "幽默活泼的风格，让人轻松愉快",
        NarrationStyle.DOCUMENTARY: "沉稳纪录片的风格，客观叙述",
    }
    
    def __init__(self, llm_service=None):
        self.llm = llm_service or ai_service_manager.get_llm()
    
    def generate(
        self,
        segments: List[VideoSegment],
        context: str = "",
        emotion: EmotionType = EmotionType.NEUTRAL,
        style: NarrationStyle = NarrationStyle.DOCUMENTARY,
        progress_callback: Optional[Callable] = None
    ) -> List[NarrationBlock]:
        """
        生成解说文案
        
        Args:
            segments: 视频片段
            context: 背景上下文
            emotion: 情感类型
            style: 叙事风格
            progress_callback: 进度回调
            
        Returns:
            解说块列表
        """
        if not self.llm:
            logger.warning("No LLM service available, using default script")
            return self._generate_default(len(segments))
        
        blocks = []
        total = len(segments)
        
        for i, seg in enumerate(segments):
            prompt = self._build_prompt(seg, context, emotion, style)
            
            try:
                result = self.llm.generate(
                    prompt=prompt,
                    system="你是一个专业的影视解说文案撰写师，擅长第一人称视角的叙事风格。"
                )
                
                if result:
                    text = result.strip()
                else:
                    text = self._get_default_text(i, style)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")
                text = self._get_default_text(i, style)
            
            # 计算时间分配
            total_duration = sum(s.end_time - s.start_time for s in segments)
            seg_ratio = (seg.end_time - seg.start_time) / max(0.001, total_duration)
            
            # 分配时间（按比例）
            start_time = seg.start_time
            end_time = seg.end_time
            
            blocks.append(NarrationBlock(
                text=text,
                start_time=start_time,
                end_time=end_time,
                emotion=emotion,
                style=style
            ))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return blocks
    
    def _build_prompt(
        self,
        segment: VideoSegment,
        context: str,
        emotion: EmotionType,
        style: NarrationStyle
    ) -> str:
        """构建提示词"""
        duration = segment.end_time - segment.start_time
        
        style_hint = self.STYLE_PROMPTS.get(style, "")
        
        prompt = f"""为以下视频片段撰写第一人称解说文案：

场景描述：{segment.description}
片段时长：约{duration:.0f}秒
情感基调：{emotion.value}
风格要求：{style_hint}
{f"背景上下文：{context}" if context else ""}

要求：
1. 第一人称"我"视角
2. {duration:.0f}秒时长，约{int(duration * 3)}个汉字
3. 符合指定风格和情感
4. 有画面感，像在现场一样叙述

解说文案："""
        
        return prompt
    
    def _generate_default(self, count: int) -> List[NarrationBlock]:
        """生成默认文案"""
        texts = [
            "这是我记忆中最深刻的时刻。",
            "那时候的我，还不知道接下来会发生什么。",
            "回想起来，一切都是最好的安排。",
            "有些事情，只有自己知道。",
            "那些藏在心底的话，从未对人说起。",
        ]
        
        return [
            NarrationBlock(
                text=texts[i % len(texts)],
                start_time=i * 10.0,
                end_time=(i + 1) * 10.0,
                emotion=EmotionType.NEUTRAL,
                style=NarrationStyle.DOCUMENTARY
            )
            for i in range(count)
        ]
    
    def _get_default_text(self, index: int, style: NarrationStyle) -> str:
        """获取默认文本"""
        defaults = {
            NarrationStyle.HEALING: "那一刻，温暖涌上心头。",
            NarrationStyle.MYSTERIOUS: "事情的真相，远比想象复杂。",
            NarrationStyle.INSPIRATIONAL: "只要坚持，一切皆有可能！",
            NarrationStyle.NOSTALGIC: "时光荏苒，回忆依旧。",
            NarrationStyle.ROMANTIC: "那一刻，心跳加速。",
            NarrationStyle.HUMOROUS: "没想到，事情会这样发展！",
            NarrationStyle.DOCUMENTARY: "这就是当时的情况。",
        }
        return defaults.get(style, "继续讲述...")


class TTSGenerator:
    """
    TTS 配音生成器
    """
    
    def __init__(self, tts_service: TTSService = None):
        self.tts = tts_service or ai_service_manager.tts or TTSService()
    
    def generate(
        self,
        narrations: List[NarrationBlock],
        output_dir: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        progress_callback: Optional[Callable] = None
    ) -> AudioTrack:
        """
        生成配音
        
        Args:
            narrations: 解说块列表
            output_dir: 输出目录
            voice: 语音名称
            progress_callback: 进度回调
            
        Returns:
            音频轨道
        """
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        audio_files = []
        total_duration = 0.0
        
        for i, narration in enumerate(narrations):
            text = narration.text
            output_path = os.path.join(output_dir, f"narration_{i:03d}.mp3")
            
            # 计算语速
            duration = narration.end_time - narration.start_time
            text_duration = len(text) / 5.0  # 估算
            rate = max(0.5, min(2.0, text_duration / duration))
            
            result = self.tts.generate_speech(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate
            )
            
            if result and os.path.exists(result):
                audio_files.append(result)
                total_duration += duration
            else:
                logger.warning(f"TTS generation failed for block {i}")
            
            if progress_callback:
                progress_callback(i + 1, len(narrations))
        
        # 合并音频
        final_audio = os.path.join(output_dir, "final_narration.mp3")
        
        if len(audio_files) == 1:
            import shutil
            shutil.copy(audio_files[0], final_audio)
        elif len(audio_files) > 1:
            self._concatenate_audio(audio_files, final_audio)
        else:
            logger.error("No audio files generated")
            return None
        
        return AudioTrack(
            audio_path=final_audio,
            duration=total_duration,
            voice=voice,
            rate=1.0
        )
    
    def _concatenate_audio(self, audio_files: List[str], output_path: str) -> bool:
        """合并音频文件"""
        try:
            import subprocess
            
            # 创建文件列表
            list_file = output_path + ".list.txt"
            with open(list_file, 'w') as f:
                for af in audio_files:
                    f.write(f"file '{af}'\n")
            
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path
            ], capture_output=True, check=True)
            
            os.remove(list_file)
            return True
            
        except Exception as e:
            logger.error(f"Audio concatenation failed: {e}")
            return False


class VoxplorePipeline:
    """
    Voxplore 核心处理流水线
    整合所有处理步骤
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.extractor = FirstPersonExtractor(config)
        self.emotion_detector = EmotionPeakDetector(config)
        self.script_generator = ScriptGenerator()
        self.tts_generator = TTSGenerator()
    
    def process(
        self,
        video_path: str,
        context: str = "",
        emotion: EmotionType = EmotionType.NEUTRAL,
        style: NarrationStyle = NarrationStyle.DOCUMENTARY,
        voice: str = "zh-CN-XiaoxiaoNeural",
        progress_callback: Optional[Callable] = None,
        output_dir: str = None
    ) -> VideoProject:
        """
        处理视频
        
        Args:
            video_path: 视频路径
            context: 背景上下文
            emotion: 情感类型
            style: 叙事风格
            voice: 配音语音
            progress_callback: 进度回调
            output_dir: 输出目录
            
        Returns:
            视频项目
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(video_path), "output")
        
        project = VideoProject(
            name=os.path.basename(video_path),
            source_videos=[video_path],
            style=style,
            emotion=emotion
        )
        
        def report(progress: float, message: str):
            if progress_callback:
                progress_callback(progress, message)
        
        try:
            # Step 1: 提取第一人称片段
            report(0.1, "正在分析视频...")
            segments = self.extractor.extract(
                video_path,
                use_cache=True,
                progress_callback=lambda c, t: report(0.1 + 0.2 * c / t, "正在提取第一人称片段...")
            )
            project.segments = segments
            report(0.3, f"找到 {len(segments)} 个片段")
            
            if not segments:
                logger.warning("No first-person segments found")
                return project
            
            # Step 2: 检测情感峰值
            report(0.35, "正在分析情感峰值...")
            peaks = self.emotion_detector.detect(
                segments,
                progress_callback=lambda c, t: report(0.35 + 0.15 * c / t, "正在分析情感...")
            )
            project.emotion_peaks = peaks
            report(0.5, f"找到 {len(peaks)} 个情感峰值")
            
            # Step 3: 生成解说文案
            report(0.55, "正在生成解说文案...")
            narrations = self.script_generator.generate(
                segments,
                context=context,
                emotion=emotion,
                style=style,
                progress_callback=lambda c, t: report(0.55 + 0.2 * c / t, "正在撰写文案...")
            )
            project.narration_blocks = narrations
            report(0.75, "文案生成完成")
            
            # Step 4: 生成配音
            report(0.8, "正在生成配音...")
            audio_track = self.tts_generator.generate(
                narrations,
                output_dir=output_dir,
                voice=voice,
                progress_callback=lambda c, t: report(0.8 + 0.15 * c / t, "正在合成语音...")
            )
            if audio_track:
                project.audio_track = audio_track
            report(0.95, "配音生成完成")
            
            report(1.0, "处理完成！")
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            raise
        
        return project


__all__ = [
    "PipelineConfig",
    "EmotionPeakDetector",
    "FirstPersonExtractor",
    "ScriptGenerator",
    "TTSGenerator",
    "VoxplorePipeline",
]
