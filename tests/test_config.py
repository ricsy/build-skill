"""tests/test_config.py"""

from build_skill.config import AppConfig, DebugConfig, BuildConfig, PackConfig, ValidationConfig


def test_debug_config_defaults():
    """DebugConfig 默认值"""
    cfg = DebugConfig()
    assert cfg.enabled is False
    assert cfg.log_level == "INFO"


def test_build_config_defaults():
    """BuildConfig 默认值"""
    cfg = BuildConfig()
    assert cfg.default_skill == ""
    assert cfg.output_dir == "dist"
    assert cfg.skills_dir == "skills"


def test_pack_config_defaults():
    """PackConfig 默认值"""
    cfg = PackConfig()
    assert cfg.exclude_patterns == []
    assert cfg.config_patches == {}
    assert cfg.file_copy_rules == []
    assert cfg.version_file == "__init__.py"
    assert cfg.version_regex == r'__version__\s*=\s*["\']([^"\']+)["\']'
    assert cfg.skill_version_overrides == {}


def test_validation_config_defaults():
    """ValidationConfig 默认值"""
    cfg = ValidationConfig()
    assert cfg.name_max_len == 64
    assert cfg.desc_max_len == 1024
    assert cfg.compat_max_len == 500
    assert cfg.skill_file_max_lines == 500


def test_app_config_model_validate():
    """AppConfig Pydantic 模型校验"""
    data = {
        "build": {"default_skill": "openclaw-kb", "output_dir": "dist"},
        "debug": {"enabled": True, "log_level": "DEBUG"},
        "pack": {"exclude_patterns": ["__pycache__"]},
        "validation": {"name_max_len": 32},
    }
    cfg = AppConfig.model_validate(data)
    assert cfg.build.default_skill == "openclaw-kb"
    assert cfg.debug.enabled is True
    assert cfg.debug.log_level == "DEBUG"
    assert cfg.pack.exclude_patterns == ["__pycache__"]
    assert cfg.validation.name_max_len == 32


def test_app_config_empty_validation():
    """AppConfig 空数据使用默认值"""
    cfg = AppConfig.model_validate({})
    assert cfg.build.output_dir == "dist"
    assert cfg.debug.enabled is False


def test_pack_config_version_overrides():
    """PackConfig skill_version_overrides per-skill 配置"""
    cfg = PackConfig.model_validate(
        {
            "version_file": "pyproject.toml",
            "version_regex": r'version\s*=\s*"([^"]+)"',
            "skill_version_overrides": {
                "my-skill": {
                    "version_file": "__init__.py",
                },
                "other-skill": {
                    "version_regex": r'"version":\s*"([^"]+)"',
                },
            },
        }
    )
    assert cfg.version_file == "pyproject.toml"
    assert cfg.skill_version_overrides["my-skill"].version_file == "__init__.py"
    assert cfg.skill_version_overrides["my-skill"].version_regex is None
    assert cfg.skill_version_overrides["other-skill"].version_regex == r'"version":\s*"([^"]+)"'
    assert cfg.skill_version_overrides["other-skill"].version_file is None
