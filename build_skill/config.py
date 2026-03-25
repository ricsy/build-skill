"""配置加载模块"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from path_config import load_config


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
        """解析完整的目标路径：type/to（to 省略时为 type）"""
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
        if path is not None:
            from path_config.loaders import YamlLoader

            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"配置文件不存在: {p}")
            data = YamlLoader().load(str(p))
            return cls.model_validate(data)

        data = load_config(
            name=".build_skill.yaml",
            xdg="build-skill/config.yaml",
            env="BUILD_SKILL_CONFIG",
            default={},
        )
        return cls.model_validate(data)


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置（惰性加载）"""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config
