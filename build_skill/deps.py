"""Python 依赖检查模块"""

import re
from pathlib import Path

from build_skill.utils import info, warn


def get_missing_packages(req_file: str = "requirements.txt") -> list[str]:
    """获取未安装的依赖包列表

    Args:
        req_file: requirements.txt 文件路径

    Returns:
        未安装的包名列表（空列表表示全部已安装）

    支持的格式：
        requests>=2.28.0
        numpy<2.0
        pandas==1.5.0
        package-name（含横杠，自动转换为下划线用于 import 检查）

    跳过的格式：
        # 注释行
        -e git+https://...
        git+ssh://...
        (空行)
    """
    req_path = Path(req_file)
    if not req_path.exists():
        return []

    missing: list[str] = []
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # 跳过：空行、注释、-e（本地编辑安装）、git+（git 直接安装）
        if not line or line.startswith("#") or line.startswith("-e") or line.startswith("git"):
            continue

        # 去掉版本约束: pkg>=1.0 -> pkg
        pkg = re.sub(r"[<>=!~].*$", "", line).strip()
        if not pkg:
            continue

        # 将横杠替换为下划线用于 import 检查（pkg-name -> pkg_name）
        import_name = pkg.replace("-", "_")
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)

    return missing


def check_dependencies(req_file: str = "requirements.txt") -> bool:
    """检查依赖是否全部安装

    Returns:
        True 全部安装，False 有缺失
    """
    missing = get_missing_packages(req_file)
    if missing:
        warn(f"缺少以下依赖: {missing}")
        warn("请运行: pip install -r requirements.txt")
        return False
    info("所有依赖已安装")
    return True
