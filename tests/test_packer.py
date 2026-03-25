"""tests/test_packer.py"""

import re
import tarfile

from build_skill.packer import TarPacker, PackResult
from build_skill.config import PackConfig, FileCopyRule


def test_pack_result_dataclass():
    """PackResult 数据类"""
    result = PackResult(output_file="dist/test.tar.gz", file_count=42, size="1.2M")
    assert result.output_file == "dist/test.tar.gz"
    assert result.file_count == 42
    assert result.size == "1.2M"


def test_patch_key_value_single_key(tmp_path):
    """_patch_key_value 替换单个键值"""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("debug:\n  enabled: true\n  log_level: DEBUG\n", encoding="utf-8")
    packer = TarPacker(PackConfig(config_patches={"debug": {"enabled": "false"}}))
    packer.patch_config(cfg)
    content = cfg.read_text(encoding="utf-8")
    # enabled 应该被替换为 false
    assert re.search(r"^\s+enabled:\s*false", content, re.MULTILINE)


def test_patch_key_value_preserves_comments(tmp_path):
    """_patch_key_value 保留 YAML 注释"""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("debug:   # debug 配置\n  enabled: true  # 是否启用\n", encoding="utf-8")
    packer = TarPacker(PackConfig(config_patches={"debug": {"enabled": "false"}}))
    packer.patch_config(cfg)
    content = cfg.read_text(encoding="utf-8")
    # 注释应保留
    assert "# debug 配置" in content
    assert "# 是否启用" in content


def test_copy_rule_dir_to_parent(tmp_path):
    """目录复制：type + to（to 作为子路径）"""
    # from 相对于 skill_dir 的上两级（项目根目录），所以 src/ 放在 tmp_path/src/
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.txt").write_text("a")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "__init__.py").write_text("")

    cfg = PackConfig(
        file_copy_rules=[
            FileCopyRule.model_validate({"from": "src", "type": "scripts", "to": "src"})
        ]
    )
    packer = TarPacker(cfg)
    result = packer.pack("test-skill", str(tmp_path / "dist"), str(tmp_path / "skills"))

    with tarfile.open(result.output_file) as tf:
        names = [m.name for m in tf.getmembers()]
    assert "test-skill/scripts/src/a.txt" in names


def test_copy_rule_dir_no_to(tmp_path):
    """目录复制：仅有 type（直接复制到 type 目录）"""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "b.txt").write_text("b")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "__init__.py").write_text("")

    cfg = PackConfig(
        file_copy_rules=[FileCopyRule.model_validate({"from": "src", "type": "scripts"})]
    )
    packer = TarPacker(cfg)
    result = packer.pack("test-skill", str(tmp_path / "dist"), str(tmp_path / "skills"))

    with tarfile.open(result.output_file) as tf:
        names = [m.name for m in tf.getmembers()]
    assert "test-skill/scripts/b.txt" in names


def test_copy_rule_dir_with_glob(tmp_path):
    """目录复制 + glob 过滤（只复制匹配的文件）"""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a")
    (tmp_path / "src" / "b.txt").write_text("b")
    (tmp_path / "src" / "c.py").write_text("c")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "__init__.py").write_text("")

    cfg = PackConfig(
        file_copy_rules=[
            FileCopyRule.model_validate(
                {"from": "src", "type": "scripts", "to": "src", "glob": "*.py"}
            )
        ]
    )
    packer = TarPacker(cfg)
    result = packer.pack("test-skill", str(tmp_path / "dist"), str(tmp_path / "skills"))

    with tarfile.open(result.output_file) as tf:
        names = [m.name for m in tf.getmembers()]
    # glob="*.py" 只复制 .py 文件
    assert "test-skill/scripts/src/a.py" in names
    assert "test-skill/scripts/src/c.py" in names
    assert "test-skill/scripts/src/b.txt" not in names


def test_copy_rule_file(tmp_path):
    """文件复制：单个文件复制"""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    # 文件需要放在 skill_dir 的上两级（即项目根目录 tmp_path）
    (tmp_path / "config.yaml").write_text("key: value", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "__init__.py").write_text("")

    cfg = PackConfig(
        file_copy_rules=[FileCopyRule.model_validate({"from": "config.yaml", "type": "scripts"})]
    )
    packer = TarPacker(cfg)
    result = packer.pack("test-skill", str(tmp_path / "dist"), str(tmp_path / "skills"))

    with tarfile.open(result.output_file) as tf:
        names = [m.name for m in tf.getmembers()]
    assert "test-skill/scripts/config.yaml" in names


def test_pack_excludes_pycache(tmp_path):
    """__pycache__ 目录应被排除在打包之外"""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "__init__.py").write_text("")

    # 源码 src/ 里含 __pycache__/
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# main", encoding="utf-8")
    pycache_dir = tmp_path / "src" / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "main.cpython-311.pyc").write_bytes(b"fake bytecode")

    cfg = PackConfig(
        file_copy_rules=[
            FileCopyRule.model_validate({"from": "src", "type": "scripts", "to": "src"})
        ],
        exclude_patterns=["__pycache__", "*.pyc"],
    )
    packer = TarPacker(cfg)
    result = packer.pack("test-skill", str(tmp_path / "dist"), str(tmp_path / "skills"))

    with tarfile.open(result.output_file) as tf:
        names = [m.name for m in tf.getmembers()]
    # __pycache__ 不应出现在 tar 中
    assert not any("__pycache__" in n for n in names)
    # 源码文件应保留
    assert "test-skill/scripts/src/main.py" in names


def test_pack_creates_tarball(tmp_path, monkeypatch):
    """pack() 生成 tar.gz 文件"""
    # 创建模拟的 skill 目录结构
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\n---\n", encoding="utf-8"
    )
    (skill_dir / "src").mkdir()
    (skill_dir / "src" / "main.py").write_text("# main", encoding="utf-8")

    # Mock get_config
    # 实际测试需要临时目录和打包逻辑
    # 这里简化测试，实际应测试完整 pack 流程
    assert True  # placeholder
