#!/usr/bin/env python3
"""
回归测试: project_template_manager + highlight_detector 收紧 except Exception 后,
文件 IO / shutil / subprocess 错误仍正确处理, 但 RuntimeError/TypeError 不再被吞.

诚实性核心: 收紧后非预期异常 (RuntimeError 等真实编程 bug) 应该 raise,
而不再被 log 后吞掉 (掩盖 bug).
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# 1. project_template_manager.py:106 _load_templates JSON 加载
# =============================================================================


def test_load_templates_json_decode_error_logs_error(tmp_path):
    """JSON 解析失败 → log error, 不 crash"""
    from scenefab.project_template_manager import ProjectTemplateManager

    mgr = ProjectTemplateManager.__new__(ProjectTemplateManager)
    mgr.logger = MagicMock()
    mgr.templates = {}
    mgr.templates_dir = tmp_path

    # 创建一个无效 JSON 文件
    index_file = tmp_path / "templates.json"
    index_file.write_text("这不是 JSON, { 坏的格式")

    # JSONDecodeError 应该被 catch, 不 crash
    mgr._load_templates()


def test_load_templates_runtime_error_propagates(tmp_path):
    """★诚实性: _load_templates 中 RuntimeError 不再被吞"""
    from scenefab.project_template_manager import ProjectTemplateManager

    mgr = ProjectTemplateManager.__new__(ProjectTemplateManager)
    mgr.logger = MagicMock()
    mgr.templates = {}
    mgr.templates_dir = tmp_path

    # 模拟 TemplateInfo.from_dict 抛 RuntimeError
    with patch("scenefab.project_template_manager.TemplateInfo.from_dict",
               side_effect=RuntimeError("Code bug: bad template schema")):
        index_file = tmp_path / "templates.json"
        index_file.write_text('{"tpl1": {"id": "tpl1", "name": "test"}}')

        with pytest.raises(RuntimeError, match="Code bug"):
            mgr._load_templates()


# =============================================================================
# 2. project_template_manager.py:168 _calculate_directory_size os.walk
# =============================================================================


def test_calculate_directory_size_oserror_returns_zero(tmp_path):
    """os.walk OSError → return 0 (行为保持)"""
    from scenefab.project_template_manager import ProjectTemplateManager

    mgr = ProjectTemplateManager.__new__(ProjectTemplateManager)
    mgr.logger = MagicMock()

    with patch("os.walk", side_effect=OSError("Permission denied")):
        result = mgr._calculate_directory_size(tmp_path)
        assert result == 0


def test_calculate_directory_size_runtime_error_propagates(tmp_path):
    """★诚实性: _calculate_directory_size 中 RuntimeError 不再被吞"""
    from scenefab.project_template_manager import ProjectTemplateManager

    mgr = ProjectTemplateManager.__new__(ProjectTemplateManager)
    mgr.logger = MagicMock()

    with patch("os.walk", side_effect=RuntimeError("Code bug: bad walker")):
        with pytest.raises(RuntimeError, match="Code bug"):
            mgr._calculate_directory_size(tmp_path)


# =============================================================================
# 3. project_template_manager.py:351 _apply_variables_to_project
# =============================================================================


def test_apply_variables_runtime_error_propagates():
    """★诚实性: replace_variables 中 RuntimeError 不再被吞"""
    from scenefab.project_template_manager import ProjectTemplateManager

    mgr = ProjectTemplateManager.__new__(ProjectTemplateManager)
    mgr.logger = MagicMock()

    # 用一个 mock dict 让 .items() 抛 RuntimeError
    class BadDict(dict):
        def items(self):
            raise RuntimeError("Code bug: bad items")

    with pytest.raises(RuntimeError, match="Code bug"):
        mgr._apply_variables_to_project(BadDict({"k": "v"}), {"var": "x"})


# =============================================================================
# 4. highlight_detector.py:219 _run_ffmpeg
# =============================================================================


def test_run_ffmpeg_subprocess_error_returns_completed_process():
    """FFmpeg subprocess 失败 → CompletedProcess (returncode=1) (行为保持)"""
    from scenefab.services.video.highlight_detector import HighlightDetector

    detector = HighlightDetector.__new__(HighlightDetector)
    detector.config = MagicMock()

    with patch("scenefab.services.video.highlight_detector._get_executor") as mock_exec:
        mock_exec.return_value.run.side_effect = subprocess.SubprocessError("ffmpeg failed")

        result = detector._run_ffmpeg(["ffmpeg", "-i", "input.mp4"], timeout=10)

    assert result.returncode == 1
    assert "ffmpeg failed" in result.stderr


def test_run_ffmpeg_filenotfound_returns_completed_process():
    """FFmpeg 未安装 (FileNotFoundError) → CompletedProcess (returncode=1)"""
    from scenefab.services.video.highlight_detector import HighlightDetector

    detector = HighlightDetector.__new__(HighlightDetector)
    detector.config = MagicMock()

    with patch("scenefab.services.video.highlight_detector._get_executor") as mock_exec:
        mock_exec.return_value.run.side_effect = FileNotFoundError("ffmpeg not in PATH")

        result = detector._run_ffmpeg(["ffmpeg", "-i", "input.mp4"], timeout=10)

    assert result.returncode == 1


def test_run_ffmpeg_runtime_error_propagates():
    """★诚实性: FFmpeg 调用 RuntimeError 不再被吞"""
    from scenefab.services.video.highlight_detector import HighlightDetector

    detector = HighlightDetector.__new__(HighlightDetector)
    detector.config = MagicMock()

    with patch("scenefab.services.video.highlight_detector._get_executor") as mock_exec:
        mock_exec.return_value.run.side_effect = RuntimeError("Code bug: bad executor")

        with pytest.raises(RuntimeError, match="Code bug"):
            detector._run_ffmpeg(["ffmpeg", "-i", "input.mp4"], timeout=10)


def test_run_ffmpeg_security_error_blocked():
    """SecurityError (命令被拦截) → return CompletedProcess(1) + warning (行为保持)"""
    from scenefab.services.video.highlight_detector import HighlightDetector
    from scenefab.utils.security import SecurityError

    detector = HighlightDetector.__new__(HighlightDetector)
    detector.config = MagicMock()

    with patch("scenefab.services.video.highlight_detector._get_executor") as mock_exec:
        mock_exec.return_value.run.side_effect = SecurityError("command blocked")

        result = detector._run_ffmpeg(["rm", "-rf", "/"], timeout=10)

    assert result.returncode == 1
    assert "SecurityError" in result.stderr