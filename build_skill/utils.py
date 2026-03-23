"""工具函数模块"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

from build_skill.config import get_config

if TYPE_CHECKING:
    from loguru import Logger

# loguru 懒加载
_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """获取或初始化 loguru logger 实例"""
    global _logger
    if _logger is not None:
        return _logger

    import loguru
    import sys

    logger = loguru.logger

    # 移除默认处理器
    logger.remove()

    # 过滤：WARNING→WARN，ERROR→ERR
    def _short_level_filter(record: loguru.Record) -> bool:
        level_map = {
            "WARNING": "WARN",
            "ERROR": "ERR.",
            "SUCCESS": "SUC.",
        }
        record["level"].name = level_map.get(record["level"].name, record["level"].name)
        return True

    cfg = get_config()
    level = "DEBUG" if cfg.debug.enabled else cfg.debug.log_level

    # stderr 输出（始终启用，带颜色）
    logger.add(
        sys.stderr,
        level=level,
        format="<level>[{time:YYYY-MM-DD HH:mm:ss}]</level> <level>[{level}]</level> <level>{message}</level>",
        colorize=True,
        filter=_short_level_filter,
    )

    _logger = logger
    return logger


def info(msg: Any, *args: object) -> None:
    """输出 INFO 级别日志"""
    _get_logger().info(msg, *args)


def warn(msg: Any, *args: object) -> None:
    """输出 WARNING 级别日志"""
    _get_logger().warning(msg, *args)


def error(msg: Any, *args: object) -> None:
    """输出 ERROR 级别日志"""
    _get_logger().error(msg, *args)


def success(msg: Any, *args: object) -> None:
    """输出成功日志"""
    _get_logger().success(msg, *args)


def is_debug() -> bool:
    """当前是否开启调试模式（读取 config.debug.enabled）"""
    return get_config().debug.enabled


def log_level() -> str:
    """获取当前日志级别"""
    return get_config().debug.log_level


def resolve_skill_name(skills_dir: Path, name: Optional[str] = None) -> str:
    """推断或使用指定的 skill 名称

    Args:
        skills_dir: skills/ 目录路径
        name: 可选，指定的 skill 名称

    Returns:
        skill 名称字符串

    Raises:
        ValueError: 未指定 name 且 skills/ 下无唯一子目录
    """
    if name is not None and name != "":
        return name

    # 自动推断：skills/ 下唯一子目录
    subdirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]

    if len(subdirs) == 1:
        return subdirs[0]

    if len(subdirs) == 0:
        raise ValueError("未找到 skill 目录，请用 --name 指定")

    raise ValueError(f"skills/ 下有多个子目录，请用 --name 指定: {subdirs}")


def get_version_from_file(
    init_file: str,
    version_regex: str = r'__version__\s*=\s*["\']([^"\']+)["\']',
) -> str:
    """从文件路径读取版本号，失败返回 "0.0.0"

    Args:
        init_file: 版本文件路径（可以是 __init__.py、pyproject.toml 等任意文件）
        version_regex: 提取版本号的正则（需有 1 个捕获组）
    """
    import re

    path = Path(init_file)
    if not path.exists():
        return "0.0.0"
    content = path.read_text(encoding="utf-8")
    match = re.search(version_regex, content)
    if match:
        return match.group(1)
    return "0.0.0"
