"""配置加载模块"""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class DebugConfig(BaseModel):
    """debug 模式配置"""

    enabled: bool = False
    log_level: str = "INFO"


class BuildConfig(BaseModel):
    """构建相关配置"""

    skills_dir: str = "skills"
    default_skill: str = ""
    output_dir: str = "dist"


class FileCopyRule(BaseModel):
    """文件复制规则"""

    from_: str = Field(alias="from")
    type: str  # 顶层目录，必须在 directory_scope 白名单内
    to: Optional[str] = None  # 子路径（相对于 type），默认为 from_
    glob: Optional[str] = None

    model_config = {"populate_by_name": True}

    def resolve_to(self) -> str:
        """解析完整的目标路径：type/to（to 省略时用 from_）"""
        if self.to:
            return f"{self.type}/{self.to}"
        return self.type


class SkillVersionConfig(BaseModel):
    """skill 级别版本读取配置（覆盖全局默认）"""

    version_file: Optional[str] = None
    version_regex: Optional[str] = None


class PackConfig(BaseModel):
    """打包相关配置"""

    exclude_patterns: list[str] = []
    config_patches: dict[str, dict[str, str]] = {}
    file_copy_rules: list[FileCopyRule] = []
    version_file: str = "__init__.py"
    version_regex: str = r'__version__\s*=\s*["\']([^"\']+)["\']'
    skill_version_overrides: dict[str, SkillVersionConfig] = {}


class ValidationConfig(BaseModel):
    """校验相关配置"""

    name_max_len: int = 64
    desc_max_len: int = 1024
    compat_max_len: int = 500
    skill_file_max_lines: int = 500
    directory_scope: list[str] = ["scripts", "references", "assets"]


class AppConfig(BaseModel):
    """全局配置"""

    build: BuildConfig = BuildConfig()
    debug: DebugConfig = DebugConfig()
    pack: PackConfig = PackConfig()
    validation: ValidationConfig = ValidationConfig()

    @classmethod
    def load(cls, path: Optional[str | Path] = None) -> "AppConfig":
        """从 YAML 文件加载配置

        搜索路径（优先级从高到低）：
        1. 传入的 path 参数
        2. 环境变量 BUILD_SKILL_CONFIG
        3. 当前目录 .build_skill.yaml（用户项目根目录）
        4. XDG 配置目录（Linux: ~/.config/build-skill/config.yaml）
        5. 包内默认配置（仅作为最后回退）
        """
        import os

        def _load_yaml(p: Path) -> Optional[dict[str, Any]]:
            """从指定路径加载 YAML 文件"""
            if p.exists():
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return None

        # 优先级 1：显式指定
        if path is not None:
            p = Path(path)
            data = _load_yaml(p)
            if data is not None:
                return cls.model_validate(data)
            raise FileNotFoundError(f"配置文件不存在: {p}")

        # 优先级 2：环境变量
        env_path = os.environ.get("BUILD_SKILL_CONFIG")
        if env_path:
            data = _load_yaml(Path(env_path))
            if data is not None:
                return cls.model_validate(data)

        # 优先级 3：当前目录
        data = _load_yaml(Path(".build_skill.yaml"))
        if data is not None:
            return cls.model_validate(data)

        # 优先级 4：XDG 配置目录
        xdg_path = Path(os.path.expanduser("~/.config/build-skill/config.yaml"))
        data = _load_yaml(xdg_path)
        if data is not None:
            return cls.model_validate(data)

        # 优先级 5：包内默认配置
        return cls.model_validate({})


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置（惰性加载）"""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config
