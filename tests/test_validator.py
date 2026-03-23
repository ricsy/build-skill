"""tests/test_validator.py"""

import pytest
from build_skill.validator import FrontmatterSchema, FrontmatterValidator
from build_skill.config import ValidationConfig


def test_name_format_valid():
    """name 格式正确（小写字母、数字、连字符）"""
    fm = FrontmatterSchema(name="openclaw-kb", description="A knowledge base")
    assert fm.name == "openclaw-kb"


def test_name_with_underscore_raises():
    """name 包含下划线时抛出 ValueError"""
    with pytest.raises(ValueError, match="禁止下划线"):
        FrontmatterSchema(name="openclaw_kb", description="Bad name")


def test_name_with_uppercase_raises():
    """name 包含大写字母时抛出 ValueError"""
    with pytest.raises(ValueError):
        FrontmatterSchema(name="OpenClaw", description="Bad name")


def test_name_starting_with_hyphen_raises():
    """name 以连字符开头时抛出 ValueError"""
    with pytest.raises(ValueError):
        FrontmatterSchema(name="-openclaw", description="Bad")


def test_description_max_length():
    """description 超过 max_length 时抛出 ValueError"""
    with pytest.raises(ValueError):
        FrontmatterSchema(name="test", description="x" * 1025)


def test_frontmatter_validator_valid(tmp_path):
    """有效的 SKILL.md 校验通过"""
    skill_dir = tmp_path / "skills" / "openclaw-kb"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: openclaw-kb\ndescription: A knowledge base\n---\n", encoding="utf-8"
    )
    cfg = ValidationConfig()
    validator = FrontmatterValidator(cfg)
    passed = validator.validate(skill_dir)
    assert passed is True
    assert validator.get_issues() == []


def test_frontmatter_validator_missing_skills_md(tmp_path):
    """SKILL.md 不存在时校验失败"""
    skill_dir = tmp_path / "skills" / "openclaw-kb"
    skill_dir.mkdir(parents=True)
    cfg = ValidationConfig()
    validator = FrontmatterValidator(cfg)
    passed = validator.validate(skill_dir)
    assert passed is False
    assert any("不存在" in issue for issue in validator.get_issues())


def test_frontmatter_validator_name_mismatch(tmp_path):
    """name 与目录名不匹配时校验失败"""
    skill_dir = tmp_path / "skills" / "openclaw-kb"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: wrong-name\ndescription: Wrong\n---\n", encoding="utf-8")
    cfg = ValidationConfig()
    validator = FrontmatterValidator(cfg)
    passed = validator.validate(skill_dir)
    assert passed is False
    assert any("不匹配" in issue for issue in validator.get_issues())
