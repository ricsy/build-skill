"""tests/test_deps.py"""

from build_skill.deps import get_missing_packages


def test_get_missing_packages_empty_file(tmp_path):
    """空的 requirements.txt 返回空列表"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    assert missing == []


def test_get_missing_packages_with_comments(tmp_path):
    """包含注释行的 requirements.txt 正确解析"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("# 这是注释\ntyper==0.12.5\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    # typer 已安装所以不在缺失列表
    assert isinstance(missing, list)


def test_get_missing_packages_nonexistent_file():
    """不存在的 requirements.txt 返回空列表（跳过检查）"""
    missing = get_missing_packages("/nonexistent/requirements.txt")
    assert missing == []


def test_get_missing_packages_strips_version_constraints(tmp_path):
    """版本约束符号被正确剥离"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("typer>=0.12.0\npytest<3.0\nclick==0.7.0\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    # typer, pytest, click 都已安装，不在缺失列表
    assert missing == []


def test_get_missing_packages_skips_editable(tmp_path):
    """-e 本地编辑安装被跳过"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("-e ./local_pkg\ntyper==0.12.5\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    assert missing == []


def test_get_missing_packages_skips_git_deps(tmp_path):
    """git+ 直接安装被跳过"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("git+https://github.com/user/repo.git\ntyper==0.12.5\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    assert missing == []


def test_get_missing_packages_skips_empty_lines(tmp_path):
    """空行被跳过"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("\n\ntyper==0.12.5\n\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    assert missing == []


def test_get_missing_packages_with_dashes(tmp_path):
    """横杠包名正确转换为下划线用于 import 检查"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("pydantic-settings>=2.0.0\n", encoding="utf-8")
    missing = get_missing_packages(str(req_file))
    # pydantic-settings 不存在，转换后 import pydantic_settings 失败
    assert missing == ["pydantic-settings"]


def test_get_missing_packages_mixed_format(tmp_path):
    """混合多种格式的 requirements.txt 正确解析"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        "# header comment\n"
        "\n"
        "-e ./editable\n"
        "git+ssh://git@github.com/user/repo.git\n"
        "typer>=0.12.0\n"
        "requests<2.30.0\n"
        "click==0.7.0\n"
        "package-not-exist==1.0.0\n",
        encoding="utf-8",
    )
    missing = get_missing_packages(str(req_file))
    assert "package-not-exist" in missing
    assert "typer" not in missing
    assert "requests" not in missing
    assert "click" not in missing
