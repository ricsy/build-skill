"""tests/test_validator.py"""

import pytest
from build_skill.validator import FileCopyRuleValidator, FrontmatterSchema, FrontmatterValidator
from build_skill.config import FileCopyRule, ValidationConfig


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


class TestFileCopyRuleValidator:
    """FileCopyRuleValidator 测试"""

    def test_type_in_scope_passes(self, tmp_path):
        """type 在 directory_scope 内时校验通过"""
        rules = [
            FileCopyRule.model_validate({"from": "src", "type": "scripts", "to": "src"}),
            FileCopyRule.model_validate({"from": "docs", "type": "references", "to": "doc"}),
            FileCopyRule.model_validate(
                {"from": "imgs", "type": "assets", "to": "images/logo.png"}
            ),
        ]
        validator = FileCopyRuleValidator(rules, ["scripts", "references", "assets"])
        assert validator.validate(tmp_path) is True
        assert validator.get_issues() == []

    def test_type_out_of_scope_fails(self, tmp_path):
        """type 不在 directory_scope 内时校验失败"""
        rules = [FileCopyRule.model_validate({"from": "src", "type": "other"})]
        validator = FileCopyRuleValidator(rules, ["scripts", "references", "assets"])
        assert validator.validate(tmp_path) is False
        issues = validator.get_issues()
        assert len(issues) == 1
        assert "other" in issues[0]
        assert "不在允许范围内" in issues[0]

    def test_multiple_type_out_of_scope_fails(self, tmp_path):
        """多个 type 都不在范围内时，全部报错"""
        rules = [
            FileCopyRule.model_validate({"from": "src", "type": "other"}),
            FileCopyRule.model_validate({"from": "docs", "type": "invalid"}),
        ]
        validator = FileCopyRuleValidator(rules, ["scripts", "references", "assets"])
        assert validator.validate(tmp_path) is False
        issues = validator.get_issues()
        assert len(issues) == 2

    def test_type_required(self, tmp_path):
        """type 为必填字段"""
        # type 是必填的，验证 ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FileCopyRule.model_validate({"from": "src"})

    def test_no_rules_passes(self, tmp_path):
        """file_copy_rules 为空时校验通过"""
        validator = FileCopyRuleValidator([], ["scripts", "references", "assets"])
        assert validator.validate(tmp_path) is True
        assert validator.get_issues() == []

    def test_custom_directory_scope(self, tmp_path):
        """自定义 directory_scope 生效"""
        rules = [
            FileCopyRule.model_validate({"from": "src", "type": "custom"}),
            FileCopyRule.model_validate({"from": "src", "type": "allowed"}),
        ]
        validator = FileCopyRuleValidator(rules, ["custom", "allowed"])
        assert validator.validate(tmp_path) is True

        # 不在范围内的仍会失败
        rules2 = [FileCopyRule.model_validate({"from": "src", "type": "forbidden"})]
        validator2 = FileCopyRuleValidator(rules2, ["custom", "allowed"])
        assert validator2.validate(tmp_path) is False

    def test_resolve_to_with_type_and_to(self, tmp_path):
        """type + to 组合解析正确"""
        rule = FileCopyRule.model_validate({"from": "src", "type": "scripts", "to": "lib"})
        assert rule.resolve_to() == "scripts/lib"

    def test_resolve_to_with_type_only(self, tmp_path):
        """仅有 type 时解析为 type 本身"""
        rule = FileCopyRule.model_validate({"from": "src", "type": "scripts"})
        assert rule.resolve_to() == "scripts"
