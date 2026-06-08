"""
异步子进程工具

为高频阻塞调用 (ffmpeg, ffprobe, version checks) 提供 async 接口。
不改变现有 sync API，仅作为可选优化路径。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_subprocess(
    cmd: Sequence[str],
    timeout: float | None = 30.0,
    check: bool = False,
) -> tuple[int, str, str]:
    """
    异步执行子进程并返回 (returncode, stdout, stderr)。

    Args:
        cmd: 命令列表
        timeout: 超时秒数 (None=无超时)
        check: True 时若返回非零码则 raise

    Returns:
        (returncode, stdout, stderr) 元组
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
        if check and proc.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}, stderr: {stderr_str}")
        return proc.returncode or 0, stdout_str, stderr_str
    except TimeoutError:
        logger.error(f"Subprocess timeout: {cmd}")
        raise
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0] if cmd else 'empty'}")
        raise


async def run_ffmpeg(args: Sequence[str], timeout: float = 300.0) -> int:
    """异步执行 ffmpeg 命令"""
    returncode, _, _ = await run_subprocess(["ffmpeg", *args], timeout=timeout)
    return returncode


async def run_ffprobe(
    video_path: str | Path,
    timeout: float = 30.0,
) -> dict[str, str]:
    """
    异步 ffprobe 探测视频元信息。

    Returns:
        解析后的 key=value 字典
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=width,height,r_frame_rate,codec_name",
        "-of", "default=noprint_wrappers=1",
        str(video_path),
    ]
    _, stdout, _ = await run_subprocess(cmd, timeout=timeout)
    return dict(
        line.split("=", 1)
        for line in stdout.splitlines() if "=" in line
    )


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """
    异步重试装饰器（指数退避）。

    替代 AI 重试循环中的 time.sleep 阻塞。

    Args:
        func: 异步函数
        max_attempts: 最大尝试次数
        delay: 初始延迟秒数
        backoff: 退避倍数
        exceptions: 触发重试的异常类型

    Returns:
        函数返回值
    """
    current_delay = delay
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_attempts:
                logger.error(f"Retry failed after {max_attempts} attempts: {e}")
                raise
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}, retrying in {current_delay}s")
            await asyncio.sleep(current_delay)
            current_delay *= backoff
    raise RuntimeError("unreachable")  # pragma: no cover
