"""打包逻辑模块"""

import glob
import re
import shutil
import tarfile
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from build_skill.config import FileCopyRule, PackConfig
from build_skill.utils import get_version_from_file, warn


@dataclass
class PackResult:
    """打包结果"""

    output_file: str
    file_count: int
    size: str


class BasePacker(ABC):
    """打包器抽象基类"""

    @abstractmethod
    def pack(self, skill_name: str, output_dir: str, skills_dir: str = "skills") -> PackResult:
        """执行打包"""
        raise NotImplementedError

    @abstractmethod
    def patch_config(self, config_path: Path) -> None:
        """修补配置文件"""
        raise NotImplementedError


class TarPacker(BasePacker):
    """tar.gz 打包器实现"""

    def __init__(self, config: PackConfig) -> None:
        self._config = config

    def pack(self, skill_name: str, output_dir: str, skills_dir: str = "skills") -> PackResult:
        """打包流程：

        1. 创建临时构建目录
        2. 复制 SKILL.md
        3. 复制 src/（排除构建产物）
        4. 复制配置文件（requirements.txt, config.yaml）
        5. 复制 systemd 服务文件（如存在）
        6. 修补 config.yaml（使用 config_patches）
        7. 清理构建产物
        8. 生成 tar.gz
        """
        from datetime import date

        skill_dir = Path(skills_dir) / skill_name
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill 目录不存在: {skill_dir}")

        # 创建临时构建目录
        build_dir = Path(tempfile.mkdtemp())
        skill_build = build_dir / skill_name
        skill_build.mkdir()

        # 1. 复制 SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md 不存在: {skill_md}")
        shutil.copy2(skill_md, skill_build / "SKILL.md")

        # 2. 根据 file_copy_rules 复制文件
        for rule in self._config.file_copy_rules:
            self._copy_rule(skill_dir, skill_build, rule)

        # 3. 修补 config.yaml
        cfg_file = skill_build / "config.yaml"
        if cfg_file.exists():
            self.patch_config(cfg_file)

        # 4. 清理构建产物
        for pattern in self._config.exclude_patterns:
            for f in skill_build.rglob(pattern.replace("*", "")):
                if f.is_dir():
                    shutil.rmtree(f)
                elif f.is_file():
                    f.unlink()

        # 5. 生成 tar.gz
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        date_str = date.today().strftime("%Y%m%d")

        # 读取版本号（从 skill 自己的版本文件）
        override = self._config.skill_version_overrides.get(skill_name)
        version_file = (
            override.version_file
            if override and override.version_file
            else self._config.version_file
        )
        version_regex = (
            override.version_regex
            if override and override.version_regex
            else self._config.version_regex
        )
        version_path = skill_dir / version_file
        version = get_version_from_file(str(version_path), version_regex)
        if version == "0.0.0":
            warn(f"{version_path} 未定义版本，使用默认值 0.0.0")

        output_file = output_path / f"{skill_name}-{date_str}-v{version}.tar.gz"

        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(skill_build, arcname=skill_name)

        # 清理临时目录
        shutil.rmtree(build_dir)

        file_count = len(tarfile.open(output_file).getmembers()) - 1
        size = _human_readable_size(output_file.stat().st_size)

        return PackResult(output_file=str(output_file), file_count=file_count, size=size)

    @staticmethod
    def _copy_rule(skill_dir: Path, skill_build: Path, rule: FileCopyRule) -> None:
        """根据 FileCopyRule 复制文件或目录

        - from: 源路径（相对于 skill_dir，支持 ..）
        - to:   目标父目录（默认与 from 相同）
                   例：from="src", to="scripts" → skill_build/scripts/src
                   例：from="src", 无 to     → skill_build/src
        - glob: 可选，from 为目录时过滤文件
        """
        # from 相对于 skills/<name>/ 的上两级（即项目根目录），避免写 ../../ 前缀
        from_path = skill_dir / ".." / ".." / rule.from_
        # to 是父目录；无 to 时直接复制到 skill_build/from_
        if rule.to:
            to_parent = skill_build / rule.to
        else:
            to_parent = skill_build

        if rule.glob:
            # from 是目录，glob 过滤其中的文件
            pattern = str(from_path / rule.glob)
            matches = glob.glob(pattern, recursive=False)
            for src in matches:
                src_p = Path(src)
                dest = to_parent / src_p.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src_p.is_dir():
                    shutil.copytree(src_p, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_p, dest)
        elif from_path.is_file():
            dest = to_parent / from_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(from_path, dest)
        elif from_path.is_dir():
            if rule.to:
                dest = skill_build / rule.to
            else:
                dest = skill_build / from_path.name

            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and dest.is_dir():
                # to 已存在目录：展开 from 内容直接合并进去
                for item in from_path.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest / item.name)
            else:
                shutil.copytree(from_path, dest, dirs_exist_ok=True)

    def patch_config(self, config_path: Path) -> None:
        """使用正则行级替换修补 config.yaml，保留 YAML 注释"""
        content = config_path.read_text(encoding="utf-8")

        for section, patches in self._config.config_patches.items():
            for key, value in patches.items():
                content = self._patch_key_value(content, section, key, str(value))

        config_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _patch_key_value(
        content: str,
        section: str,
        key: str,
        value: str,
    ) -> str:
        """在指定 section 内替换单个键值，保留 YAML 注释"""
        # 定位目标 section
        pattern = rf"^({section}:\s*\n)((?:  .*\n)*)"
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            return content

        header = match.group(1)
        block = match.group(2)

        # 行级替换：key: old_value → key: new_value
        block = re.sub(
            rf"^(\s+{re.escape(key)}:\s*).*$",
            rf"\1{value}",
            block,
            flags=re.MULTILINE,
        )

        return content[: match.start()] + header + block + content[match.end() :]


def _human_readable_size(size: float) -> str:
    """将字节数转换为人类可读大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size = size / 1024
    return f"{size:.1f}TB"
