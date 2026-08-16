# docgen 技能包入口

本文件是插件的入口索引：描述技能包组成、加载契约与每个技能的用途。兼容 Agent Skills 开放标准的 harness（dsh 等）通过**技能根目录 + frontmatter** 原生发现本包中的技能，本文件与 `manifest.json` 用于人工查阅与支持「入口文件」型加载器的读取。

## 加载契约（摘要）

- 发现方式：目录束 `<name>/SKILL.md` 或平铺文件 `<name>.md`，一层深度，递归目录不扫描；
- 身份字段：frontmatter 中的 `name` 必须为 kebab-case 且与所在目录/文件名一致；
- 路由字段：`description`（必填，含触发关键词）与 `whenToUse`（可选）决定模型何时激活技能；
- 其他字段：`metadata`（字符串键值映射）、`license`、`compatibility`、`allowed-tools`（均可选，字段拼写须与 [README.md](README.md#接口说明) 接口说明中的字段表逐字一致）；
- 详细说明见 [README.md](README.md#接口说明)。

## 技能清单

| 技能 | 目录 | 用途 | 典型触发语 |
|---|---|---|---|
| readme-forge | `skills/readme-forge/` | 从代码库生成/重写 README.md | 「给这个项目写个 README」 |
| pr-dossier | `skills/pr-dossier/` | 从 diff 生成 PR 描述（变更档案） | 「为这次改动写 PR 描述」 |
| changelog-curator | `skills/changelog-curator/` | 从 git 历史生成/维护 CHANGELOG | 「更新 changelog，准备发版」 |
| diff-verdict | `skills/diff-verdict/` | 输出结构化代码审查意见 | 「审查一下这个 PR」 |

## 使用方式

接入后直接以自然语言提出需求即可，harness 的模型会自动选择合适的技能并加载其 `SKILL.md`。可在提问中追加风格选项，例如：

- 「给这个项目写个 README，篇幅=精简」
- 「审查这个 PR，关注=安全」

示例提示词见 [examples/prompts.md](examples/prompts.md)。
