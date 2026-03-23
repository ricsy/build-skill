"""frontmatter 校验模块"""

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from build_skill.config import ValidationConfig


class BaseValidator:
    """校验器抽象基类"""

    def validate(self, skill_dir: Path) -> bool:
        """执行校验，返回是否通过"""
        raise NotImplementedError

    def get_issues(self) -> list[str]:
        """获取所有校验问题列表"""
        raise NotImplementedError


class FrontmatterSchema(BaseModel):
    """frontmatter 数据模板（Pydantic）"""

    name: str = Field(..., max_length=64)
    description: str = Field(..., max_length=1024)
    compatibility: Optional[str] = Field(default=None, max_length=500)

    # noinspection PyNestedDecorators
    @field_validator("name", mode="before")
    @classmethod
    def name_format(cls, v: str) -> str:
        """name 格式校验：仅允许小写字母、数字和连字符"""
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", v):
            raise ValueError(f"'{v}' 包含非法字符，仅允许小写字母、数字和连字符（禁止下划线）")
        return v


class FrontmatterValidator(BaseValidator):
    """frontmatter 校验器实现"""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config
        self._issues: list[str] = []
        self._schema: Optional[FrontmatterSchema] = None

    def validate(self, skill_dir: Path) -> bool:
        """读取 SKILL.md，解析 frontmatter，执行校验"""
        self._issues = []
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            self._issues.append(f"SKILL.md 不存在: {skill_file}")
            return False

        # 1. 读取并解析 frontmatter（YAML）
        try:
            fm = self._parse_frontmatter(skill_file)
        except Exception as e:
            self._issues.append(f"frontmatter 解析失败: {e}")
            return False

        # 2. Pydantic 模型校验
        try:
            self._schema = FrontmatterSchema.model_validate(fm)
        except Exception as e:
            self._issues.append(f"frontmatter 校验失败: {e}")
            return False

        # 3. 额外校验：name 与目录名一致
        if self._schema.name != skill_dir.name:
            self._issues.append(
                f"name 与目录名不匹配：frontmatter='{self._schema.name}' 目录='{skill_dir.name}'"
            )

        # 4. SKILL.md 行数检查
        lines = skill_file.read_text(encoding="utf-8").count("\n")
        if lines > self._config.skill_file_max_lines:
            self._issues.append(
                f"SKILL.md 超过 {self._config.skill_file_max_lines} 行"
                f"（共 {lines} 行），建议拆分到 references/ 目录"
            )

        return len(self._issues) == 0

    def get_issues(self) -> list[str]:
        return self._issues.copy()

    @staticmethod
    def _parse_frontmatter(skill_file: Path) -> dict[str, Any]:
        """从 SKILL.md 提取并解析 YAML frontmatter"""
        import yaml

        content = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            raise ValueError("frontmatter 格式错误：未找到 --- 分隔符")

        return yaml.safe_load(match.group(1)) or {}
