# build-skill

[Skill 标准](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)

将 `skills/<name>/` 打包为 `dist/<name>-YYYYMMDD-vX.X.X.tar.gz`

* 支持的目录结构

```
<project>/
├── skills/
│   ├── <name>/
│   │   ├── __init__.py
```

## 安装

```bash
pip install -e .
```

## 使用

```bash
# 指定 skill 名称打包
build-skill --name {skill_name}

# 仅验证 frontmatter
build-skill --name {skill_name} --validate

# 指定输出目录
build-skill --name {skill_name} --output ./dist

# 检查依赖
build-skill --check-deps
```

## CLI 参数

| 参数             | 说明                            |
|----------------|-------------------------------|
| `--name`       | 指定 skill 名称（空则从 skills/ 目录推断） |
| `--output`     | 指定输出目录（默认 dist）               |
| `--validate`   | 仅验证 frontmatter，不打包           |
| `--check-deps` | 检查 Python 依赖                  |
| `--config`     | 指定配置文件路径                      |
| `--debug`      | 开启调试输出                        |
| `--help`       | 显示帮助                          |

## 配置

配置文件搜索路径（优先级从高到低）：

1. `--config` CLI 参数
2. `BUILD_SKILL_CONFIG` 环境变量
3. `./.build_skill.yaml`（当前目录）
4. `~/.config/build-skill/config.yaml`（XDG）
5. 包内默认配置

## 程序化调用

```python
from build_skill.validator import FrontmatterValidator
from build_skill.config import get_config
from build_skill.packer import TarPacker

# 验证
validator = FrontmatterValidator(get_config().validation)
validator.validate(skill_dir)

# 打包
packer = TarPacker(get_config().pack)
result = packer.pack("{skill_name}", "dist")
```
