# 变更日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- `package.json` 声明 `dsh.bundle` 与 `cordis.patch.yml`：支持
  `dsh plugin --profile demo add github:JohnXu22786/docgen` 一键安装；
- `index.js` 技能挂载适配：加载时把 `skills/` 下四个 SKILL.md 运行时注册到
  `ctx.skills`（零运行依赖），并随插件卸载逆序注销；
- README 中英双语补充插件加载（dsh.bundle）主路径说明。

## [1.0.0] - 2026-08-16

初始版本：纯提示词文档生成技能包（README / PR 描述 / changelog / 代码审查），
可用于 dsh 等插件化 agent harness。

### 新增

- 四个技能：readme-forge / pr-dossier / changelog-curator / diff-verdict
  （`SKILL.md` + YAML frontmatter，遵循 Agent Skills 开放标准）；
- `manifest.json` 自描述清单与 `SKILLS.md` 入口索引；
- 零依赖校验脚本 `scripts/validate_skills.py` 及其回归测试；
- 接入示例 `examples/prompts.md` 与 `examples/dsh-patch-enable-skills.yml`；
- 中英双语 README。