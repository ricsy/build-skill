"""CLI 模块"""

import sys
from pathlib import Path

import typer

from build_skill.config import AppConfig, get_config
from build_skill.deps import check_dependencies
from build_skill.packer import TarPacker
from build_skill.utils import error, info, warn, resolve_skill_name, success
from build_skill.validator import FrontmatterValidator

# 设置 stdout/stderr 编码为 UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

app = typer.Typer(
    help="将 skills/<name>/ 打包为 dist/<name>-YYYYMMDD-vX.X.X.tar.gz",
    add_completion=False,
)


@app.command()
def main(
    name: str = typer.Option(None, "--name", help="指定 skill 名称（逗号分隔多个，或 all）"),
    output: str = typer.Option("dist", "--output", help="指定输出目录"),
    validate_only: bool = typer.Option(False, "--validate", help="仅验证 frontmatter"),
    check_deps: bool = typer.Option(False, "--check-deps", help="检查 Python 依赖"),
    config_path: str = typer.Option(None, "--config", help="配置文件路径"),
    debug: bool = typer.Option(False, "--debug", help="开启调试输出"),
) -> None:
    """打包 skill，如：test-20260324-v1.0.0.tar.gz"""
    # 1. 加载配置（可指定配置文件路径）
    if config_path is not None:
        cfg = AppConfig.load(config_path)
    else:
        cfg = get_config()

    # 2. CLI 参数覆盖 debug 配置
    if debug:
        cfg.debug.enabled = True
        cfg.debug.log_level = "DEBUG"

    # 3. 检查依赖（--check-deps）
    if check_deps:
        check_dependencies()
        return

    # 4. 确定要处理的 skill 列表
    skills_dir = Path(cfg.build.skills_dir)

    if name and name.lower() == "all":
        # 批量处理：所有 skill
        if not skills_dir.exists():
            error(f"Skill 目录不存在: {skills_dir}")
            raise typer.Exit(1)
        skill_names = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        if not skill_names:
            error(f"Skill 目录为空: {skills_dir}")
            raise typer.Exit(1)
        info(f"批量处理 {len(skill_names)} 个 skill: {skill_names}")
    elif name and "," in name:
        # 逗号分隔的多个 skill
        skill_names = [n.strip() for n in name.split(",") if n.strip()]
    elif name:
        # 单个 skill
        skill_names = [name]
    else:
        # 从 skills_dir 推断或使用配置的 default_skill
        try:
            skill_names = [resolve_skill_name(skills_dir, cfg.build.default_skill)]
            info(f"自动推断 skill: {skill_names[0]}")
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1)

    # 5. 批量验证
    validator = FrontmatterValidator(cfg.validation)
    results: dict[str, bool] = {}
    all_passed = True

    for skill_name in skill_names:
        skill_dir = skills_dir / skill_name
        if not skill_dir.exists():
            error(f"Skill 目录不存在: {skill_dir}")
            results[skill_name] = False
            all_passed = False
            continue

        passed = validator.validate(skill_dir)
        results[skill_name] = passed
        if passed:
            info(f"[{skill_name}] 验证通过")
        else:
            error(f"[{skill_name}] 验证失败:")
            for issue in validator.get_issues():
                error(f"  - {issue}")
            all_passed = False

    # 6. 仅验证模式
    if validate_only:
        if not all_passed:
            raise typer.Exit(1)
        info("全部验证通过")
        return

    # 7. 批量打包
    packer = TarPacker(cfg.pack)
    for skill_name in skill_names:
        if not results.get(skill_name, False):
            warn(f"[{skill_name}] 跳过打包")
            continue  # 跳过验证失败的
        skill_dir = skills_dir / skill_name
        if not skill_dir.exists():
            warn(f"Skill 目录不存在: {skill_dir}")
            continue
        info(f"开始打包 skill: {skill_name}")
        result = packer.pack(skill_name, output, cfg.build.skills_dir)
        success(f"打包完成: {result.output_file} ({result.size})")


if __name__ == "__main__":
    app()
