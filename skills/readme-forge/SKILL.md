---
name: readme-forge
description: 从代码库生成或重写 README.md 项目文档：盘点仓库结构、提取公共 API 与安装运行方式，产出结构化的项目说明。当用户要求生成或更新 README、项目简介、使用文档时使用。Generates README documentation from a codebase.
whenToUse: 用户提到「README」「项目说明」「使用文档」或要求为仓库补文档时；也适用于仓库已有 README 但内容过时、命令失效、结构混乱时的重写。
metadata:
  author: docgen
  version: "1.0.0"
  family: docgen
license: MIT
compatibility: 纯提示词技能，无需网络与第三方依赖；需要读取代码库文件与常见清单文件（package.json、pyproject.toml、Cargo.toml 等）的能力。
---

# readme-forge：README 生成

## 职责

把任意代码库转化为一份准确、可执行的 README.md。本技能的核心原则是**只写有证据的内容**：每个特性、每条命令、每个徽章都必须在仓库里有出处；找不到证据就写明「未提供」或直接省略，绝不编造。

## 何时使用

- 新仓库没有 README，用户要求补一份；
- 已有 README 但命令失效、结构混乱、与代码脱节，需要重写；
- 用户只给了仓库路径或目录，要求「介绍一下这个项目」。

## 输入收集

动手前先收集以下证据（能拿到多少算多少，拿不到的跳过并在输出中标注）：

| 证据 | 来源 | 用途 |
|---|---|---|
| 仓库树 | 根目录一层 + 关键子目录（src/、lib/、docs/、examples/） | 判断规模、模块划分 |
| 语言与构建信息 | package.json / pyproject.toml / Cargo.toml / go.mod / requirements.txt / *.csproj 等 | 技术栈、版本要求、依赖 |
| 安装与运行命令 | 清单文件的 scripts 字段、Makefile、justfile、docker-compose.yml | install_command / test_command（运行命令并入最小示例） |
| 入口与公共 API | 主入口文件（main.py、index.ts、cli.py…）、`__init__.py` 导出的符号、README 引用的模块 | API 概览、示例 |
| 测试方式 | CI 配置（.github/workflows、.gitlab-ci.yml）、清单 scripts | test_command、徽章依据 |
| 已有文档 | docs/ 目录、现有 README 残留内容 | 文档索引、避免重复 |
| 许可与作者 | LICENSE、仓库元信息 | 许可章节 |

## 工作流程

1. **盘点**：列出仓库树（两层为限）与清单文件，先判断「这是什么项目、用的是什么技术栈」。
2. **提取证据**：从清单和入口文件中提取真实存在的命令、版本约束、导出 API；从 CI 中提取测试与构建流程。
3. **澄清缺口**：如果仓库信息不足以回答「这个项目解决什么问题」，优先从代码注释、README 残留、示例代码推断；仍不确定时，把问题整理成简短清单问用户，而不是猜测。
4. **起草**：按下方输出模板组织内容，先写骨架再填证据。
5. **核验**：逐条检查每条命令、每个特性、每个路径是否能在仓库中找到对应物。

## 输出模板与变量

按以下结构输出（markdown 原文，直接可保存为 README.md）：

```markdown
# {project_name}

> {tagline}

{badges}

## 简介
{summary}

## 特性
{features}

## 快速开始
### 环境要求
{requirements}
### 安装
{install_command}
### 最小示例
{minimal_example}

## 文档索引
{docs_index}

## 测试
{test_command}

## 贡献
{contributing}

## 许可
{license}
```

| 模板变量 | 含义 | 示例 |
|---|---|---|
| {project_name} | 项目名（取清单文件 name 或目录名） | dsh-plugin |
| {tagline} | 一句话定位（从描述字段提炼） | 为代码库铸造文档的技能包 |
| {badges} | 徽章区，只放有证据的（CI 徽章依据配置文件、许可徽章依据 LICENSE） | `![License](...)` |
| {summary} | 3-6 句项目简介：解决什么问题、怎么工作、适合谁 | … |
| {features} | 特性列表，每条对应代码里的具体能力 | - 从 git 历史生成 changelog |
| {requirements} | 环境要求（语言版本、运行时、依赖），以清单文件为准 | Node.js >= 20 |
| {install_command} | 真实可执行的安装命令 | `npm install` / `pip install -r requirements.txt` |
| {minimal_example} | 最小使用示例（真实存在的命令/API，带预期输出） | `dsh --help` |
| {docs_index} | 指向 docs/ 下已有文档的链接列表；没有则省略此节 | `[API 文档](docs/api.md)` |
| {test_command} | 真实存在的测试命令 | `npm test` / `python -m unittest` |
| {contributing} | 指向贡献文档或简短的贡献说明；没有则省略 | 见 [CONTRIBUTING.md] |
| {license} | 许可名称 + 声明（LICENSE 不存在时写「未提供」） | MIT License |

## 风格选项

默认语言跟随用户提问语言，篇幅为标准。用户可用自然语言覆盖：

- 语言：`语言=简体中文`、`language=en`、`双语`
- 篇幅：`篇幅=精简`（只保留简介/快速开始/许可三节）、`篇幅=标准`（默认）、`篇幅=详尽`（补充架构与设计说明，须有代码依据）
- 语气：`语气=正式`（默认，客观陈述）、`语气=亲和`（面向新手的解释性语气）

## 质量检查清单

输出前逐项自检，任何一项不满足都要修正：

- [ ] 每条命令（安装/运行/测试）都来自清单文件或代码，不是凭经验补的
- [ ] 每个特性条目在代码中能找到对应实现或配置
- [ ] 版本号、语言版本、依赖名与实际文件一致
- [ ] 文件路径和模块名与实际结构一致（相对路径没有跳出去）
- [ ] 徽章以仓库真实内容为据，不虚构覆盖率/下载量
- [ ] 示例代码的 API 名称、参数、输出与代码一致
- [ ] 没有「TODO」「待补充」等占位符；确实缺失的信息用「未提供」标注或询问用户
- [ ] 结构完整：至少包含标题、一句话简介、快速开始、许可四部分

## 不要做

- 不要编造 CLI 参数、API、命令——这是 README 生成最常见的错误，宁可省略
- 不要整棵目录树贴进 README，只保留与用户相关的入口结构
- 不要写「高性能」「企业级」等无证据的形容词
- 不要在生成后自称「我检查过」——除非真的逐条核验过证据

## 边界情况

- **空仓库 / 几乎没有文件**：直接说明现状，输出只含标题与「尚未就绪」说明，不硬凑章节。
- **Monorepo / 多包仓库**：在简介说明结构，每个子包一节「快速开始」，命令按子包路径给出。
- **README 已存在**：先对比旧版与代码，保留仍然正确的历史信息（如截图、链接），重写过时部分。
- **语言无法确定**：以清单文件和主要源码文件的注释语言为准，不靠猜测。
- **超大仓库**：只覆盖公共入口与用户视角，不逐模块罗列；必要时询问用户重点。
