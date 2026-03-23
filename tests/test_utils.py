"""tests/test_utils.py"""

import pytest
from build_skill.utils import resolve_skill_name, get_version_from_file


def test_get_version_from_file(tmp_path):
    """get_version_from_file 从 __init__.py 读取 __version__"""
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "1.2.3"', encoding="utf-8")
    v = get_version_from_file(str(init_file))
    assert v == "1.2.3"


def test_get_version_from_file_missing(tmp_path):
    """get_version_from_file 文件不存在时返回 0.0.0"""
    v = get_version_from_file(str(tmp_path / "nonexistent.py"))
    assert v == "0.0.0"


def test_get_version_from_file_no_version(tmp_path):
    """get_version_from_file 无 __version__ 时返回 0.0.0"""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("# no version here", encoding="utf-8")
    v = get_version_from_file(str(init_file))
    assert v == "0.0.0"


def test_get_version_from_file_custom_regex(tmp_path):
    """get_version_from_file 使用自定义正则提取版本"""
    init_file = tmp_path / "pyproject.toml"
    init_file.write_text('version = "2.0.0"\nname = "my-skill"', encoding="utf-8")
    v = get_version_from_file(str(init_file), r'version\s*=\s*"([^"]+)"')
    assert v == "2.0.0"


def test_get_version_from_file_single_quotes(tmp_path):
    """get_version_from_file 支持单引号版本号"""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("__version__ = '3.5.0'", encoding="utf-8")
    v = get_version_from_file(str(init_file))
    assert v == "3.5.0"


def test_resolve_skill_name_from_arg(tmp_path):
    """指定 name 时直接返回"""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    result = resolve_skill_name(skills_dir, "my-skill")
    assert result == "my-skill"


def test_resolve_skill_name_single_subdir(tmp_path):
    """skills/ 下唯一子目录时自动推断"""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "openclaw-kb").mkdir()
    result = resolve_skill_name(skills_dir, None)
    assert result == "openclaw-kb"


def test_resolve_skill_name_no_subdir(tmp_path):
    """skills/ 为空且未指定 name 时抛出 ValueError"""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    with pytest.raises(ValueError, match="请用 --name 指定"):
        resolve_skill_name(skills_dir, None)


def test_resolve_skill_name_multiple_subdirs(tmp_path):
    """skills/ 下多个子目录且未指定 name 时抛出 ValueError"""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "skill-a").mkdir()
    (skills_dir / "skill-b").mkdir()
    with pytest.raises(ValueError, match="请用 --name 指定"):
        resolve_skill_name(skills_dir, None)
